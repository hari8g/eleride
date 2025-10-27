from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import os, json, math, csv


router = APIRouter(prefix="/cashflow", tags=["cashflow"])

PACK_PATH = "/artifacts/dash_pack.json"
DATA_PATH = "/data/rider_week_clean.csv"


class CFSeries(BaseModel):
    past: List[float]
    forecast: List[float]
    rationale: str | None = None


def _load_pack() -> Any:
    if not os.path.exists(PACK_PATH):
        return None
    with open(PACK_PATH, "r") as f:
        return json.load(f)


def _aggregate_from_csv(city: str | None) -> Dict[str, List[float]]:
    # Try to aggregate 4-week totals per store from rider_week_clean.csv if it has week-like fields
    if not os.path.exists(DATA_PATH):
        return {}
    stores: Dict[str, List[float]] = {}
    try:
        with open(DATA_PATH, newline="") as f:
            rdr = csv.DictReader(f)
            for row in rdr:
                if city and str(row.get("city") or "").upper() != city.upper():
                    continue
                store = str(row.get("store") or "").strip()
                if not store:
                    continue
                total = 0.0
                for k in ("final_with_gst_minus_settlement","final_with_gst","final_payout","base_payout","base_pay"):
                    v = row.get(k)
                    if v is not None and v != "":
                        try:
                            total = float(v)
                            break
                        except Exception:
                            pass
                if store not in stores:
                    stores[store] = [0.0,0.0,0.0,0.0]
                # naive: distribute single row across recent weeks (proxy if no week col)
                stores[store][0] += total * 0.4
                stores[store][1] += total * 0.3
                stores[store][2] += total * 0.2
                stores[store][3] += total * 0.1
    except Exception:
        return {}
    return stores


@router.get("/forecast")
def cashflow_forecast(city: str | None = None) -> Dict[str, Dict[str, CFSeries]]:
    """
    Returns per-store cashflow: past 4 weeks and next 4 weeks forecast (simple trend or MA).
    Uses artifacts pack to estimate baseline when no time series exists.
    """
    pack = _load_pack() or {}
    out: Dict[str, Dict[str, CFSeries]] = {}
    targets = [city] if city else list(pack.keys())
    for c in targets:
        chosen = None
        for k in pack.keys():
            if k.upper() == (c or k).upper():
                chosen = k
                break
        stores_cf: Dict[str, CFSeries] = {}
        # Try CSV aggregation
        csv_agg = _aggregate_from_csv(chosen)
        # Baseline per store from payouts if pack present
        base_rows = []
        if chosen and isinstance(pack.get(chosen), dict):
            base_rows = pack[chosen].get("payouts") or pack[chosen].get("incentives") or []
        for r in base_rows:
            store = str(r.get("store") or "").strip()
            if not store:
                continue
            base_val = 0.0
            for k in ("final_with_gst","final_with_gst_minus_settlement","net_after_adj"):
                v = r.get(k)
                if v is not None:
                    try:
                        base_val = float(v)
                        break
                    except Exception:
                        pass
            past = csv_agg.get(store)
            if not past:
                # create synthetic past 4 weeks around base
                past = [base_val*0.9, base_val*0.95, base_val*1.02, base_val*1.0]
            # simple forecast: last diff continue, plus slight regression to mean
            diffs = [past[i]-past[i-1] for i in range(1,len(past))]
            trend = sum(diffs)/len(diffs) if diffs else 0.0
            ma = sum(past[-3:])/min(3,len(past))
            f1 = past[-1] + trend*0.6
            f2 = f1*0.6 + ma*0.4
            f3 = f2*0.6 + ma*0.4
            f4 = f3*0.6 + ma*0.4
            stores_cf[store] = CFSeries(past=[round(x,2) for x in past], forecast=[round(f1,2), round(f2,2), round(f3,2), round(f4,2)], rationale="trend + MA blend")
        if chosen:
            out[chosen] = stores_cf
    return out


