from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    lat: float
    lon: float


class ItineraryRequest(BaseModel):
    car_id: str = Field(...)
    soc_start: float = Field(...)
    soc_min: float = Field(...)
    soc_max: float = Field(...)
    departure: Coordinates
    arrival: Coordinates
