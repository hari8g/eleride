from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import os, json


router = APIRouter(prefix="/expansion", tags=["expansion"])

PACK_PATH = "/artifacts/dash_pack.json"


class Opp(BaseModel):
    store: str
    roi_score: float
    capacity_gap: float | None = None
    demand_score: float | None = None
    expected_gmv_week: float | None = None
    rationale: str | None = None


def _load_pack() -> Any:
    if not os.path.exists(PACK_PATH):
        raise HTTPException(status_code=404, detail="dash pack not found; run analytics")
    with open(PACK_PATH, "r") as f:
        return json.load(f)


@router.get("/opps")
def expansion_opportunities(city: str | None = None, weight_gap: float = 0.5, weight_demand: float = 0.5) -> Dict[str, List[Opp]]:
    pack = _load_pack()
    out: Dict[str, List[Opp]] = {}
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
        rows: List[Opp] = []
        for r in ext:
            store = str(r.get("store") or "").strip()
            if not store:
                continue
            demand = r.get("demand_score")
            gap = None
            if r.get("recommended_riders_day") is not None and r.get("riders_week") is not None:
                try:
                    current_day = float(r.get("riders_week"))/6.5
                    gap = max(0.0, float(r.get("recommended_riders_day")) - current_day)
                except Exception:
                    gap = None
            # expected GMV proxy from earning index
            gmv = r.get("store_earning_index")
            # ROI score blend
            sc_gap = 0.0 if gap is None else min(1.0, gap/25.0) * 100.0
            sc_dem = 0.0 if demand is None else float(demand)
            roi = weight_gap*sc_gap + weight_demand*sc_dem
            why = []
            if gap and gap > 0: why.append(f"Capacity gap {gap:.1f} riders/day")
            if demand and demand > 60: why.append("Strong demand")
            if gmv: why.append("High earning index")
            rows.append(Opp(store=store, roi_score=round(roi,1), capacity_gap=None if gap is None else round(gap,1), demand_score=None if demand is None else round(float(demand),1), expected_gmv_week=None if gmv is None else round(float(gmv),2), rationale="; ".join(why) if why else "Balanced"))
        # Fallback if no insights: synthesize from payouts/incentives
        if not rows:
            base = pack[chosen].get("payouts") or pack[chosen].get("incentives") or []
            for r in base:
                store = str(r.get("store") or "").strip()
                if not store:
                    continue
                gmv = None
                for k in ("final_with_gst","final_with_gst_minus_settlement","net_after_adj"):
                    v = r.get(k)
                    if v is not None:
                        try:
                            gmv = float(v)
                            break
                        except Exception:
                            pass
                demand = None
                ds = r.get("demand_score")
                if ds is not None:
                    try:
                        demand = float(ds)
                    except Exception:
                        demand = None
                if demand is None and gmv is not None:
                    demand = max(20.0, min(95.0, (gmv / 2000.0) * 100.0))
                # capacity gap heuristic 5-15 riders/day if demand seems solid
                gap = 0.0
                if demand and demand > 50:
                    gap = max(3.0, min(18.0, (demand - 50.0) / 3.0))
                sc_gap = min(1.0, gap/25.0) * 100.0
                sc_dem = 0.0 if demand is None else float(demand)
                roi = weight_gap*sc_gap + weight_demand*sc_dem
                why = []
                if gap and gap > 0: why.append(f"Capacity gap {gap:.1f} riders/day")
                if demand and demand > 60: why.append("Strong demand")
                if gmv: why.append("High earning index")
                rows.append(Opp(store=store, roi_score=round(roi,1), capacity_gap=None if gap is None else round(gap,1), demand_score=None if demand is None else round(float(demand),1), expected_gmv_week=None if gmv is None else round(float(gmv),2), rationale="; ".join(why) if why else "Balanced"))

        # sort desc by roi
        rows.sort(key=lambda x: x.roi_score, reverse=True)
        out[chosen] = rows
    return out


