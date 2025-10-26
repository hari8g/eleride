from datetime import datetime
from pydantic import BaseModel, Field


class JobBase(BaseModel):
    external_job_id: str = Field(..., max_length=64)
    timestamp: datetime
    pickup_lat: float
    pickup_lng: float
    dropoff_lat: float
    dropoff_lng: float
    energy_kwh: float
    price_usd: float | None = None
    zone: str | None = None


class JobCreate(JobBase):
    pass


class Job(JobBase):
    id: int

    class Config:
        from_attributes = True


