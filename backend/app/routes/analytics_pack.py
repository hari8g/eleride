from fastapi import APIRouter, HTTPException
import os, json, math

router = APIRouter(prefix="/analytics", tags=["analytics"])

PACK_PATH = "/artifacts/dash_pack.json"

def _san(o):
    if isinstance(o, dict):
        return {k: _san(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_san(v) for v in o]
    if isinstance(o, float):
        if math.isnan(o) or math.isinf(o):
            return None
    return o

@router.get("/pack")
def get_pack(city: str | None = None):
    if not os.path.exists(PACK_PATH):
        raise HTTPException(status_code=404, detail="dash pack not found, run analytics")
    with open(PACK_PATH, 'r') as f:
        data = json.load(f)
    data = _san(data)
    if city:
        for k in data.keys():
            if k.upper() == city.upper():
                return {k: data[k]}
        return {city: {}}
    return data


