from fastapi import APIRouter, Depends
from pydantic import BaseModel
from ..services.payout_model import PayoutModelService, get_payout_service


class EstimateRequest(BaseModel):
    energy_kwh: float
    pickup_lat: float
    pickup_lng: float
    dropoff_lat: float
    dropoff_lng: float


class EstimateResponse(BaseModel):
    estimated_price_usd: float


router = APIRouter(prefix="/estimate", tags=["estimate"])


@router.post("/", response_model=EstimateResponse)
def estimate(req: EstimateRequest, svc: PayoutModelService = Depends(get_payout_service)):
    price = svc.estimate_price(
        energy_kwh=req.energy_kwh,
        pickup_lat=req.pickup_lat,
        pickup_lng=req.pickup_lng,
        dropoff_lat=req.dropoff_lat,
        dropoff_lng=req.dropoff_lng,
    )
    return EstimateResponse(estimated_price_usd=price)


