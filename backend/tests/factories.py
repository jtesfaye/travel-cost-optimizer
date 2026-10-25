"""Builders and fake external services shared by the stage tests."""

from datetime import datetime, timedelta, timezone

import requests
from google.api_core.exceptions import GoogleAPICallError, ResourceExhausted  # noqa: F401
from google.maps import places_v1, routing_v2
from google.type import money_pb2

from app.schemas.optimize import (
    Coordinate,
    OptimizeOptions,
    OptimizeRequest,
    VehicleInput,
)
from app.services.geo import encode_polyline, haversine_mi, interpolate
from app.services.optimizer import Candidate, Station

# ~306 mi, roughly Los Angeles -> San Francisco, as a straight line
A = (34.0, -118.0)
B = (37.0, -122.0)

FuelType = places_v1.FuelOptions.FuelPrice.FuelType


def line(n: int = 61, a=A, b=B) -> list[tuple[float, float]]:
    return [interpolate(a, b, i / (n - 1)) for i in range(n)]


def miles(points) -> float:
    return sum(haversine_mi(p, q) for p, q in zip(points, points[1:]))


def close(got, want, tol: float = 1e-5) -> bool:
    """Point lists match within `tol` degrees (pytest.approx can't compare lists of tuples)."""
    return len(got) == len(want) and all(
        abs(g[0] - w[0]) <= tol and abs(g[1] - w[1]) <= tol for g, w in zip(got, want)
    )


def point_at_mile(points, mile: float) -> tuple[float, float]:
    """The point `mile` miles along the polyline."""
    walked = 0.0
    for p, q in zip(points, points[1:]):
        seg = haversine_mi(p, q)
        if walked + seg >= mile:
            return interpolate(p, q, (mile - walked) / seg)
        walked += seg
    return points[-1]


def beside(points, mile: float, off_mi: float) -> tuple[float, float]:
    """A point `off_mi` miles to the side of the route at `mile` (flat-earth maths,
    fine at these distances)."""
    import math

    lat, lng = point_at_mile(points, mile)
    ahead = point_at_mile(points, mile + 0.5)
    behind = point_at_mile(points, max(mile - 0.5, 0))
    per_deg = 69.17  # miles per degree of latitude
    dy = (ahead[0] - behind[0]) * per_deg
    dx = (ahead[1] - behind[1]) * per_deg * math.cos(math.radians(lat))
    norm = math.hypot(dx, dy)
    nx, ny = -dy / norm, dx / norm
    return (
        lat + ny * off_mi / per_deg,
        lng + nx * off_mi / (per_deg * math.cos(math.radians(lat))),
    )


def candidate(points=None, tag="0", toll_cost=0.0, **kw) -> Candidate:
    points = points or line()
    return Candidate(
        tag=tag,
        label=kw.pop("label", f"Route {tag}"),
        description=kw.pop("description", "test route"),
        distance_mi=kw.pop("distance_mi", round(miles(points), 1)),
        duration_min=kw.pop("duration_min", 300),
        toll_cost=toll_cost,
        points=points,
        **kw,
    )


def gas_vehicle(mpg=25.0, tank_gal=10.0) -> VehicleInput:
    return VehicleInput(type="gas", mpg=mpg, tank_gal=tank_gal)


def ev_vehicle(range_mi=300.0, battery_kwh=75.0) -> VehicleInput:
    return VehicleInput(type="ev", range_mi=range_mi, battery_kwh=battery_kwh)


def request(vehicle=None, a=A, b=B, **options) -> OptimizeRequest:
    return OptimizeRequest(
        origin=Coordinate(lat=a[0], lng=a[1]),
        destination=Coordinate(lat=b[0], lng=b[1]),
        vehicle=vehicle or gas_vehicle(),
        options=OptimizeOptions(**options),
    )


def station(mile, price=3.5, source="live", **kw) -> Station:
    return Station(
        name=kw.pop("name", f"Station {mile}"),
        address=kw.pop("address", "1 Test Rd"),
        lat=kw.pop("lat", 35.0),
        lng=kw.pop("lng", -119.0),
        mile_marker=float(mile),
        price=price,
        detour_mi=kw.pop("detour_mi", 0.5),
        detour_min=kw.pop("detour_min", 1.0),
        source=source,
    )


# ------------------------------------------------------------------ Routes API


def usd(units: int, nanos: int = 0) -> money_pb2.Money:
    return money_pb2.Money(currency_code="USD", units=units, nanos=nanos)


def api_route(
    points=None,
    *,
    meters=160_934,
    minutes=90,
    description="I-5 N",
    tolls=None,
) -> routing_v2.Route:
    return routing_v2.Route(
        distance_meters=meters,
        duration=timedelta(minutes=minutes),
        description=description,
        polyline=routing_v2.Polyline(encoded_polyline=encode_polyline(points or line(11))),
        travel_advisory=routing_v2.RouteTravelAdvisory(
            toll_info=routing_v2.TollInfo(estimated_price=tolls or [])
        ),
    )


class FakeRoutesClient:
    def __init__(self, routes=None):
        self.routes = routes if routes is not None else [api_route()]
        self.calls = []

    def compute_routes(self, request, metadata):
        self.calls.append((request, metadata))
        return routing_v2.ComputeRoutesResponse(routes=self.routes)


# ------------------------------------------------------------------ Places API


def place(
    pid,
    lat,
    lng,
    *,
    price=3.599,
    age_hours=1,
    fuel_type=FuelType.REGULAR_UNLEADED,
    currency="USD",
) -> places_v1.Place:
    prices = []
    if price is not None:
        units = int(price)
        prices.append(
            places_v1.FuelOptions.FuelPrice(
                type_=fuel_type,
                price=money_pb2.Money(
                    currency_code=currency, units=units, nanos=round((price - units) * 1e9)
                ),
                update_time=datetime.now(timezone.utc) - timedelta(hours=age_hours),
            )
        )
    return places_v1.Place(
        id=pid,
        display_name={"text": f"Gas {pid}"},
        formatted_address=f"{pid} Main St",
        location={"latitude": lat, "longitude": lng},
        fuel_options=places_v1.FuelOptions(fuel_prices=prices),
    )


class FakePlacesClient:
    """Behaves like Nearby Search: returns the `max_result_count` nearest of its
    places inside the requested circle, so coverage gaps show up in tests."""

    def __init__(self, places=None, error=None):
        self.places = places or []
        self.error = error
        self.calls = []

    def search_nearby(self, request, metadata):
        self.calls.append((request, metadata))
        if self.error:
            raise self.error
        circle = request.location_restriction.circle
        center = (circle.center.latitude, circle.center.longitude)
        radius_mi = circle.radius / 1609.344
        inside = sorted(
            (
                (haversine_mi(center, (p.location.latitude, p.location.longitude)), p)
                for p in self.places
            ),
            key=lambda t: t[0],
        )
        found = [p for d, p in inside if d <= radius_mi][: request.max_result_count]
        return places_v1.SearchNearbyResponse(places=found)


def api_error(message="quota exceeded") -> GoogleAPICallError:
    return GoogleAPICallError(message)


# ------------------------------------------------------------------- NREL API


def nrel_station(sid, lat, lng, pricing=None, name=None) -> dict:
    return {
        "id": sid,
        "station_name": name or f"Charger {sid}",
        "latitude": lat,
        "longitude": lng,
        "street_address": f"{sid} Charge Ave",
        "city": "Bakersfield",
        "state": "CA",
        "ev_pricing": pricing,
    }


class FakeNrel:
    def __init__(self, stations=None, error=None):
        self.stations = stations or []
        self.error = error
        self.calls = []

    def post(self, url, data, timeout):
        self.calls.append({"url": url, "data": data, "timeout": timeout})
        if self.error:
            raise self.error
        stations = self.stations

        class Response:
            def raise_for_status(self):
                pass

            def json(self):
                return {"fuel_stations": stations}

        return Response()


def http_error() -> requests.HTTPError:
    return requests.HTTPError("422 Client Error: invalid parameter")
