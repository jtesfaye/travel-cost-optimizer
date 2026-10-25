"""Stage 1 - routing: turn origin/destination into priced-by-distance Candidates.

Covers get_routes (Routes API), toll parsing, per-route energy cost, the polyline
codec the rest of the pipeline relies on, and the stub candidate generator.
"""

import pytest
from google.maps import routing_v2
from google.type import money_pb2

from app.schemas.optimize import Coordinate
from app.services import optimizer
from app.services.geo import decode_polyline, encode_polyline
from tests import factories as f

# --------------------------------------------------------------------- unit


@pytest.mark.unit
class TestDeriveEnergyCost:
    def test_gas_uses_mpg_and_stub_price(self):
        # 300 mi / 30 mpg = 10 gal * $3.45
        assert optimizer.derive_energy_cost(300, f.gas_vehicle(mpg=30)) == 34.5

    def test_ev_uses_kwh_per_mile_and_stub_price(self):
        # 75 kWh / 300 mi = 0.25 kWh/mi; 300 mi = 75 kWh * $0.42
        assert optimizer.derive_energy_cost(300, f.ev_vehicle(300, 75)) == 31.5

    def test_hybrid_is_priced_like_gas(self):
        hybrid = f.gas_vehicle(mpg=50).model_copy(update={"type": "hybrid"})
        assert optimizer.derive_energy_cost(100, hybrid) == round(100 / 50 * 3.45, 2)

    def test_zero_distance_is_free(self):
        assert optimizer.derive_energy_cost(0, f.gas_vehicle()) == 0

    def test_rounds_to_cents(self):
        cost = optimizer.derive_energy_cost(10, f.gas_vehicle(mpg=33))
        assert cost == round(cost, 2)

    def test_worse_mpg_costs_more(self):
        thirsty = optimizer.derive_energy_cost(100, f.gas_vehicle(mpg=15))
        frugal = optimizer.derive_energy_cost(100, f.gas_vehicle(mpg=45))
        assert thirsty > frugal


@pytest.mark.unit
class TestBuildTollList:
    @staticmethod
    def toll_info(*prices):
        return routing_v2.TollInfo(estimated_price=list(prices))

    def test_no_tolls(self):
        assert optimizer.build_toll_list(self.toll_info()) == []

    def test_converts_units_and_nanos(self):
        (toll,) = optimizer.build_toll_list(self.toll_info(f.usd(4, 250_000_000)))
        assert toll.cost == 4.25

    def test_one_toll_per_usd_entry(self):
        tolls = optimizer.build_toll_list(self.toll_info(f.usd(2), f.usd(3, 500_000_000)))
        assert [t.cost for t in tolls] == [2.0, 3.5]

    def test_ignores_non_usd(self):
        cad = money_pb2.Money(currency_code="CAD", units=9)
        tolls = optimizer.build_toll_list(self.toll_info(cad, f.usd(2)))
        assert [t.cost for t in tolls] == [2.0]

    def test_only_non_usd_gives_empty_list(self):
        eur = money_pb2.Money(currency_code="EUR", units=5)
        assert optimizer.build_toll_list(self.toll_info(eur)) == []

    def test_rounds_to_cents(self):
        (toll,) = optimizer.build_toll_list(self.toll_info(f.usd(1, 333_333_333)))
        assert toll.cost == 1.33


@pytest.mark.unit
class TestPolylineCodec:
    # the worked example from Google's encoded polyline documentation
    GOOGLE_EXAMPLE = [(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)]

    def test_decodes_googles_reference_example(self):
        decoded = decode_polyline("_p~iF~ps|U_ulLnnqC_mqNvxq`@")
        assert f.close(decoded, self.GOOGLE_EXAMPLE)

    def test_round_trip(self):
        pts = f.line(25)
        again = decode_polyline(encode_polyline(pts))
        assert f.close(again, pts)

    def test_empty(self):
        assert decode_polyline("") == []

    def test_handles_negative_and_zero_deltas(self):
        pts = [(0.0, 0.0), (0.0, 0.0), (-1.5, 2.5), (-1.5, -2.5)]
        assert f.close(decode_polyline(encode_polyline(pts)), pts)


@pytest.mark.unit
class TestGetRoutes:
    ORIGIN = Coordinate(lat=34.05, lng=-118.25)
    DEST = Coordinate(lat=37.77, lng=-122.42)

    async def test_maps_route_fields_to_candidate(self, fake_routes):
        fake_routes.routes = [
            f.api_route(f.line(11), meters=160_934, minutes=90, description="I-5 N")
        ]
        (c,) = await optimizer.get_routes(self.ORIGIN, self.DEST)

        assert c.distance_mi == 100.0  # 160,934 m
        assert c.duration_min == 90
        assert c.description == "I-5 N"
        assert f.close(c.points, f.line(11))

    async def test_duration_is_total_seconds_not_the_seconds_field(self, fake_routes):
        # proto-plus gives a timedelta; .seconds would wrap at 24h and report 120
        fake_routes.routes = [f.api_route(minutes=26 * 60 + 2)]
        (c,) = await optimizer.get_routes(self.ORIGIN, self.DEST)
        assert c.duration_min == 26 * 60 + 2

    async def test_toll_cost_sums_usd_tolls(self, fake_routes):
        fake_routes.routes = [f.api_route(tolls=[f.usd(2, 500_000_000), f.usd(1)])]
        (c,) = await optimizer.get_routes(self.ORIGIN, self.DEST)
        assert c.toll_cost == 3.5

    async def test_route_without_tolls_costs_nothing(self, fake_routes):
        (c,) = await optimizer.get_routes(self.ORIGIN, self.DEST)
        assert c.toll_cost == 0

    async def test_alternatives_get_unique_tags(self, fake_routes):
        fake_routes.routes = [f.api_route(), f.api_route(), f.api_route()]
        candidates = await optimizer.get_routes(self.ORIGIN, self.DEST)
        assert [c.tag for c in candidates] == ["0", "1", "2"]
        assert len({c.label for c in candidates}) == 3

    async def test_request_carries_waypoints_tolls_and_alternatives(self, fake_routes):
        await optimizer.get_routes(self.ORIGIN, self.DEST)
        (request, metadata), = fake_routes.calls

        assert request.origin.location.lat_lng.latitude == self.ORIGIN.lat
        assert request.origin.location.lat_lng.longitude == self.ORIGIN.lng
        assert request.destination.location.lat_lng.latitude == self.DEST.lat
        assert request.destination.location.lat_lng.longitude == self.DEST.lng
        assert request.travel_mode == routing_v2.RouteTravelMode.DRIVE
        assert request.compute_alternative_routes is True
        assert (
            routing_v2.ComputeRoutesRequest.ExtraComputation.TOLLS
            in request.extra_computations
        )

    async def test_field_mask_asks_for_everything_the_candidate_needs(self, fake_routes):
        await optimizer.get_routes(self.ORIGIN, self.DEST)
        (_, metadata), = fake_routes.calls
        key, mask = metadata[0]

        assert key == "x-goog-fieldmask"
        assert " " not in mask
        for field in (
            "routes.distanceMeters",
            "routes.duration",
            "routes.polyline.encodedPolyline",
            "routes.travelAdvisory.tollInfo",
        ):
            assert field in mask.split(",")

    async def test_no_routes_is_no_feasible_route(self, fake_routes):
        fake_routes.routes = []
        with pytest.raises(optimizer.OptimizationError) as err:
            await optimizer.get_routes(self.ORIGIN, self.DEST)
        assert err.value.code == "no_feasible_route"


@pytest.mark.unit
class TestGenerateCandidateRoutes:
    async def test_returns_the_routes_api_candidates_for_the_request(self, fake_routes):
        fake_routes.routes = [f.api_route(f.line(21), description="I-5"), f.api_route(f.line(11))]
        candidates = await optimizer.generate_candidate_routes(f.request())
        assert [c.description for c in candidates][0] == "I-5"
        assert [c.tag for c in candidates] == ["0", "1"]

    async def test_asks_for_the_requested_origin_and_destination(self, fake_routes):
        req = f.request()
        await optimizer.generate_candidate_routes(req)
        sent, _ = fake_routes.calls[0]
        assert sent.origin.location.lat_lng.latitude == pytest.approx(req.origin.lat)
        assert sent.destination.location.lat_lng.longitude == pytest.approx(req.destination.lng)

    async def test_no_route_is_rejected(self, fake_routes):
        fake_routes.routes = []
        with pytest.raises(optimizer.OptimizationError) as err:
            await optimizer.generate_candidate_routes(f.request())
        assert err.value.code == "no_feasible_route"


# -------------------------------------------------------------- integration


@pytest.mark.integration
class TestRoutingStageIntegration:
    async def test_api_response_becomes_consistent_candidates(self, fake_routes):
        pts = f.line(41)
        fake_routes.routes = [
            f.api_route(pts, meters=round(f.miles(pts) * 1609.344), tolls=[f.usd(6)]),
            f.api_route(f.line(21), meters=round(f.miles(f.line(21)) * 1609.344)),
        ]
        candidates = await optimizer.get_routes(
            Coordinate(lat=f.A[0], lng=f.A[1]), Coordinate(lat=f.B[0], lng=f.B[1])
        )

        assert len(candidates) == 2
        for c in candidates:
            # reported distance and the geometry it came with agree
            assert c.distance_mi == pytest.approx(f.miles(c.points), abs=0.2)
            assert c.points[0] == pytest.approx(f.A, abs=1e-4)
            assert c.points[-1] == pytest.approx(f.B, abs=1e-4)
        assert [c.toll_cost for c in candidates] == [6.0, 0]

    async def test_distance_converts_meters_to_miles(self, fake_routes):
        fake_routes.routes = [f.api_route(meters=1_609_344)]  # exactly 1000 mi
        (c,) = await optimizer.get_routes(
            Coordinate(lat=f.A[0], lng=f.A[1]), Coordinate(lat=f.B[0], lng=f.B[1])
        )
        assert c.distance_mi == pytest.approx(1000, rel=1e-4)
