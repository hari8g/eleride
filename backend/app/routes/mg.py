from fastapi import APIRouter, HTTPException
import os, json, math

router = APIRouter(prefix="/mg", tags=["mg"])

PATH_JSON = "/artifacts/mg_guidance.json"

def _san(o):
    if isinstance(o, dict):
        return {k: _san(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_san(v) for v in o]
    if isinstance(o, float):
        if math.isnan(o) or math.isinf(o):
            return None
    return o

@router.get("/guidance")
def guidance(city: str | None = None):
    if not os.path.exists(PATH_JSON):
        raise HTTPException(status_code=404, detail="MG guidance not found, run analytics")
    with open(PATH_JSON, 'r') as f:
        data = json.load(f)
    data = _san(data)
    if city:
        for k in data.keys():
            if k.upper() == city.upper():
                return {k: data[k]}
        return {city: []}
    return data


