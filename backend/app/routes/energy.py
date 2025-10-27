from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import os, json, math


router = APIRouter(prefix="/energy", tags=["energy"])

PACK_PATH = "/artifacts/dash_pack.json"


class EnergyRow(BaseModel):
    store: str
    orders_week: float | None = None
    avg_dist_km_per_order: float | None = None
    energy_kwh_week: float | None = None
    est_swaps_week: float | None = None


def _load_pack() -> Dict[str, Any]:
    if not os.path.exists(PACK_PATH):
        raise HTTPException(status_code=404, detail="dash pack not found; run analytics")
    with open(PACK_PATH, "r") as f:
        return json.load(f)


@router.get("/demand")
def energy_demand(city: str | None = None, kwh_per_km: float = 0.03, battery_kwh: float = 2.0) -> Dict[str, List[EnergyRow]]:
    """
    Estimate weekly energy need per store using avg distance/order and orders volume.
    - kwh_per_km: energy consumption per km (default: 0.03 kWh/km)
    - battery_kwh: battery capacity to derive swap counts (default: 2.0 kWh)
    """
    pack = _load_pack()

    def _city_rows(obj: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Prefer productivity block: expects avg_dist_per_order, orders_per_day/week
        prod = obj.get("productivity") or []
        if isinstance(prod, list) and prod:
            return prod
        # Fallback to payouts/incentives/demand if present
        return obj.get("payouts") or obj.get("incentives") or []

    out: Dict[str, List[EnergyRow]] = {}
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
        rows = _city_rows(pack[chosen_key])
        result: List[EnergyRow] = []
        for r in rows:
            try:
                store = str(r.get("store") or r.get("zone") or "").strip()
                if not store:
                    continue
                avg_dist = r.get("avg_dist_per_order")
                if avg_dist is None:
                    # try distance_km per job proxy if available
                    avg_dist = r.get("distance_km")
                orders_week = r.get("orders_per_week")
                if orders_week is None:
                    # derive from orders/day * 6.5 if available
                    opd = r.get("orders_per_day")
                    if opd is not None:
                        orders_week = float(opd) * 6.5
                if orders_week is None and r.get("riders_week") is not None and r.get("orders_per_rider_week") is not None:
                    orders_week = float(r.get("riders_week")) * float(r.get("orders_per_rider_week"))

                energy_kwh_week = None
                swaps_week = None
                if avg_dist is not None and orders_week is not None:
                    energy_kwh_week = float(avg_dist) * float(orders_week) * float(kwh_per_km)
                    if battery_kwh and battery_kwh > 0:
                        swaps_week = energy_kwh_week / float(battery_kwh)

                er = EnergyRow(
                    store=store,
                    orders_week=None if orders_week is None else round(float(orders_week), 2),
                    avg_dist_km_per_order=None if avg_dist is None else round(float(avg_dist), 3),
                    energy_kwh_week=None if energy_kwh_week is None else round(float(energy_kwh_week), 2),
                    est_swaps_week=None if swaps_week is None else round(float(swaps_week), 1),
                )
                result.append(er)
            except Exception:
                continue
        out[chosen_key] = result
    return out


