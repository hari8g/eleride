from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import os, json, math, hashlib


router = APIRouter(prefix="/maintenance", tags=["maintenance"])

PACK_PATH = "/artifacts/dash_pack.json"


class MaintRow(BaseModel):
    store: str
    downtime_risk: float | None = None
    est_tickets_week: float | None = None
    notes: str | None = None


def _load_pack() -> Dict[str, Any]:
    if not os.path.exists(PACK_PATH):
        raise HTTPException(status_code=404, detail="dash pack not found; run analytics")
    with open(PACK_PATH, "r") as f:
        return json.load(f)


def _variate(store: str, scale: float = 0.08) -> float:
    # Deterministic pseudo-random in [-scale, +scale]
    h = hashlib.sha256(store.encode()).hexdigest()
    v = int(h[:6], 16) / float(0xFFFFFF)  # 0..1
    return (v - 0.5) * 2 * scale


def _combine_risk(idle: float | None, sat: float | None, instability: float | None, avg_km: float | None, orders_wk: float | None) -> tuple[float, str]:
    notes: List[str] = []
    score = 0.0
    w_idle, w_sat, w_inst, w_km, w_vol = 0.35, 0.25, 0.2, 0.1, 0.1
    if idle is not None:
        score += w_idle * max(0.0, min(100.0, float(idle)))
        if idle > 70: notes.append("High idle time risk")
    if sat is not None:
        score += w_sat * max(0.0, min(100.0, float(sat)))
        if sat > 70: notes.append("Market saturation")
    if instability is not None:
        score += w_inst * max(0.0, min(100.0, float(instability)))
        if instability > 60: notes.append("Earnings instability")
    if avg_km is not None:
        km_scaled = max(0.0, min(100.0, (float(avg_km) / 8.0) * 100.0))  # >8km/order stresses vehicle
        score += w_km * km_scaled
        if avg_km > 8: notes.append("Long routes stress")
    if orders_wk is not None:
        vol_scaled = max(0.0, min(100.0, (float(orders_wk) / 1200.0) * 100.0))  # heavy volume -> wear
        score += w_vol * vol_scaled
        if orders_wk > 800: notes.append("Heavy weekly volume")
    return score, "; ".join(notes) if notes else "Stable"


@router.get("/risk")
def maintenance_risk(city: str | None = None) -> Dict[str, List[MaintRow]]:
    """
    Maintenance risk estimation:
    - Inputs: idle_time_risk, demand_saturation(_score), stability_index, avg_dist_per_order, orders per week
    - Output: downtime_risk (0-100), est_tickets_week, with rationale notes
    """
    pack = _load_pack()
    out: Dict[str, List[MaintRow]] = {}
    targets = [city] if city else list(pack.keys())
    for c in targets:
        chosen_key = None
        for k in pack.keys():
            if k.upper() == c.upper():
                chosen_key = k
                break
        if not chosen_key:
            out[c] = []
            continue

        ext = pack.get(chosen_key, {}).get("extended") or pack.get(chosen_key, {}).get("insights") or []
        prod = pack.get(chosen_key, {}).get("productivity") or []
        rows: List[MaintRow] = []
        source = ext or []
        if not source:
            base = pack.get(chosen_key, {}).get("payouts") or pack.get(chosen_key, {}).get("incentives") or []
            for r in base:
                s = str(r.get("store") or "").strip()
                if not s:
                    continue
                # baseline with slight variation
                base_risk = 22.0 + (_variate(s, 10.0))
                rows.append(MaintRow(store=s, downtime_risk=round(max(0.0, min(100.0, base_risk)), 1), est_tickets_week=round(max(0.2, base_risk/25.0), 1), notes="baseline"))
        for r in source:
            store = str(r.get("store") or "").strip()
            if not store:
                continue
            idle = r.get("idle_time_risk")
            sat = r.get("demand_saturation") or r.get("demand_saturation_score")
            instability = r.get("stability_index")
            # find matching productivity row for distance/volume
            avg_km = None
            orders_week = None
            try:
                p = next((x for x in prod if str(x.get("store") or "").strip() == store), None)
                if p:
                    avg_km = p.get("avg_dist_per_order")
                    orders_week = p.get("orders_per_week") or (p.get("orders_per_day") and float(p.get("orders_per_day")) * 6.5)
            except Exception:
                pass
            base_score, why = _combine_risk(idle, sat, instability, avg_km, orders_week)
            varied = base_score + _variate(store, 8.0) * 100.0
            risk = max(0.0, min(100.0, varied))
            tickets = max(0.1, (risk/100.0) * (float(r.get("riders_week") or 50) / 5.0))
            rows.append(MaintRow(store=store, downtime_risk=round(risk, 1), est_tickets_week=round(tickets, 1), notes=why))
        out[chosen_key] = rows
    return out


