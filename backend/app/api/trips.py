from fastapi import APIRouter, HTTPException

from app.schemas.trip import Trip, TripCreate

router = APIRouter(prefix="/trips", tags=["trips"])

_trips: dict[int, Trip] = {}
_next_id = 1


@router.get("/", response_model=list[Trip])
def list_trips():
    return list(_trips.values())


@router.post("/", response_model=Trip, status_code=201)
def create_trip(trip: TripCreate):
    global _next_id
    new_trip = Trip(id=_next_id, **trip.model_dump())
    _trips[_next_id] = new_trip
    _next_id += 1
    return new_trip


@router.get("/{trip_id}", response_model=Trip)
def get_trip(trip_id: int):
    trip = _trips.get(trip_id)
    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip
