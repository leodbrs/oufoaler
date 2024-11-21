from typing import List, Optional

from pydantic import BaseModel, Field


class ChargingStation(BaseModel):
    id: str = Field(..., alias="id")
    coordinates: List[float]  # [longitude, latitude]
    address: Optional[str] = Field("Unknown", alias="address")
    operator: Optional[str] = Field("Unknown", alias="operator")
    plug_type: Optional[str] = Field("Unknown", alias="prise_type")
    access: Optional[str] = Field("Unknown", alias="access")
    accessibility: Optional[str] = Field("Unknown", alias="accessibility")
    power: Optional[float] = Field(0.0, alias="max_power")
    distance_along_route_km: Optional[float] = None
    charging_time_hours: Optional[float] = None

    class Config:
        populate_by_name = True
        str_strip_whitespace = True
