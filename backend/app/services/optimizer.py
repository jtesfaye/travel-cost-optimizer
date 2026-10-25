"""Optimization pipeline.

Stages:

    1. generate_candidate_routes -> Routes API (alternatives, tolls, polyline)
    2. find_corridor_stations    -> Places (gas) / NREL (EV) stations + prices
    3. plan_stops                -> greedy "next cheaper station" planner
"""

import asyncio
import bisect
import math
import re
import random
import statistics
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.schemas.optimize import (
    Cost,
    OptimizeRequest,
    OptimizeResult,
    RouteResult,
    Stop,
    Toll,
    VehicleInput,
    Coordinate
)
from app.core.config import settings
from app.services.geo import decode_polyline, encode_polyline, haversine_mi, interpolate
import requests
from google.api_core.exceptions import GoogleAPICallError, ResourceExhausted, ServiceUnavailable
from google.maps import places_v1, routing_v2

# Authenticate with the Maps API key (not Application Default Credentials).
client = routing_v2.RoutesClient(client_options={"api_key": settings.maps_api_key})
places_client = places_v1.PlacesClient(client_options={"api_key": settings.maps_api_key})

ProgressFn = Callable[[str, float], None]

METER_CONV = .0006213712  # miles per meter
METERS_PER_MI = 1609.344
STUB_GAS_PRICE = 3.45  # $/gal
STUB_EV_PRICE = 0.42  # $/kWh

MAX_DETOUR_MI = 8  # round-trip miles off the route; farther stations are dropped
# A station up to MAX_DETOUR_MI / 2 off the route is at most
# sqrt((SAMPLE / 2)^2 + (MAX_DETOUR / 2)^2) = 7.2 mi from the nearest circle
# centre, so with these values no in-budget station falls between circles.
STATION_SAMPLE_MI = 12  # spacing of search circles along the route
STATION_RADIUS_MI = 8
DETOUR_SPEED_MPH = 30
PRICE_FRESH_HOURS = 48  # older Places prices still count, but as "estimated"
MAX_CONCURRENT_SEARCHES = 8
# Places searches are cached by snapped search centre, so overlapping circles
# (across alternative routes and repeat requests) cost one API call.
PLACES_CACHE_TTL_S = 3600
PLACES_CACHE_MAX_ENTRIES = 5000
PLACES_GRID_DEG = 0.02  # search centres snap to this grid (~1.4 mi of latitude)
# Snapping moves a centre by at most ~0.98 mi; widen the circle by that much so
# it still covers the unsnapped one.
PLACES_SNAP_SLACK_MI = 1.0
PLACES_MAX_RETRIES = 3
PLACES_RETRY_BASE_S = 1.0
NREL_ROUTE_SPACING_MI = 0.5  # thin the polyline before sending it to NREL


class OptimizationError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Candidate:
    """A raw route from the routing provider, before pricing."""

    tag: str
    label: str
    description: str
    distance_mi: float
    duration_min: float
    toll_cost: float
    points: list[tuple[float, float]]
    tolls: list[Toll] = field(default_factory=list)


@dataclass
class Station:
    name: str
    address: str
    lat: float
    lng: float
    mile_marker: float
    price: float
    detour_mi: float
    detour_min: float
    source: str  # "live" | "estimated"


"""Cost of the energy consumed over `distance_mi` at the flat default price, for
when no real price is available (e.g. a trip that needs no stop)."""
def derive_energy_cost(distance_mi: float, vehicle: VehicleInput) -> float:
    
    if vehicle.type == "ev":
        return round(distance_mi * vehicle.battery_kwh / vehicle.range_mi * STUB_EV_PRICE, 2)
    return round(distance_mi / vehicle.mpg * STUB_GAS_PRICE, 2)


"""
Convert a Routes API TollInfo into Toll entries (USD only).
The API gives no per-gantry names, only a total per currency, and omits
estimated_price when it knows tolls exist but not their price.
"""
def build_toll_list(tollInfo) -> list[Toll]:
    
    return [
        Toll(name="Route tolls", cost=round(price.units + price.nanos / 1e9, 2))
        for price in tollInfo.estimated_price
        if price.currency_code == "USD"
    ]

async def get_routes(origin: Coordinate, destination: Coordinate) -> list[Candidate]:
    org = routing_v2.Waypoint(
        location=routing_v2.Location(
            lat_lng={"latitude": origin.lat, "longitude": origin.lng}
        )
    )
    dest = routing_v2.Waypoint(
        location=routing_v2.Location(
            lat_lng={"latitude": destination.lat, "longitude": destination.lng}
        )
    )

    request = routing_v2.ComputeRoutesRequest(
        origin=org,
        destination=dest,
        travel_mode=routing_v2.RouteTravelMode.DRIVE,
        compute_alternative_routes=True,
        extra_computations=[routing_v2.ComputeRoutesRequest.ExtraComputation.TOLLS],
    )

    metadata = [
        (
            "x-goog-fieldmask",
            "routes.description,routes.duration,routes.distanceMeters,"
            "routes.polyline.encodedPolyline,routes.travelAdvisory.tollInfo",
        )
    ]

    response = await asyncio.to_thread(
        client.compute_routes, request=request, metadata=metadata
    )
    if not response.routes:
        raise OptimizationError("no_feasible_route", "No route found between these points.")

    candidates = []
    for idx, route in enumerate(response.routes):
        tolls = build_toll_list(route.travel_advisory.toll_info)
        candidates.append(
            Candidate(
                tag=str(idx),
                label=f"Route {idx + 1}",
                description=route.description,
                distance_mi=round(route.distance_meters * METER_CONV, 1),
                duration_min=round(route.duration.total_seconds() / 60),  # proto-plus gives timedelta
                toll_cost=sum(t.cost for t in tolls),
                tolls=tolls,
                points=decode_polyline(route.polyline.encoded_polyline),
            )
        )
    return candidates


async def generate_candidate_routes(req: OptimizeRequest) -> list[Candidate]:
    return await get_routes(req.origin, req.destination)


def _money(m) -> float:
    return int(m.units) + m.nanos / 1e9


def _station_from_place(place, route_mile: float, off_route_mi: float) -> Station:
    price, source = STUB_GAS_PRICE, "estimated"
    for fp in place.fuel_options.fuel_prices:
        if (
            fp.type_ == places_v1.FuelOptions.FuelPrice.FuelType.REGULAR_UNLEADED
            and fp.price.currency_code == "USD"
        ):
            price = round(_money(fp.price), 3)
            age = datetime.now(timezone.utc) - fp.update_time
            if age.total_seconds() <= PRICE_FRESH_HOURS * 3600:
                source = "live"
            break

    detour_mi = round(2 * off_route_mi, 1)
    return Station(
        name=place.display_name.text,
        address=place.formatted_address,
        lat=place.location.latitude,
        lng=place.location.longitude,
        mile_marker=round(route_mile, 1),
        price=price,
        detour_mi=detour_mi,
        detour_min=round(detour_mi / DETOUR_SPEED_MPH * 60, 1),
        source=source,
    )

def _cumulative_miles(pts: list[tuple[float, float]]) -> list[float]:
    """Miles along the polyline at each vertex."""
    cumulative = [0.0]
    for a, b in zip(pts, pts[1:]):
        cumulative.append(cumulative[-1] + haversine_mi(a, b))
    return cumulative


def _point_at(
    pts: list[tuple[float, float]], cumulative: list[float], mile: float
) -> tuple[float, float]:
    """The coordinate `mile` miles along the polyline."""
    i = min(max(bisect.bisect_right(cumulative, mile) - 1, 0), len(pts) - 2)
    seg = cumulative[i + 1] - cumulative[i]
    return interpolate(pts[i], pts[i + 1], (mile - cumulative[i]) / seg) if seg else pts[i]


# ---------------------------------------------------------------- Places search

_places_cache: dict[tuple[int, int], tuple[float, places_v1.SearchNearbyResponse]] = {}
_places_inflight: dict[tuple[int, int], asyncio.Task] = {}
_places_calls: deque[float] = deque()  # monotonic times of recent API calls


def _clear_places_state() -> None:
    _places_cache.clear()
    _places_inflight.clear()
    _places_calls.clear()


async def _acquire_places_slot() -> None:
    """Sliding-window limiter: at most settings.places_requests_per_minute calls
    in any 60s. No awaits between the check and the append, so no lock is needed."""
    while True:
        now = time.monotonic()
        while _places_calls and now - _places_calls[0] >= 60:
            _places_calls.popleft()
        if len(_places_calls) < settings.places_requests_per_minute:
            _places_calls.append(now)
            return
        await asyncio.sleep(60 - (now - _places_calls[0]))


async def _search_nearby(cell: tuple[int, int]) -> places_v1.SearchNearbyResponse:
    """One Places call for a grid cell, rate limited, retrying quota/outage errors."""
    center = {"latitude": cell[0] * PLACES_GRID_DEG, "longitude": cell[1] * PLACES_GRID_DEG}
    request = places_v1.SearchNearbyRequest(
        included_types=["gas_station"],
        max_result_count=20,
        rank_preference=places_v1.SearchNearbyRequest.RankPreference.DISTANCE,
        location_restriction=places_v1.SearchNearbyRequest.LocationRestriction(
            circle=places_v1.Circle(
                center=center,
                radius=(STATION_RADIUS_MI + PLACES_SNAP_SLACK_MI) * METERS_PER_MI,
            )
        ),
    )
    metadata = [
        (
            "x-goog-fieldmask",
            "places.id,places.displayName,places.formattedAddress,places.location,"
            "places.fuelOptions",
        )
    ]
    for attempt in range(PLACES_MAX_RETRIES + 1):
        await _acquire_places_slot()
        try:
            return await asyncio.to_thread(
                places_client.search_nearby, request=request, metadata=metadata
            )
        except (ResourceExhausted, ServiceUnavailable):
            if attempt == PLACES_MAX_RETRIES:
                raise
            await asyncio.sleep(PLACES_RETRY_BASE_S * 2**attempt * (1 + random.random() / 4))
    raise AssertionError("unreachable")


async def _cached_search(center: tuple[float, float]) -> places_v1.SearchNearbyResponse:
    """Cached, de-duplicated Places search around `center` (snapped to the grid).
    Concurrent callers for the same cell share one in-flight request; failures
    are never cached."""
    cell = (round(center[0] / PLACES_GRID_DEG), round(center[1] / PLACES_GRID_DEG))
    now = time.monotonic()
    hit = _places_cache.get(cell)
    if hit and hit[0] > now:
        return hit[1]

    task = _places_inflight.get(cell)
    if task is None:

        async def fetch():
            resp = await _search_nearby(cell)
            if len(_places_cache) >= PLACES_CACHE_MAX_ENTRIES:
                _places_cache.pop(next(iter(_places_cache)))  # oldest insertion
            _places_cache[cell] = (time.monotonic() + PLACES_CACHE_TTL_S, resp)
            return resp

        task = asyncio.create_task(fetch())
        _places_inflight[cell] = task
        task.add_done_callback(lambda _t: _places_inflight.pop(cell, None))
    return await asyncio.shield(task)


async def find_gas_stations(c: Candidate) -> list[Station]:
    """Search for stations in overlapping circles along the whole route and let
    the planner pick; no fuel simulation is needed to decide where to look.

    Prices come from Places `fuelOptions` (regular unleaded) and are "live" when
    recent. Stations with no price fall back to the flat stub price, "estimated".
    """
    pts = c.points

    cumulative = _cumulative_miles(pts)

    # one search centre every STATION_SAMPLE_MI along the route (not snapped to
    # vertices, which can be far apart), always including start and end
    total = cumulative[-1]
    center_miles = [m * STATION_SAMPLE_MI for m in range(int(total // STATION_SAMPLE_MI) + 1)]
    if total - center_miles[-1] > 1e-6:
        center_miles.append(total)
    centers = [(mile, _point_at(pts, cumulative, mile)) for mile in center_miles]

    sem = asyncio.Semaphore(MAX_CONCURRENT_SEARCHES)

    async def search(center: tuple[float, float]):
        async with sem:
            return await _cached_search(center)

    # let every search finish (and be cached) even if one fails, so a retry
    # only repeats the failed cells
    results = await asyncio.gather(*(search(p) for _, p in centers), return_exceptions=True)
    for r in results:
        if isinstance(r, GoogleAPICallError):
            raise OptimizationError("upstream_error", f"Station search failed: {r.message}") from r
        if isinstance(r, BaseException):
            raise r
    responses = results

    stations: dict[str, Station] = {}
    for (center_mile, _), resp in zip(centers, responses):
        # only the vertices near this circle can be a station's closest point
        reach = STATION_RADIUS_MI + PLACES_SNAP_SLACK_MI + 1
        lo = max(0, bisect.bisect_left(cumulative, center_mile - reach) - 1)
        hi = min(len(pts), bisect.bisect_right(cumulative, center_mile + reach) + 1)
        for place in resp.places:
            if place.id in stations:
                continue
            here = (place.location.latitude, place.location.longitude)
            idx = min(range(lo, hi), key=lambda j: haversine_mi(here, pts[j]))
            off_route = haversine_mi(here, pts[idx])
            if 2 * off_route > MAX_DETOUR_MI:
                continue
            stations[place.id] = _station_from_place(place, cumulative[idx], off_route)

    return sorted(stations.values(), key=lambda s: s.mile_marker)


def parse_ev_price(text: str | None) -> float | None:
    """$/kWh from NREL's free-text `ev_pricing`; None when it isn't per-kWh
    (per-minute, per-session, "varies") so the caller can fall back."""
    if not text:
        return None
    t = text.lower()
    if m := re.search(r"\$\s*(\d+(?:\.\d+)?)\s*(?:/|per)?\s*kwh", t):
        return float(m.group(1))
    if "$" not in t and re.search(r"\bfree\b", t):
        return 0.0
    return None


def _nearest_vertex(pts: list[tuple[float, float]], here: tuple[float, float]) -> int:
    """Closest polyline vertex: scan every 20th point, then refine around the best."""
    step = 20
    coarse = min(range(0, len(pts), step), key=lambda j: haversine_mi(here, pts[j]))
    lo, hi = max(0, coarse - step), min(len(pts), coarse + step + 1)
    return min(range(lo, hi), key=lambda j: haversine_mi(here, pts[j]))


def _nrel_route_wkt(pts: list[tuple[float, float]], cumulative: list[float]) -> str:
    thinned, next_mile = [], 0.0
    for p, mile in zip(pts, cumulative):
        if mile >= next_mile:
            thinned.append(p)
            next_mile = mile + NREL_ROUTE_SPACING_MI
    if thinned[-1] != pts[-1]:
        thinned.append(pts[-1])
    return "LINESTRING(" + ", ".join(f"{lng:.5f} {lat:.5f}" for lat, lng in thinned) + ")"


async def find_ev_stations(c: Candidate) -> list[Station]:
    """Public DC fast chargers within the detour budget of the route, from NREL's
    Alternative Fuel Stations `nearby-route` search (a single call per route).

    NREL has no live prices, only a listed `ev_pricing` string. Stations whose
    string parses to $/kWh use it; the rest get the median of the parsed prices
    on this route (or the stub price if there are none). Both are "estimated".
    """
    pts = c.points
    cumulative = _cumulative_miles(pts)

    def fetch() -> list[dict]:
        resp = requests.post(
            f"{settings.nrel_base_url}/nearby-route.json",
            data={
                "api_key": settings.nrel_api_key,
                "route": _nrel_route_wkt(pts, cumulative),
                "distance": MAX_DETOUR_MI / 2,
                "fuel_type": "ELEC",
                "ev_charging_level": "dc_fast",
                "access": "public",
                "status": "E",
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["fuel_stations"]

    try:
        raw = await asyncio.to_thread(fetch)
    except requests.RequestException as e:
        raise OptimizationError("upstream_error", f"Charger search failed: {e}") from e

    located = []
    for st in raw:
        here = (st["latitude"], st["longitude"])
        idx = _nearest_vertex(pts, here)
        off_route = haversine_mi(here, pts[idx])
        if 2 * off_route <= MAX_DETOUR_MI:
            located.append((st, cumulative[idx], off_route))

    listed = {st["id"]: parse_ev_price(st.get("ev_pricing")) for st, _, _ in located}
    paid = [p for p in listed.values() if p]
    fallback = round(statistics.median(paid), 3) if len(paid) >= 3 else STUB_EV_PRICE

    stations = []
    for st, mile, off_route in located:
        price = listed[st["id"]]
        detour_mi = round(2 * off_route, 1)
        stations.append(
            Station(
                name=st["station_name"],
                address=", ".join(
                    x for x in (st.get("street_address"), st.get("city"), st.get("state")) if x
                ),
                lat=st["latitude"],
                lng=st["longitude"],
                mile_marker=round(mile, 1),
                price=fallback if price is None else price,
                detour_mi=detour_mi,
                detour_min=round(detour_mi / DETOUR_SPEED_MPH * 60, 1),
                source="estimated",
            )
        )
    return sorted(stations, key=lambda s: s.mile_marker)


async def find_corridor_stations(req: OptimizeRequest, c: Candidate) -> list[Station]:
    if req.vehicle.type == "ev":
        return await find_ev_stations(c)
    return await find_gas_stations(c)


def full_range_mi(v: VehicleInput) -> float:
    return v.range_mi if v.type == "ev" else v.mpg * v.tank_gal

def plan_stops(
    req: OptimizeRequest, c: Candidate, stations: list[Station]
) -> list[Stop]:
    """Greedy "next cheaper station" planner.

    At each station: if a cheaper station (or the destination) is within reach of
    a full tank, buy only enough to get there; otherwise fill up and drive to the
    cheapest station in reach. Fuel is tracked in miles of range and never drops
    below the reserve. From the start nothing can be bought, so the first stop is
    the cheapest station within the starting range.
    """
    v, opts = req.vehicle, req.options
    ev = v.type == "ev"
    full = full_range_mi(v)
    reserve = full * opts.reserve_pct / 100
    fuel = full * opts.start_fuel_pct / 100  # miles of range in the tank
    if fuel - reserve <= 0:
        raise OptimizationError("no_feasible_route", "Starting fuel is below the reserve level.")

    dest = Station("Destination", "", 0.0, 0.0, c.distance_mi, 0.0, 0.0, 0.0, "estimated")
    ahead = sorted(
        [s for s in stations if 0 < s.mile_marker < c.distance_mi] + [dest],
        key=lambda s: s.mile_marker,
    )

    def in_reach(here: float, usable: float) -> list[Station]:
        return [s for s in ahead if here < s.mile_marker <= here + usable]

    def unreachable(here: float, usable: float) -> OptimizationError:
        return OptimizationError(
            "no_feasible_route",
            f"No station reachable within {usable:.0f} miles after mile {here:.0f}.",
        )

    def cheapest(options: list[Station]) -> Station:
        return min(options, key=lambda s: (s.price, -s.mile_marker))

    buys: list[tuple[Station, float]] = []  # (station, miles of range bought)
    here = 0.0
    options = in_reach(here, fuel - reserve)
    if not options:
        raise unreachable(here, fuel - reserve)
    nxt = cheapest(options)
    fuel -= nxt.mile_marker - here
    here = nxt.mile_marker

    while nxt is not dest:
        options = in_reach(here, full - reserve)
        if not options:
            raise unreachable(here, full - reserve)
        cheaper = next((s for s in options if s.price < nxt.price), None)
        if cheaper:
            target = cheaper
            buy = max(0.0, target.mile_marker - here + reserve - fuel)
        else:
            target = cheapest(options)
            buy = full - fuel
        if buy > 1e-9:
            buys.append((nxt, buy))
        fuel += buy - (target.mile_marker - here)
        here = target.mile_marker
        nxt = target

    per_mile = (v.battery_kwh / v.range_mi) if ev else (1 / v.mpg)  # kWh or gal per mile
    stops = []
    for i, (s, buy) in enumerate(buys):
        amount = round(buy * per_mile, 2)
        stops.append(
            Stop(
                id=f"{c.tag}-stop-{i + 1}",
                type="charging" if ev else "fuel",
                name=s.name,
                address=s.address,
                lat=s.lat,
                lng=s.lng,
                mile_marker=s.mile_marker,
                price=s.price,
                price_unit="kWh" if ev else "gal",
                amount=amount,
                cost=round(amount * s.price, 2),
                detour_mi=s.detour_mi,
                detour_min=s.detour_min,
                price_source=s.source,  # type: ignore[arg-type]
            )
        )
    return stops


def energy_cost(v: VehicleInput, distance_mi: float, stops: list[Stop]) -> float:
    """Value the energy *consumed* at the average price actually paid (weighted by
    amount bought), so the starting tank is priced like the rest and routes stay
    comparable. A trip with no stops has no price to go on, so it uses the flat
    default."""
    bought = sum(s.amount for s in stops)
    if bought <= 0:
        return derive_energy_cost(distance_mi, v)
    per_mile = (v.battery_kwh / v.range_mi) if v.type == "ev" else (1 / v.mpg)
    return round(distance_mi * per_mile * sum(s.cost for s in stops) / bought, 2)


# ---------------------------------------------------------------- pipeline


async def optimize(req: OptimizeRequest, report: ProgressFn) -> OptimizeResult:
    report("routing", 0.05)
    candidates = await generate_candidate_routes(req)

    report("pricing", 0.35)
    stations = {c.tag: await find_corridor_stations(req, c) for c in candidates}

    report("optimizing", 0.7)
    routes: list[RouteResult] = []
    for c in candidates:
        stops = plan_stops(req, c, stations[c.tag])
        energy = energy_cost(req.vehicle, c.distance_mi, stops)
        routes.append(
            RouteResult(
                id=f"route-{c.tag}",
                tag=c.tag,  # type: ignore[arg-type]
                label=c.label,
                description=c.description,
                distance_mi=c.distance_mi,
                duration_min=c.duration_min,
                cost=Cost(
                    energy=energy,
                    tolls=c.toll_cost,
                    total=round(energy + c.toll_cost, 2),
                ),
                polyline=encode_polyline(c.points),
                stops=stops,
                tolls=c.tolls,
            )
        )

    best = min(routes, key=lambda r: r.cost.total)
    return OptimizeResult(
        routes=routes,
        recommended_route_id=best.id,
        price_as_of=datetime.now(timezone.utc),
    )
