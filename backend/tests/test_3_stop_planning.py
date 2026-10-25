"""Stage 3 - optimizing: choose where to stop and what the energy costs.

plan_stops is the greedy "next cheaper station" planner. The first group of tests
pins down what any planner must satisfy (legs drivable on the usable range, stops
from the supplied stations, tank within bounds); the price-aware group checks the
greedy choices themselves. Fuel is tracked in miles of range: 250 mi tank, 25 mi
reserve, 25 mpg.
"""

import pytest

from app.schemas.optimize import Stop
from app.services import optimizer
from tests import factories as f

ROUTE = f.line(307)
MILES = f.miles(ROUTE)  # ~306

GAS = f.gas_vehicle(mpg=25, tank_gal=10)  # 250 mi range, 225 usable at the 10% default reserve
USABLE = 225.0


def every(step, start=None, last=None, **kw):
    start = start or step
    last = last or MILES - 1
    return [f.station(m, **kw) for m in range(int(start), int(last), step)]


def plan(stations, vehicle=GAS, candidate=None, **options):
    return optimizer.plan_stops(f.request(vehicle, **options), candidate or f.candidate(ROUTE), stations)


def make_stop(price, mile=50.0, amount=1) -> Stop:
    return Stop(
        id=f"s{mile}", type="fuel", name="S", address="a", lat=0, lng=0, mile_marker=mile,
        price=price, price_unit="gal", amount=amount, cost=round(price * amount, 2), detour_mi=0, detour_min=0,
        price_source="live",
    )


def simulate(stops, c=None, vehicle=GAS, start_pct=100, reserve_pct=10):
    """Replay a plan; return (lowest fuel seen, highest fuel seen) in miles."""
    c = c or f.candidate(ROUTE)
    full = optimizer.full_range_mi(vehicle)
    per_mile = 1 / vehicle.mpg
    fuel, here, lo, hi = full * start_pct / 100, 0.0, full, 0.0
    for s in stops:
        fuel -= s.mile_marker - here
        lo = min(lo, fuel)
        fuel += s.amount / per_mile
        hi = max(hi, fuel)
        here = s.mile_marker
    fuel -= c.distance_mi - here
    return min(lo, fuel), hi


# --------------------------------------------------------------------- unit


@pytest.mark.unit
class TestFullRange:
    def test_gas_is_mpg_times_tank(self):
        assert optimizer.full_range_mi(f.gas_vehicle(mpg=30, tank_gal=12)) == 360

    def test_hybrid_is_mpg_times_tank(self):
        hybrid = f.gas_vehicle(mpg=50, tank_gal=9).model_copy(update={"type": "hybrid"})
        assert optimizer.full_range_mi(hybrid) == 450

    def test_ev_is_rated_range(self):
        assert optimizer.full_range_mi(f.ev_vehicle(range_mi=280)) == 280


@pytest.mark.unit
class TestPlanStops:
    def test_no_stops_when_the_destination_is_within_the_starting_range(self):
        short = f.candidate(f.line(11, f.A, (34.5, -118.5)))  # ~45 mi
        assert plan(every(10, last=40), candidate=short) == []

    def test_a_trip_exactly_at_the_usable_range_needs_no_stop(self):
        c = f.candidate(ROUTE, distance_mi=USABLE)
        assert plan(every(30), candidate=c) == []

    def test_a_trip_just_past_the_usable_range_needs_a_stop(self):
        c = f.candidate(ROUTE, distance_mi=USABLE + 1)
        assert len(plan(every(30), candidate=c)) >= 1

    def test_every_leg_is_drivable_on_the_usable_range(self):
        stops = plan(every(30))
        miles = [0.0, *(s.mile_marker for s in stops), MILES]
        assert stops
        assert all(b - a <= USABLE + 1e-6 for a, b in zip(miles, miles[1:]))

    def test_stops_move_forward_and_come_from_the_given_stations(self):
        stations = every(30)
        stops = plan(stations)
        marks = [s.mile_marker for s in stops]
        assert marks == sorted(set(marks))
        assert set(marks) <= {s.mile_marker for s in stations}

    def test_unsorted_stations_are_fine(self):
        stations = every(30)
        assert plan(list(reversed(stations))) == plan(stations)

    def test_a_station_exactly_at_the_limit_of_reach_can_be_used(self):
        stops = plan([f.station(USABLE)])
        assert [s.mile_marker for s in stops] == [USABLE]

    def test_lower_starting_fuel_brings_the_first_stop_forward(self):
        full = plan(every(10))[0].mile_marker
        low = plan(every(10), start_fuel_pct=40)[0].mile_marker
        assert low <= 75  # 250 * 0.40 - 25 mi reserve
        assert low < full

    def test_a_bigger_reserve_shortens_the_legs(self):
        stops = plan(every(10), reserve_pct=40)
        miles = [0.0, *(s.mile_marker for s in stops), MILES]
        assert all(b - a <= 250 * 0.6 + 1e-6 for a, b in zip(miles, miles[1:]))

    def test_total_bought_covers_the_trip_down_to_the_reserve(self):
        stops = plan(every(30))
        bought_mi = sum(s.amount for s in stops) * 25
        assert bought_mi == pytest.approx(MILES + 25 - 250, abs=0.5)

    def test_cost_is_amount_times_price(self):
        stops = plan(every(30, price=3.8))
        assert all(s.cost == pytest.approx(s.amount * 3.8, abs=0.01) for s in stops)

    def test_gas_stops_are_fuel_in_gallons(self):
        stops = plan(every(30))
        assert {(s.type, s.price_unit) for s in stops} == {("fuel", "gal")}

    def test_ev_stops_are_charging_in_kwh(self):
        ev = f.ev_vehicle(range_mi=200, battery_kwh=60)  # 0.3 kWh/mi
        stops = plan(every(30), vehicle=ev)
        assert stops
        assert {(s.type, s.price_unit) for s in stops} == {("charging", "kWh")}
        assert sum(s.amount for s in stops) == pytest.approx((MILES + 20 - 200) * 0.3, abs=0.1)

    def test_ids_are_unique_and_tagged_with_the_route(self):
        stops = plan(every(30), candidate=f.candidate(ROUTE, tag="fastest"))
        assert [s.id for s in stops] == [f"fastest-stop-{i + 1}" for i in range(len(stops))]

    def test_station_details_and_price_source_carry_over(self):
        station = f.station(
            100, price=3.31, source="estimated", name="Chevron", address="9 Oak",
            lat=35.5, lng=-119.5, detour_mi=1.2, detour_min=2.4,
        )
        (stop,) = plan([station], candidate=f.candidate(ROUTE, distance_mi=260))

        assert (stop.name, stop.address, stop.lat, stop.lng) == ("Chevron", "9 Oak", 35.5, -119.5)
        assert (stop.price, stop.price_source) == (3.31, "estimated")
        assert (stop.detour_mi, stop.detour_min) == (1.2, 2.4)

    def test_no_stations_on_a_long_trip_is_infeasible(self):
        with pytest.raises(optimizer.OptimizationError) as err:
            plan([])
        assert err.value.code == "no_feasible_route"

    def test_a_gap_wider_than_the_range_is_infeasible(self):
        with pytest.raises(optimizer.OptimizationError) as err:
            plan([f.station(30), f.station(280)])  # 250 miles between them
        assert err.value.code == "no_feasible_route"
        assert "mile 30" in err.value.message

    def test_starting_below_the_reserve_is_infeasible(self):
        with pytest.raises(optimizer.OptimizationError) as err:
            plan(every(30), start_fuel_pct=5, reserve_pct=10)
        assert err.value.code == "no_feasible_route"
        assert "reserve" in err.value.message


@pytest.mark.unit
class TestEnergyCost:
    def test_trip_with_no_stops_uses_the_flat_default_gas_price(self):
        # 300 mi / 30 mpg = 10 gal
        assert optimizer.energy_cost(f.gas_vehicle(mpg=30), 300, []) == 34.5

    def test_trip_with_no_stops_uses_the_flat_default_ev_price(self):
        assert optimizer.energy_cost(f.ev_vehicle(300, 75), 300, []) == 31.5

    def test_uses_the_average_price_weighted_by_amount_bought(self):
        stops = [make_stop(3.0, amount=1), make_stop(4.0, amount=3)]
        # 100 mi / 25 mpg = 4 gal at (3*1 + 4*3) / 4 = $3.75
        assert optimizer.energy_cost(GAS, 100, stops) == 15.0

    def test_cheaper_stops_lower_the_cost(self):
        cheap = optimizer.energy_cost(GAS, 100, [make_stop(3.0)])
        dear = optimizer.energy_cost(GAS, 100, [make_stop(4.5)])
        assert cheap < dear

    def test_rounds_to_cents(self):
        cost = optimizer.energy_cost(GAS, 123.456, [make_stop(3.333)])
        assert cost == round(cost, 2)


# -------------------------------------------------------------- integration


@pytest.mark.integration
class TestStopPlanningIntegration:
    async def test_gas_stops_planned_from_searched_stations(self, fake_places):
        fake_places.places = [
            f.place(f"s{m}", *f.beside(ROUTE, m, 1), price=3.0 + (m % 50) / 100)
            for m in range(10, 300, 10)
        ]
        c = f.candidate(ROUTE)
        req = f.request(GAS)
        stations = await optimizer.find_corridor_stations(req, c)
        stops = optimizer.plan_stops(req, c, stations)

        miles = [0.0, *(s.mile_marker for s in stops), c.distance_mi]
        assert stops
        assert all(b - a <= USABLE + 0.5 for a, b in zip(miles, miles[1:]))
        assert {s.name for s in stops} <= {s.name for s in stations}
        energy = optimizer.energy_cost(req.vehicle, c.distance_mi, stops)
        prices = [s.price for s in stops]
        assert energy == pytest.approx(c.distance_mi / 25 * sum(prices) / len(prices), abs=0.01)

    async def test_ev_stops_planned_from_nrel_chargers(self, fake_nrel):
        fake_nrel.stations = [
            f.nrel_station(f"c{m}", *f.beside(ROUTE, m, 1), "$0.45/kWh") for m in range(40, 300, 40)
        ]
        ev = f.ev_vehicle(range_mi=200, battery_kwh=60)
        c, req = f.candidate(ROUTE), f.request(ev)
        stations = await optimizer.find_corridor_stations(req, c)
        stops = optimizer.plan_stops(req, c, stations)

        assert stops and {s.type for s in stops} == {"charging"}
        assert {s.price_source for s in stops} == {"estimated"}
        assert all(s.price == 0.45 for s in stops)

    async def test_sparse_chargers_make_the_trip_infeasible(self, fake_nrel):
        fake_nrel.stations = [f.nrel_station("only", *f.beside(ROUTE, 30, 1), None)]
        ev = f.ev_vehicle(range_mi=150, battery_kwh=45)
        c, req = f.candidate(ROUTE), f.request(ev)
        stations = await optimizer.find_corridor_stations(req, c)
        with pytest.raises(optimizer.OptimizationError) as err:
            optimizer.plan_stops(req, c, stations)
        assert err.value.code == "no_feasible_route"


# ---------------------------------------------------------- price-aware, unit

LONG = f.candidate(ROUTE, distance_mi=600)


@pytest.mark.unit
class TestCheapestNextStation:
    def test_buys_only_enough_to_reach_a_cheaper_station(self):
        stations = [f.station(80, 4.0), f.station(160, 3.0), f.station(250, 3.5)]
        stops = plan(stations, start_fuel_pct=50)

        assert [s.mile_marker for s in stops] == [80, 160]
        # at 80 with 45 mi left: reach 160 with the 25 mi reserve intact -> 60 mi
        assert stops[0].amount == pytest.approx(60 / 25, abs=0.01)
        # at 160 with 25 mi left: the destination is in reach -> 146 mi
        assert stops[1].amount == pytest.approx(146 / 25, abs=0.01)

    def test_fills_up_when_nothing_cheaper_is_in_reach(self):
        stations = [f.station(100, 3.0), f.station(300, 4.0), f.station(400, 5.0), f.station(520, 4.0)]
        stops = plan(stations, candidate=LONG)

        assert [s.mile_marker for s in stops] == [100, 300, 520]
        assert stops[0].amount == pytest.approx(100 / 25, abs=0.01)  # 150 mi left -> full 250
        assert stops[1].amount == pytest.approx(200 / 25, abs=0.01)  # 50 mi left -> full
        assert stops[2].amount == pytest.approx(75 / 25, abs=0.01)  # just enough for 80 mi + reserve

    def test_a_cheap_station_outweighs_stopping_early_at_a_dear_one(self):
        # 100 is in reach at 4.00, 200 at 3.00: skip straight to the cheap one
        stops = plan([f.station(100, 4.0), f.station(200, 3.0)])
        assert [s.mile_marker for s in stops] == [200]
        assert stops[0].price == 3.0

    def test_first_stop_is_the_cheapest_in_starting_range(self):
        stops = plan([f.station(100, 3.9), f.station(150, 3.1), f.station(220, 3.6)])
        assert [s.price for s in stops] == [3.1]

    def test_ties_prefer_the_farther_station(self):
        stops = plan([f.station(100, 3.5), f.station(200, 3.5)])
        assert [s.mile_marker for s in stops] == [200]

    def test_fills_up_at_a_cheap_station_before_a_run_of_dear_ones(self):
        stations = [f.station(150, 2.9), f.station(210, 4.5), f.station(300, 4.6), f.station(450, 4.5)]
        stops = plan(stations, candidate=LONG)
        assert stops[0].price == 2.9
        assert stops[0].amount == pytest.approx(150 / 25, abs=0.01)  # 100 mi left -> full 250

    def test_unreachable_gap_raises(self):
        with pytest.raises(optimizer.OptimizationError) as err:
            plan([f.station(100), f.station(400)], candidate=LONG)
        assert err.value.code == "no_feasible_route"

    def test_no_stations_on_a_long_trip_raises(self):
        with pytest.raises(optimizer.OptimizationError) as err:
            plan([])
        assert err.value.code == "no_feasible_route"

    def test_start_fuel_below_reserve_raises(self):
        with pytest.raises(optimizer.OptimizationError):
            plan(every(30), start_fuel_pct=5)

    @pytest.mark.parametrize("seed", range(20))
    def test_tank_stays_between_reserve_and_full_for_any_prices(self, seed):
        import random

        rng = random.Random(seed)
        stations = [f.station(m, round(rng.uniform(2.8, 4.6), 2)) for m in range(15, 585, 15)]
        pct = rng.choice([100, 60, 35])
        stops = plan(stations, candidate=LONG, start_fuel_pct=pct)

        lo, hi = simulate(stops, LONG, start_pct=pct)
        assert lo >= 25 - 0.5
        assert hi <= 250 + 0.5
