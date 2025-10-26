from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(prefix="/settlement", tags=["settlement"])


class SettlementRequest(BaseModel):
    contract_id: str
    actual_energy_kwh: float


class SettlementResponse(BaseModel):
    contract_id: str
    payout_usd: float


@router.post("/", response_model=SettlementResponse)
def settle(req: SettlementRequest):
    # Simple payout rule: $0.30/kWh
    payout = round(req.actual_energy_kwh * 0.30, 2)
    return SettlementResponse(contract_id=req.contract_id, payout_usd=payout)


