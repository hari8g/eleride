from fastapi import APIRouter, HTTPException
import os, json, math

router = APIRouter(prefix="/earnings", tags=["earnings"])

PATH_JSON = "/artifacts/earnings_per_ride.json"

def _san(o):
    if isinstance(o, dict):
        return {k: _san(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_san(v) for v in o]
    if isinstance(o, float):
        if math.isnan(o) or math.isinf(o):
            return None
    return o

@router.get("/per-ride")
def per_ride(city: str, store: str | None = None):
    if not os.path.exists(PATH_JSON):
        raise HTTPException(status_code=404, detail="earnings artifact not found, run analytics")
    with open(PATH_JSON, 'r') as f:
        data = json.load(f)
    data = _san(data)
    # case-insensitive city key
    key = None
    for k in data.keys():
        if k.upper() == city.upper():
            key = k
            break
    if key is None:
        return {city: []}
    rows = data[key]
    if store:
        rows = [r for r in rows if r.get('store','').upper() == store.upper()]
    return {key: rows}


