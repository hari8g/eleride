from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(prefix="/match", tags=["match"])


class MatchRequest(BaseModel):
    external_job_id: str
    zone: str | None = None


class MatchResponse(BaseModel):
    provider_id: str
    strategy: str


@router.post("/", response_model=MatchResponse)
def match_job(req: MatchRequest):
    # Simple placeholder strategy
    zone_part = req.zone or "generic"
    provider_id = f"provider-{zone_part}"
    return MatchResponse(provider_id=provider_id, strategy="zone-affinity")


