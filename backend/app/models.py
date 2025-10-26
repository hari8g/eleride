from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.orm import relationship
from .db import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    external_job_id = Column(String(64), unique=True, index=True, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    pickup_lat = Column(Float, nullable=False)
    pickup_lng = Column(Float, nullable=False)
    dropoff_lat = Column(Float, nullable=False)
    dropoff_lng = Column(Float, nullable=False)
    energy_kwh = Column(Float, nullable=False)
    price_usd = Column(Float, nullable=True)
    zone = Column(String(64), nullable=True)


