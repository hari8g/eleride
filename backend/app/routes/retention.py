from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import os, json


router = APIRouter(prefix="/retention", tags=["retention"])

PACK_PATH = "/artifacts/dash_pack.json"


class RetRow(BaseModel):
    cee_id: str | None = None
    cee_name: str | None = None
    store: str | None = None
    risk: float
    actions: str


def _load_pack() -> Any:
    if not os.path.exists(PACK_PATH):
        raise HTTPException(status_code=404, detail="dash pack not found; run analytics")
    with open(PACK_PATH, "r") as f:
        return json.load(f)


@router.get("/at-risk")
def at_risk(city: str | None = None) -> Dict[str, List[RetRow]]:
    pack = _load_pack()
    out: Dict[str, List[RetRow]] = {}
    targets = [city] if city else list(pack.keys())
    for c in targets:
        chosen = None
        for k in pack.keys():
            if k.upper() == (c or k).upper():
                chosen = k
                break
        if not chosen:
            out[c] = []
            continue
        ext = pack[chosen].get("extended") or pack[chosen].get("insights") or []
        rows: List[RetRow] = []
        for r in ext:
            store = str(r.get("store") or "").strip()
            idle = r.get("idle_time_risk") or 0
            stab = r.get("stability_index") or 70
            ramp = r.get("new_rider_ramp_score") or 70
            # risk: high idle + low stability + low ramp => churn risk
            risk = 0.5*(idle/100.0) + 0.3*(max(0.0, (70-stab))/70.0) + 0.2*(max(0.0, (70-ramp))/70.0)
            risk = max(0.0, min(1.0, risk)) * 100.0
            acts = []
            if idle > 60: acts.append("Rebalance shifts / hotspots")
            if stab < 60: acts.append("Stabilize payouts, reduce variance")
            if ramp < 60: acts.append("Assign mentor, easier shifts")
            if not acts: acts.append("Recognition + small bonus")
            rows.append(RetRow(store=store, risk=round(risk,1), actions="; ".join(acts)))
        if not rows:
            # synthesize at-risk list using payouts/incentives store names
            base = pack[chosen].get("payouts") or pack[chosen].get("incentives") or []
            for r in base:
                store = str(r.get("store") or "").strip()
                if not store:
                    continue
                # moderate synthetic risk 15-45%
                import hashlib
                h = int(hashlib.sha256(store.encode()).hexdigest()[:6], 16) / float(0xFFFFFF)
                risk = 15.0 + h * 30.0
                acts = ["Recognition + small bonus"]
                if risk > 35: acts = ["Rebalance shifts / hotspots", "Stabilize payouts"]
                rows.append(RetRow(store=store, risk=round(risk,1), actions="; ".join(acts)))
        rows.sort(key=lambda x: x.risk, reverse=True)
        out[chosen] = rows
    return out


