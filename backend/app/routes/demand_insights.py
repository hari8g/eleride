from fastapi import APIRouter, HTTPException, Query
import os, json
import math

router = APIRouter(prefix="/demand", tags=["demand"])

FORECAST_PATH = "/artifacts/demand_store.json"               # existing/simple
INSIGHTS_PATH = "/artifacts/demand_store_extended.json"      # new/extended

@router.get("/forecast")
def demand_forecast(city: str | None = None):
    path = INSIGHTS_PATH if os.path.exists(INSIGHTS_PATH) else FORECAST_PATH
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="No demand artifact found. Run analytics first.")
    with open(path, "r") as f:
        data = json.load(f)
    def _san(o):
        if isinstance(o, dict):
            return {k: _san(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_san(v) for v in o]
        if isinstance(o, float):
            if math.isnan(o) or math.isinf(o):
                return None
        return o
    data = _san(data)
    if city:
        for k in list(data.keys()):
            if k.upper() == city.upper():
                return {k: data[k]}
        return {city: []}
    return data

@router.get("/insights")
def demand_insights(city: str | None = None):
    if not os.path.exists(INSIGHTS_PATH):
        raise HTTPException(status_code=404, detail="Extended insights not found. Run extended analytics.")
    with open(INSIGHTS_PATH, "r") as f:
        data = json.load(f)
    def _san(o):
        if isinstance(o, dict):
            return {k: _san(v) for k, v in o.items()}
        if isinstance(o, list):
            return [_san(v) for v in o]
        if isinstance(o, float):
            if math.isnan(o) or math.isinf(o):
                return None
        return o
    data = _san(data)
    if city:
        for k in list(data.keys()):
            if k.upper() == city.upper():
                return {k: data[k]}
        return {city: []}
    return data


