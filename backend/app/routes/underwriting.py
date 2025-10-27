from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import os, json, math


router = APIRouter(prefix="/underwriting", tags=["underwriting"])

CREDIT_PATH = "/artifacts/credit_profiles.json"
PACK_PATH = "/artifacts/dash_pack.json"


class UWRow(BaseModel):
    cee_id: str
    cee_name: str | None = None
    store: str | None = None
    credit_score: float | None = None
    monthly_median_inr: float | None = None
    recommended_limit_inr: float | None = None
    pd: float | None = None  # probability of default (0..1)
    lgd: float | None = None  # loss given default (0..1)
    ead: float | None = None  # exposure at default
    expected_loss_inr: float | None = None
    rationale: str | None = None


def _load(path: str) -> Any:
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)


@router.get("/credit")
def credit_underwriting(city: str | None = None) -> Dict[str, List[UWRow]]:
    credit = _load(CREDIT_PATH)
    pack = _load(PACK_PATH) or {}
    if credit is None:
        raise HTTPException(status_code=404, detail="credit profiles not found; run analytics")

    out: Dict[str, List[UWRow]] = {}
    targets = [city] if city else list(credit.keys())
    for c in targets:
        chosen = None
        for k in credit.keys():
            if k.upper() == (c or k).upper():
                chosen = k
                break
        if not chosen:
            out[c] = []
            continue
        rows: List[UWRow] = []
        # derive city-level stability from dash pack if available
        city_pack = None
        for k in pack.keys():
            if k.upper() == chosen.upper():
                city_pack = pack[k]
                break
        store_to_stability: Dict[str, float] = {}
        if city_pack and isinstance(city_pack, dict):
            for r in (city_pack.get("extended") or city_pack.get("insights") or []):
                s = str(r.get("store") or "")
                if s:
                    st = r.get("stability_index")
                    if st is not None:
                        store_to_stability[s] = float(st)

        for r in credit.get(chosen, []):
            try:
                cee_id = str(r.get("cee_id") or r.get("id") or "")
                if not cee_id:
                    continue
                cee_name = r.get("cee_name")
                store = r.get("store")
                earn_med = float(r.get("earning_median") or 0)
                orders_day = r.get("orders_per_day")
                attend = r.get("attendance_per_week")
                stability = None
                if store and store in store_to_stability:
                    stability = store_to_stability[store]
                # credit_score present or derive basic score
                score = r.get("credit_score")
                if score is None:
                    # simple model: earnings and attendance raise score, volatility (inverse stability) lowers
                    base = min(100.0, (earn_med / 1500.0) * 100.0)
                    att = 0.0 if attend is None else min(100.0, (float(attend) / 6.5) * 100.0)
                    vol_penalty = 0.0 if stability is None else max(0.0, 100.0 - float(stability))
                    score = max(0.0, min(100.0, 0.5 * base + 0.4 * att + 0.1 * (100.0 - vol_penalty)))
                # recommended limit = 1.5x monthly median (weekly median * 4)
                monthly_median = earn_med * 4.0
                limit = monthly_median * 1.5
                # PD maps inversely to score, clamp 2%..25%
                pd = max(0.02, min(0.25, (100.0 - float(score)) / 300.0))
                # LGD conservative 40%
                lgd = 0.4
                # EAD = limit
                ead = limit
                el = pd * lgd * ead
                rationale_parts = []
                if score >= 75: rationale_parts.append("Strong earnings and attendance")
                elif score >= 60: rationale_parts.append("Moderate risk; stable profile")
                else: rationale_parts.append("Higher risk; consider lower limit")
                if stability is not None and stability < 50:
                    rationale_parts.append("Low stability index")
                if attend is not None and float(attend) < 4.0:
                    rationale_parts.append("Low weekly attendance")

                rows.append(UWRow(
                    cee_id=cee_id,
                    cee_name=cee_name,
                    store=store,
                    credit_score=round(float(score), 1) if score is not None else None,
                    monthly_median_inr=round(monthly_median, 2),
                    recommended_limit_inr=round(limit, 2),
                    pd=round(pd, 3),
                    lgd=round(lgd, 2),
                    ead=round(ead, 2),
                    expected_loss_inr=round(el, 2),
                    rationale="; ".join(rationale_parts),
                ))
            except Exception:
                continue
        out[chosen] = rows
    return out


