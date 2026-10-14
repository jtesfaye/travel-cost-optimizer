from pydantic import BaseModel


class TripBase(BaseModel):
    destination: str
    budget: float


class TripCreate(TripBase):
    pass


class Trip(TripBase):
    id: int

    class Config:
        from_attributes = True
