from typing import Optional

from pydantic import BaseModel, Field


class Car(BaseModel):
    id: str = Field(...)
    make: str = Field(...)
    model: str = Field(...)
    version: str = Field(...)
    power: float = Field(...)
    battery_capacity: float = Field(...)
    range_best: float = Field(...)
    range_worst: float = Field(...)
    image: Optional[str] = Field(None)

    class Config:
        populate_by_name = True
        str_strip_whitespace = True
