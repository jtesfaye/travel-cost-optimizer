"""Stage 4 - the whole pipeline: optimize() end to end, and the HTTP job API.

External services (Routes, Places, NREL) are faked; everything inside the app runs
for real. The `routed` fixture gives the fake Routes API two alternatives.
"""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import jobs, optimizer
from app.services.geo import decode_polyline
from tests import factories as f

DIRECT = f.line(307)  # ~306 mi, one vertex a mile
M = (35.0, -121.0)
VIA_COAST = [*f.line(160, f.A, M), *f.line(160, M, f.B)[1:]]  # longer way round


def meters(points) -> int:
    return round(f.miles(points) * 1609.344)


def stations_along(points, price, step=20, id_prefix="p"):
    return [
        f.place(f"{id_prefix}{m}", *f.beside(points, m, 1), price=price)
        for m in range(step, int(f.miles(points)) - 5, step)
    ]


def both_routes(direct_price=3.5, coast_price=3.5):
    return stations_along(DIRECT, direct_price) + stations_along(VIA_COAST, coast_price, id_prefix="q")


@pytest.fixture
def routed(fake_routes, no_delay):
    """Two alternatives: a tolled direct road and a longer free one."""
    fake_routes.routes = [
        f.api_route(DIRECT, meters=meters(DIRECT), minutes=300, description="I-5", tolls=[f.usd(6)]),
        f.api_route(VIA_COAST, meters=meters(VIA_COAST), minutes=340, description="US-101"),
    ]
    return fake_routes


class Progress:
    def __init__(self):
        self.calls = []

    def __call__(self, stage, fraction):
        self.calls.append((stage, fraction))


# ---------------------------------------------------------- optimize(), unit


@pytest.mark.unit
class TestOptimizeProgress:
    async def test_reports_stages_in_order_with_rising_progress(self, routed, fake_places):
        fake_places.places = both_routes()
        progress = Progress()
        await optimizer.optimize(f.request(), progress)

        assert [s for s, _ in progress.calls] == ["routing", "pricing", "optimizing"]
        fractions = [p for _, p in progress.calls]
        assert fractions == sorted(fractions) and 0 < fractions[0] < fractions[-1] < 1

    async def test_failure_in_pricing_never_reaches_optimizing(self, routed, fake_places):
        fake_places.error = f.api_error("boom")
        progress = Progress()
        with pytest.raises(optimizer.OptimizationError):
            await optimizer.optimize(f.request(), progress)
        assert [s for s, _ in progress.calls] == ["routing", "pricing"]

    async def test_routing_failure_stops_before_pricing(self, fake_routes, no_delay, fake_places):
        fake_routes.routes = []
        progress = Progress()
        with pytest.raises(optimizer.OptimizationError) as err:
            await optimizer.optimize(f.request(), progress)
        assert err.value.code == "no_feasible_route"
        assert [s for s, _ in progress.calls] == ["routing"]
        assert fake_places.calls == []


# ------------------------------------------------------ optimize(), integration


@pytest.mark.integration
class TestOptimizeIntegration:
    async def test_one_result_per_candidate_route(self, routed, fake_places):
        fake_places.places = both_routes()
        result = await optimizer.optimize(f.request(), Progress())

        assert [r.id for r in result.routes] == ["route-0", "route-1"]
        assert [r.description for r in result.routes] == ["I-5", "US-101"]
        assert [r.duration_min for r in result.routes] == [300, 340]

    async def test_route_geometry_survives_to_the_response(self, routed, fake_places):
        fake_places.places = both_routes()
        result = await optimizer.optimize(f.request(), Progress())
        assert f.close(decode_polyline(result.routes[0].polyline), DIRECT)

    async def test_costs_add_up(self, routed, fake_places):
        fake_places.places = both_routes()
        result = await optimizer.optimize(f.request(), Progress())

        for r in result.routes:
            assert r.cost.total == pytest.approx(r.cost.energy + r.cost.tolls, abs=0.01)
            assert r.cost.tolls == pytest.approx(sum(t.cost for t in r.tolls))
            assert r.cost.energy > 0
        assert result.routes[0].cost.tolls == 6.0
        assert [(t.name, t.cost) for t in result.routes[0].tolls] == [("Route tolls", 6.0)]
        assert result.routes[1].cost.tolls == 0.0

    async def test_cheapest_total_is_recommended(self, routed, fake_places):
        # direct road: tolled and pricey fuel; coast road: longer but free and cheap fuel
        fake_places.places = both_routes(direct_price=4.2, coast_price=3.0)
        result = await optimizer.optimize(f.request(), Progress())

        cheapest = min(result.routes, key=lambda r: r.cost.total)
        assert result.recommended_route_id == cheapest.id == "route-1"

    async def test_tolls_can_flip_the_recommendation(self, routed, fake_places):
        # same fuel price both ways, so the shorter road wins until its toll gets big
        fake_places.places = both_routes()

        def direct_with_toll(dollars):
            routed.routes[0] = f.api_route(
                DIRECT, meters=meters(DIRECT), minutes=300, description="I-5", tolls=[f.usd(dollars)]
            )

        direct_with_toll(1)
        assert (await optimizer.optimize(f.request(), Progress())).recommended_route_id == "route-0"
        direct_with_toll(80)
        assert (await optimizer.optimize(f.request(), Progress())).recommended_route_id == "route-1"

    async def test_stops_are_planned_per_route_from_its_own_stations(self, routed, fake_places):
        fake_places.places = both_routes()
        result = await optimizer.optimize(f.request(), Progress())

        assert result.routes[0].stops and result.routes[1].stops
        assert all(s.id.startswith("0-stop-") for s in result.routes[0].stops)
        assert all(s.id.startswith("1-stop-") for s in result.routes[1].stops)
        assert all(s.type == "fuel" for r in result.routes for s in r.stops)

    async def test_ev_trip_uses_nrel_chargers_and_kwh(self, routed, fake_nrel):
        fake_nrel.stations = [
            f.nrel_station(f"{tag}{m}", *f.beside(points, m, 1), "$0.45/kWh")
            for tag, points in (("d", DIRECT), ("c", VIA_COAST))
            for m in range(30, 300, 30)
        ]
        ev = f.ev_vehicle(range_mi=200, battery_kwh=60)
        result = await optimizer.optimize(f.request(ev), Progress())

        direct = result.routes[0]
        assert direct.stops and {s.type for s in direct.stops} == {"charging"}
        assert {s.price_unit for s in direct.stops} == {"kWh"}

    async def test_price_as_of_is_now_and_timezone_aware(self, routed, fake_places):
        fake_places.places = both_routes()
        before = datetime.now(timezone.utc)
        result = await optimizer.optimize(f.request(), Progress())
        assert before <= result.price_as_of <= datetime.now(timezone.utc)

    async def test_no_reachable_station_fails_the_whole_run(self, routed, fake_places):
        fake_places.places = []
        with pytest.raises(optimizer.OptimizationError) as err:
            await optimizer.optimize(f.request(), Progress())
        assert err.value.code == "no_feasible_route"

    async def test_upstream_failure_surfaces_as_upstream_error(self, routed, fake_places):
        fake_places.error = f.api_error("quota exceeded")
        with pytest.raises(optimizer.OptimizationError) as err:
            await optimizer.optimize(f.request(), Progress())
        assert err.value.code == "upstream_error"


# ------------------------------------------------------------- HTTP job API

BODY = {
    "origin": {"lat": f.A[0], "lng": f.A[1]},
    "destination": {"lat": f.B[0], "lng": f.B[1]},
    "vehicle": {"type": "gas", "mpg": 25, "tankGal": 10},
}


@pytest.fixture
def api(routed, fake_places):
    fake_places.places = both_routes()
    with TestClient(app) as client:
        yield client


def submit(client, body=BODY):
    resp = client.post("/api/v1/optimizations", json=body)
    return resp, client.get(resp.headers["Location"]) if "Location" in resp.headers else None


@pytest.mark.integration
class TestOptimizationJobApi:
    def test_accepts_the_job_and_points_to_it(self, api):
        resp = api.post("/api/v1/optimizations", json=BODY)

        assert resp.status_code == 202
        job = resp.json()
        assert job["status"] == "queued"
        assert resp.headers["Location"] == f"/api/v1/optimizations/{job['id']}"

    def test_job_completes_with_a_camel_cased_result(self, api):
        _, polled = submit(api)
        job = polled.json()

        assert job["status"] == "succeeded"
        assert (job["stage"], job["progress"]) == ("done", 1)
        result = job["result"]
        assert len(result["routes"]) == 2
        assert result["recommendedRouteId"] in {r["id"] for r in result["routes"]}
        route = result["routes"][0]
        assert {"distanceMi", "durationMin", "cost", "polyline", "stops", "tolls"} <= route.keys()
        assert {"energy", "tolls", "total"} == route["cost"].keys()
        assert "priceAsOf" in result

    def test_ev_job_with_chargers(self, api, fake_nrel):
        fake_nrel.stations = [
            f.nrel_station(f"{tag}{m}", *f.beside(points, m, 1), "$0.40/kWh")
            for tag, points in (("d", DIRECT), ("c", VIA_COAST))
            for m in range(30, 300, 30)
        ]
        body = {**BODY, "vehicle": {"type": "ev", "rangeMi": 220, "batteryKwh": 66}}
        _, polled = submit(api, body)

        job = polled.json()
        assert job["status"] == "succeeded"
        stops = job["result"]["routes"][0]["stops"]
        assert stops and {s["priceUnit"] for s in stops} == {"kWh"}

    def test_no_reachable_station_fails_the_job_with_a_code(self, api, fake_places):
        fake_places.places = []
        _, polled = submit(api)

        job = polled.json()
        assert job["status"] == "failed"
        assert job["error"]["code"] == "no_feasible_route"
        assert job["result"] is None

    def test_provider_outage_fails_the_job_as_upstream_error(self, api, fake_places):
        fake_places.error = f.api_error("quota exceeded")
        _, polled = submit(api)
        assert polled.json()["error"]["code"] == "upstream_error"

    def test_unexpected_crash_is_reported_without_leaking_details(self, api, monkeypatch):
        async def explode(req, report):
            raise RuntimeError("secret internals")

        monkeypatch.setattr(jobs, "optimize", explode)
        _, polled = submit(api)

        error = polled.json()["error"]
        assert error["code"] == "internal_error"
        assert "secret" not in error["message"]

    def test_invalid_vehicle_is_rejected_up_front(self, api):
        body = {**BODY, "vehicle": {"type": "ev", "rangeMi": 200}}  # no battery size
        resp = api.post("/api/v1/optimizations", json=body)
        assert resp.status_code == 422

    def test_out_of_range_coordinates_are_rejected(self, api):
        body = {**BODY, "origin": {"lat": 123, "lng": f.A[1]}}
        assert api.post("/api/v1/optimizations", json=body).status_code == 422

    def test_unknown_job_is_404(self, api):
        assert api.get("/api/v1/optimizations/nope").status_code == 404
