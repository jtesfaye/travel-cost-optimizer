"""Stage 2 - pricing: find charging/fuel stations along each candidate route.

Gas goes through Google Places Nearby Search, EVs through NREL's nearby-route
search. Both return Stations with a mile marker, detour and price.
"""

import asyncio
import math

import pytest

from app.core.config import settings
from app.schemas.optimize import Coordinate
from app.services import optimizer
from app.services.geo import decode_polyline, encode_polyline
from tests import factories as f

DENSE = f.line(307)  # a vertex roughly every mile
DENSE_MILES = f.miles(DENSE)

# --------------------------------------------------------------------- unit


@pytest.mark.unit
class TestParseEvPrice:
    @pytest.mark.parametrize(
        "text, expected",
        [
            ("$0.48/kWh", 0.48),
            ("$0.35 per kWh", 0.35),
            ("$ 0.40 / kWh", 0.40),
            ("$0.35 per kWh; $0.50/min idle fee", 0.35),
            ("Free for 30 min then $0.40 per kWh", 0.40),
            ("Free", 0.0),
            ("FREE", 0.0),
            ("$1.00 per session", None),
            ("$0.25/min", None),
            ("Rates vary by time of day", None),
            ("", None),
            (None, None),
        ],
    )
    def test_parse(self, text, expected):
        assert optimizer.parse_ev_price(text) == expected


@pytest.mark.unit
class TestRouteGeometryHelpers:
    def test_cumulative_miles_starts_at_zero_and_ends_at_length(self):
        cumulative = optimizer._cumulative_miles(DENSE)
        assert cumulative[0] == 0
        assert cumulative[-1] == pytest.approx(DENSE_MILES)
        assert cumulative == sorted(cumulative)

    def test_point_at_hits_the_ends_and_the_middle(self):
        cumulative = optimizer._cumulative_miles(DENSE)
        assert optimizer._point_at(DENSE, cumulative, 0) == DENSE[0]
        assert optimizer._point_at(DENSE, cumulative, cumulative[-1]) == pytest.approx(DENSE[-1])
        mid = optimizer._point_at(DENSE, cumulative, cumulative[-1] / 2)
        assert f.miles([DENSE[0], mid]) == pytest.approx(cumulative[-1] / 2, rel=0.01)

    def test_point_at_is_not_snapped_to_vertices(self):
        sparse = [f.A, f.B]  # one 300+ mile segment
        cumulative = optimizer._cumulative_miles(sparse)
        mile = cumulative[-1] / 3
        assert f.miles([sparse[0], optimizer._point_at(sparse, cumulative, mile)]) == pytest.approx(mile, rel=0.01)  # lat/lng interpolation vs great circle

    @pytest.mark.parametrize("n", [2, 5, 20, 21, 307])
    def test_nearest_vertex_matches_brute_force(self, n):
        pts = f.line(n)
        for k in range(0, n, max(1, n // 7)):
            here = (pts[k][0] + 0.02, pts[k][1] - 0.01)
            brute = min(range(n), key=lambda j: optimizer.haversine_mi(here, pts[j]))
            assert optimizer._nearest_vertex(pts, here) == brute

    def test_nrel_route_is_longitude_first_wkt(self):
        wkt = optimizer._nrel_route_wkt(f.line(3), optimizer._cumulative_miles(f.line(3)))
        assert wkt.startswith("LINESTRING(-118.00000 34.00000, ")
        assert wkt.endswith("-122.00000 37.00000)")

    def test_nrel_route_is_thinned_but_keeps_both_ends(self):
        pts = f.line(3001)  # a vertex every ~0.1 mi
        wkt = optimizer._nrel_route_wkt(pts, optimizer._cumulative_miles(pts))
        count = wkt.count(",") + 1
        assert count < len(pts) / 3
        assert wkt.startswith("LINESTRING(-118.00000 34.00000")
        assert wkt.endswith("-122.00000 37.00000)")


@pytest.mark.unit
class TestStationFromPlace:
    def test_fresh_price_is_live(self):
        s = optimizer._station_from_place(f.place("a", 35, -119, price=3.599, age_hours=1), 12.34, 0.5)
        assert (s.price, s.source) == (3.599, "live")

    def test_stale_price_is_kept_but_estimated(self):
        s = optimizer._station_from_place(f.place("a", 35, -119, price=3.7, age_hours=100), 10, 0.5)
        assert (s.price, s.source) == (3.7, "estimated")

    def test_missing_price_falls_back_to_stub(self):
        s = optimizer._station_from_place(f.place("a", 35, -119, price=None), 10, 0.5)
        assert (s.price, s.source) == (optimizer.STUB_GAS_PRICE, "estimated")

    def test_diesel_only_does_not_count_as_regular(self):
        p = f.place("a", 35, -119, price=4.9, fuel_type=f.FuelType.DIESEL)
        s = optimizer._station_from_place(p, 10, 0.5)
        assert (s.price, s.source) == (optimizer.STUB_GAS_PRICE, "estimated")

    def test_non_usd_price_is_ignored(self):
        p = f.place("a", 35, -119, price=1.9, currency="CAD")
        s = optimizer._station_from_place(p, 10, 0.5)
        assert s.price == optimizer.STUB_GAS_PRICE

    def test_detour_is_a_round_trip_and_minutes_follow_speed(self):
        s = optimizer._station_from_place(f.place("a", 35, -119), 10, 1.5)
        assert s.detour_mi == 3.0
        assert s.detour_min == pytest.approx(3.0 / optimizer.DETOUR_SPEED_MPH * 60)

    def test_copies_identity_and_position(self):
        s = optimizer._station_from_place(f.place("abc", 35.5, -119.25), 42.449, 0.2)
        assert (s.name, s.address) == ("Gas abc", "abc Main St")
        assert (s.lat, s.lng) == (35.5, -119.25)
        assert s.mile_marker == 42.4


@pytest.mark.unit
class TestFindGasStations:
    async def test_search_circles_cover_the_route_end_to_end(self, fake_places):
        await optimizer.find_gas_stations(f.candidate(DENSE))
        centers = [
            (r.location_restriction.circle.center.latitude, r.location_restriction.circle.center.longitude)
            for r, _ in fake_places.calls
        ]
        assert len(centers) == math.floor(DENSE_MILES / optimizer.STATION_SAMPLE_MI) + 1 + 1
        # searches run concurrently, so calls arrive in any order; this route heads north
        ordered = sorted(centers)
        # centres snap to the cache grid, which moves them under a mile
        slack = optimizer.PLACES_SNAP_SLACK_MI
        assert f.miles([ordered[0], f.A]) <= slack
        assert f.miles([ordered[-1], f.B]) <= slack
        gaps = [f.miles([p, q]) for p, q in zip(ordered, ordered[1:])]
        assert max(gaps) <= optimizer.STATION_SAMPLE_MI + 2 * slack

    async def test_request_shape(self, fake_places):
        await optimizer.find_gas_stations(f.candidate(DENSE))
        request, metadata = fake_places.calls[0]

        assert list(request.included_types) == ["gas_station"]
        assert request.max_result_count == 20
        assert request.rank_preference == optimizer.places_v1.SearchNearbyRequest.RankPreference.DISTANCE
        assert request.location_restriction.circle.radius == pytest.approx(
            (optimizer.STATION_RADIUS_MI + optimizer.PLACES_SNAP_SLACK_MI) * 1609.344
        )
        key, mask = metadata[0]
        assert key == "x-goog-fieldmask"
        assert "places.fuelOptions" in mask.split(",")
        assert " " not in mask

    async def test_circles_leave_no_gap_for_stations_within_the_detour_budget(self, fake_places):
        # every 3 miles, alternating on the road and up to 3.5 mi (7 mi round trip) off it
        offsets = [0, 2, 3.5]
        miles = [m for m in range(1, int(DENSE_MILES) - 1, 3)]
        fake_places.places = [
            f.place(f"s{m}", *f.beside(DENSE, m, offsets[k % 3])) for k, m in enumerate(miles)
        ]
        stations = await optimizer.find_gas_stations(f.candidate(DENSE))
        assert len(stations) == len(miles)

    async def test_mile_markers_track_where_the_station_really_is(self, fake_places):
        fake_places.places = [f.place(f"s{m}", *f.beside(DENSE, m, 1)) for m in (20, 100, 250)]
        stations = await optimizer.find_gas_stations(f.candidate(DENSE))
        assert [s.mile_marker for s in stations] == pytest.approx([20, 100, 250], abs=1.0)

    async def test_station_seen_by_overlapping_circles_appears_once(self, fake_places):
        # 6 miles from two neighbouring circle centres
        fake_places.places = [f.place("dup", *f.beside(DENSE, 102, 0))]
        stations = await optimizer.find_gas_stations(f.candidate(DENSE))
        here = (fake_places.places[0].location.latitude, fake_places.places[0].location.longitude)
        circles_that_saw_it = sum(
            1
            for r, _ in fake_places.calls
            if f.miles([(r.location_restriction.circle.center.latitude, r.location_restriction.circle.center.longitude), here])
            <= optimizer.STATION_RADIUS_MI
        )
        assert circles_that_saw_it >= 2
        assert [s.name for s in stations] == ["Gas dup"]

    async def test_drops_stations_too_far_off_the_route(self, fake_places):
        fake_places.places = [
            f.place("near", *f.beside(DENSE, 60, 2)),
            f.place("far", *f.beside(DENSE, 61, 6)),
        ]
        stations = await optimizer.find_gas_stations(f.candidate(DENSE))
        assert [s.name for s in stations] == ["Gas near"]

    async def test_results_are_sorted_by_mile_marker(self, fake_places):
        fake_places.places = [f.place(f"s{m}", *f.beside(DENSE, m, 1)) for m in (250, 20, 140, 60)]
        stations = await optimizer.find_gas_stations(f.candidate(DENSE))
        assert [s.mile_marker for s in stations] == sorted(s.mile_marker for s in stations)

    async def test_no_stations_gives_an_empty_list(self, fake_places):
        assert await optimizer.find_gas_stations(f.candidate(DENSE)) == []

    async def test_prices_and_freshness_come_through(self, fake_places):
        fake_places.places = [
            f.place("fresh", *f.beside(DENSE, 30, 1), price=3.2, age_hours=2),
            f.place("old", *f.beside(DENSE, 90, 1), price=3.9, age_hours=200),
            f.place("none", *f.beside(DENSE, 150, 1), price=None),
        ]
        by_name = {s.name: s for s in await optimizer.find_gas_stations(f.candidate(DENSE))}
        assert (by_name["Gas fresh"].price, by_name["Gas fresh"].source) == (3.2, "live")
        assert (by_name["Gas old"].price, by_name["Gas old"].source) == (3.9, "estimated")
        assert by_name["Gas none"].price == optimizer.STUB_GAS_PRICE

    async def test_google_errors_become_upstream_errors(self, fake_places):
        fake_places.error = f.api_error("quota exceeded")
        with pytest.raises(optimizer.OptimizationError) as err:
            await optimizer.find_gas_stations(f.candidate(DENSE))
        assert err.value.code == "upstream_error"
        assert "quota exceeded" in err.value.message


@pytest.mark.unit
class TestPlacesCacheAndLimits:
    async def test_repeat_search_hits_the_cache(self, fake_places):
        await optimizer.find_gas_stations(f.candidate(DENSE))
        first = len(fake_places.calls)
        await optimizer.find_gas_stations(f.candidate(DENSE))
        assert len(fake_places.calls) == first

    async def test_candidates_sharing_a_road_share_searches(self, fake_places):
        await asyncio.gather(
            optimizer.find_gas_stations(f.candidate(DENSE)),
            optimizer.find_gas_stations(f.candidate(DENSE)),
        )
        assert len(fake_places.calls) == math.floor(DENSE_MILES / optimizer.STATION_SAMPLE_MI) + 2

    async def test_cached_results_still_give_the_same_stations(self, fake_places):
        fake_places.places = [f.place(f"s{m}", *f.beside(DENSE, m, 1)) for m in (20, 100, 250)]
        a = await optimizer.find_gas_stations(f.candidate(DENSE))
        b = await optimizer.find_gas_stations(f.candidate(DENSE))
        assert [s.name for s in a] == [s.name for s in b] and len(a) == 3

    async def test_cache_expires(self, fake_places, monkeypatch):
        await optimizer.find_gas_stations(f.candidate(DENSE))
        first = len(fake_places.calls)
        real = optimizer.time.monotonic()
        monkeypatch.setattr(optimizer.time, "monotonic", lambda: real + optimizer.PLACES_CACHE_TTL_S + 1)
        await optimizer.find_gas_stations(f.candidate(DENSE))
        assert len(fake_places.calls) == 2 * first

    async def test_failures_are_not_cached(self, fake_places):
        fake_places.error = f.api_error("boom")
        with pytest.raises(optimizer.OptimizationError):
            await optimizer.find_gas_stations(f.candidate(DENSE))
        fake_places.error = None
        assert await optimizer.find_gas_stations(f.candidate(DENSE)) == []

    async def test_quota_errors_are_retried(self, fake_places, no_delay):
        real = fake_places.search_nearby
        failures = [f.ResourceExhausted("quota")] * 2

        def flaky(request, metadata):
            if failures:
                raise failures.pop()
            return real(request, metadata)

        fake_places.search_nearby = flaky
        await optimizer.find_gas_stations(f.candidate(DENSE))
        assert fake_places.calls  # got through after two 429s

    async def test_persistent_quota_errors_become_upstream_errors(
        self, fake_places, no_delay, monkeypatch
    ):
        monkeypatch.setattr(settings, "places_requests_per_minute", 10_000)
        fake_places.error = f.ResourceExhausted("Quota exceeded")
        with pytest.raises(optimizer.OptimizationError) as err:
            await optimizer.find_gas_stations(f.candidate(DENSE))
        assert err.value.code == "upstream_error" and "Quota exceeded" in err.value.message

    async def test_requests_per_minute_are_limited(self, fake_places, monkeypatch):
        monkeypatch.setattr(settings, "places_requests_per_minute", 5)
        sleeps = []

        async def fake_sleep(s):
            sleeps.append(s)
            # advance the clock so the window frees up
            optimizer._places_calls.clear()

        monkeypatch.setattr(optimizer.asyncio, "sleep", fake_sleep)
        await optimizer.find_gas_stations(f.candidate(DENSE))
        assert sleeps and max(len(optimizer._places_calls), 0) <= 5


@pytest.mark.unit
class TestFindEvStations:
    @staticmethod
    def chargers(*specs):
        """specs: (mile, off_mi, ev_pricing)"""
        return [
            f.nrel_station(f"c{i}", *f.beside(DENSE, mile, off), pricing)
            for i, (mile, off, pricing) in enumerate(specs)
        ]

    async def test_request_shape(self, fake_nrel):
        await optimizer.find_ev_stations(f.candidate(DENSE))
        (call,) = fake_nrel.calls
        data = call["data"]

        assert call["url"] == f"{settings.nrel_base_url}/nearby-route.json"
        assert call["timeout"] > 0
        assert data["api_key"] == "TEST_KEY"
        assert data["route"].startswith("LINESTRING(")
        assert data["distance"] == optimizer.MAX_DETOUR_MI / 2
        assert (data["fuel_type"], data["ev_charging_level"]) == ("ELEC", "dc_fast")
        assert (data["access"], data["status"]) == ("public", "E")

    async def test_listed_prices_are_used(self, fake_nrel):
        fake_nrel.stations = self.chargers((30, 1, "$0.40/kWh"), (90, 1, "$0.52 per kWh"))
        stations = await optimizer.find_ev_stations(f.candidate(DENSE))
        assert [s.price for s in stations] == [0.40, 0.52]

    async def test_free_chargers_cost_nothing(self, fake_nrel):
        fake_nrel.stations = self.chargers((30, 1, "Free"))
        (s,) = await optimizer.find_ev_stations(f.candidate(DENSE))
        assert s.price == 0.0

    async def test_unparseable_price_uses_median_of_listed_prices(self, fake_nrel):
        fake_nrel.stations = self.chargers(
            (20, 1, "$0.40/kWh"),
            (80, 1, "$0.50/kWh"),
            (140, 1, "$0.60/kWh"),
            (200, 1, "Free"),  # free chargers don't drag the median down
            (250, 1, "$0.30/min"),
            (270, 1, None),
        )
        stations = await optimizer.find_ev_stations(f.candidate(DENSE))
        assert [s.price for s in stations[-2:]] == [0.5, 0.5]

    async def test_too_few_listed_prices_falls_back_to_stub(self, fake_nrel):
        fake_nrel.stations = self.chargers((20, 1, "$0.90/kWh"), (80, 1, None))
        stations = await optimizer.find_ev_stations(f.candidate(DENSE))
        assert stations[1].price == optimizer.STUB_EV_PRICE

    async def test_all_ev_prices_are_marked_estimated(self, fake_nrel):
        fake_nrel.stations = self.chargers((20, 1, "$0.40/kWh"), (80, 1, None), (90, 1, "Free"))
        stations = await optimizer.find_ev_stations(f.candidate(DENSE))
        assert {s.source for s in stations} == {"estimated"}

    async def test_drops_chargers_too_far_off_the_route(self, fake_nrel):
        fake_nrel.stations = self.chargers((50, 1, None), (100, 7, None))
        stations = await optimizer.find_ev_stations(f.candidate(DENSE))
        assert [s.name for s in stations] == ["Charger c0"]

    async def test_sorted_with_mile_marker_detour_and_address(self, fake_nrel):
        fake_nrel.stations = self.chargers((200, 1, None), (40, 2, None))
        first, second = await optimizer.find_ev_stations(f.candidate(DENSE))

        assert first.mile_marker == pytest.approx(40, abs=1.0)
        assert second.mile_marker == pytest.approx(200, abs=1.0)
        assert first.detour_mi == pytest.approx(4.0, abs=1.0)
        assert first.address == "c1 Charge Ave, Bakersfield, CA"

    async def test_missing_address_parts_are_skipped(self, fake_nrel):
        st = f.nrel_station("x", *f.beside(DENSE, 50, 1))
        st["street_address"] = None
        fake_nrel.stations = [st]
        (s,) = await optimizer.find_ev_stations(f.candidate(DENSE))
        assert s.address == "Bakersfield, CA"

    async def test_no_chargers_gives_an_empty_list(self, fake_nrel):
        assert await optimizer.find_ev_stations(f.candidate(DENSE)) == []

    @pytest.mark.parametrize(
        "error", [pytest.param(None, id="connection"), pytest.param("http", id="http-422")]
    )
    async def test_http_failures_become_upstream_errors(self, fake_nrel, error):
        fake_nrel.error = (
            f.http_error() if error else optimizer.requests.ConnectionError("down")
        )
        with pytest.raises(optimizer.OptimizationError) as err:
            await optimizer.find_ev_stations(f.candidate(DENSE))
        assert err.value.code == "upstream_error"


@pytest.mark.unit
class TestFindCorridorStationsDispatch:
    async def test_gas_vehicle_uses_places_only(self, fake_places, fake_nrel):
        await optimizer.find_corridor_stations(f.request(f.gas_vehicle()), f.candidate(DENSE))
        assert fake_places.calls and not fake_nrel.calls

    async def test_hybrid_uses_places_only(self, fake_places, fake_nrel):
        hybrid = f.gas_vehicle().model_copy(update={"type": "hybrid"})
        await optimizer.find_corridor_stations(f.request(hybrid), f.candidate(DENSE))
        assert fake_places.calls and not fake_nrel.calls

    async def test_ev_uses_nrel_only(self, fake_places, fake_nrel):
        await optimizer.find_corridor_stations(f.request(f.ev_vehicle()), f.candidate(DENSE))
        assert fake_nrel.calls and not fake_places.calls


# -------------------------------------------------------------- integration


@pytest.mark.integration
class TestStationSearchIntegration:
    async def test_stage_one_candidates_feed_the_gas_search(self, fake_routes, fake_places):
        fake_routes.routes = [f.api_route(DENSE, meters=round(DENSE_MILES * 1609.344))]
        fake_places.places = [
            f.place(f"s{m}", *f.beside(DENSE, m, 1), price=3.0 + m / 1000, age_hours=m)
            for m in range(10, 300, 10)
        ]
        (c,) = await optimizer.get_routes(
            Coordinate(lat=f.A[0], lng=f.A[1]), Coordinate(lat=f.B[0], lng=f.B[1])
        )
        stations = await optimizer.find_corridor_stations(f.request(), c)

        assert len(stations) == 29
        assert all(0 <= s.mile_marker <= c.distance_mi for s in stations)
        assert [s.mile_marker for s in stations] == sorted(s.mile_marker for s in stations)
        # price freshness travelled with the data: <=48h old is live
        assert {s.source for s in stations if s.mile_marker < 40} == {"live"}
        assert {s.source for s in stations if s.mile_marker > 60} == {"estimated"}

    async def test_polyline_round_trip_does_not_lose_stations(self, fake_places):
        decoded = decode_polyline(encode_polyline(DENSE))
        fake_places.places = [f.place(f"s{m}", *f.beside(DENSE, m, 2)) for m in range(5, 300, 7)]
        stations = await optimizer.find_gas_stations(f.candidate(decoded))
        assert len(stations) == len(fake_places.places)

    async def test_ev_search_end_to_end(self, fake_nrel):
        fake_nrel.stations = [
            f.nrel_station(f"c{m}", *f.beside(DENSE, m, 1), pricing)
            for m, pricing in ((40, "$0.45/kWh"), (120, "$0.55/kWh"), (200, "$0.65/kWh"), (260, None))
        ]
        stations = await optimizer.find_corridor_stations(f.request(f.ev_vehicle()), f.candidate(DENSE))
        assert [s.price for s in stations] == [0.45, 0.55, 0.65, 0.55]  # last gets the median
