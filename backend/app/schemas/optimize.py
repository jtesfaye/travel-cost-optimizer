from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Snake_case in Python, camelCase on the wire (matches the frontend)."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

class Coordinate(CamelModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class VehicleInput(CamelModel):
    type: Literal["gas", "hybrid", "ev"]
    mpg: float | None = Field(default=None, gt=0)
    tank_gal: float | None = Field(default=None, gt=0)
    range_mi: float | None = Field(default=None, gt=0)
    battery_kwh: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def require_specs_for_type(self):
        required = (
            ("range_mi", "battery_kwh")
            if self.type == "ev"
            else ("mpg", "tank_gal")
        )
        missing = [name for name in required if getattr(self, name) is None]
        if missing:
            raise ValueError(f"{self.type} vehicles require: {', '.join(missing)}")
        return self


class OptimizeOptions(CamelModel):
    start_fuel_pct: float = Field(default=100, ge=0, le=100)
    reserve_pct: float = Field(default=10, ge=0, le=50)
    depart_at: datetime | None = None


class OptimizeRequest(CamelModel):
    origin: Coordinate
    destination: Coordinate
    vehicle: VehicleInput
    options: OptimizeOptions = Field(default_factory=OptimizeOptions)

class Cost(CamelModel):
    energy: float
    tolls: float
    total: float

class Stop(CamelModel):
    id: str
    type: Literal["fuel", "charging"]
    name: str
    address: str
    lat: float
    lng: float
    mile_marker: float
    price: float  # $/gal or $/kWh
    price_unit: Literal["gal", "kWh"]
    amount: float  # gallons or kWh purchased at this stop
    cost: float
    detour_mi: float
    detour_min: float
    price_source: Literal["live", "estimated"]


class Toll(CamelModel):
    name: str
    cost: float


class RouteResult(CamelModel):
    id: str
    description: str
    distance_mi: float
    duration_min: float
    cost: Cost
    polyline: str  # encoded polyline (precision 5)
    stops: list[Stop]
    tolls: list[Toll]


class OptimizeResult(CamelModel):
    routes: list[RouteResult]
    recommended_route_id: str
    price_as_of: datetime


# -------------------------------------------------------------------- job

JobStatus = Literal["queued", "running", "succeeded", "failed"]
JobStage = Literal["queued", "routing", "pricing", "optimizing", "done"]
ErrorCode = Literal["no_feasible_route", "upstream_error", "internal_error"]


class JobError(CamelModel):
    code: ErrorCode
    message: str


class OptimizeJob(CamelModel):
    id: str
    status: JobStatus
    stage: JobStage
    progress: float = Field(ge=0, le=1)
    created_at: datetime
    updated_at: datetime
    result: OptimizeResult | None = None
    error: JobError | None = None
