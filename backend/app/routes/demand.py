from fastapi import APIRouter, HTTPException
import os, json

router = APIRouter(prefix="/demand", tags=["demand"])

ARTIFACT_PATH = "/artifacts/demand_store.json"

@router.get("/forecast")
def demand_forecast(city: str | None = None):
    if not os.path.exists(ARTIFACT_PATH):
        raise HTTPException(status_code=404, detail="demand artifact not found, run analytics first")
    with open(ARTIFACT_PATH, "r") as f:
        data = json.load(f)
    if city:
        return {city: data.get(city.upper()) or data.get(city) or []}
    return data


