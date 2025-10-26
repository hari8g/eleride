from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(prefix="/contracts", tags=["contracts"])


class Contract(BaseModel):
    contract_id: str
    external_job_id: str
    provider_id: str
    terms: str


@router.post("/", response_model=Contract)
def create_contract(contract: Contract):
    # Echo stub
    return contract


@router.get("/{contract_id}", response_model=Contract)
def get_contract(contract_id: str):
    # Stub contract
    return Contract(
        contract_id=contract_id,
        external_job_id="job-123",
        provider_id="provider-generic",
        terms="flat-rate",
    )


