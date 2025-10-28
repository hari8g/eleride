import json
from pathlib import Path
from typing import Any, Dict, List
import math
import pandas as pd


LAUNCH_XLS = Path("/data/New launch store.xlsx")
ART_DIR = Path("/artifacts")
ART_DIR.mkdir(parents=True, exist_ok=True)
STORES_JSON = ART_DIR / "launch_stores.json"
PLANS_JSON = ART_DIR / "launch_plans.json"


ALIASES = {
    "store": ["Store Name","Store","Outlet","Location Name"],
    "city": ["City","Town"],
    "opening_date": ["Opening Date","Launch Date","Go Live","Golive Date"],
    "expected_orders_day": ["Daily Order Target","Orders/Day","Orders Day","Expected Orders/Day","Expected Orders"],
    "peak_hours": ["Peak hours- 6am to 10am and 6pm to 12pm","Peak Hours","Peak"],
    "sla_target_min": ["SLA Target (min)","SLA"],
    "buffer_riders": ["Buffer Riders","Buffer %","Buffer"],
    "target_orders_per_rider": ["Target Orders per Rider","Orders per Rider","Rider Productivity"],
    "avg_km_per_order": ["Avg km per order","Average Distance per Order","Distance per order km"],
    "inr_per_order": ["INR per order","Revenue per order","Payout per order"],
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = list(df.columns)
    # Build mapping
    colmap: Dict[str,str] = {}
    for canon, als in ALIASES.items():
        for a in als:
            for c in cols:
                if str(c).strip().lower() == str(a).strip().lower().replace(" ", " "):
                    colmap[c] = canon
    # Heuristics
    for c in cols:
        lc = str(c).lower()
        if c in colmap:
            continue
        if "store" in lc and "type" not in lc:
            colmap[c] = "store"
        elif "daily order target" in lc or ("order" in lc and ("day" in lc or "/day" in lc)):
            colmap[c] = "expected_orders_day"
        elif "peak" in lc:
            colmap[c] = "peak_hours"
        elif ("sla" in lc) and ("slab" not in lc):
            colmap[c] = "sla_target_min"
    return df.rename(columns=colmap)


def read_launch() -> pd.DataFrame:
    xls = pd.ExcelFile(LAUNCH_XLS)
    frames: List[pd.DataFrame] = []
    for name in xls.sheet_names:
        sdf = xls.parse(name)
        if isinstance(sdf, pd.DataFrame) and not sdf.empty:
            frames.append(sdf)
    if not frames:
        raise RuntimeError("No data found in launch workbook")
    df = pd.concat(frames, ignore_index=True)
    df = normalize_columns(df)
    # drop duplicate columns after normalization
    try:
        df = df.loc[:, ~pd.Index(df.columns).duplicated(keep='first')]
    except Exception:
        pass
    if "store" not in df.columns:
        # try derive from first text-like col
        text_cols = [c for c in df.columns if df[c].dtype == object]
        if text_cols:
            df["store"] = df[text_cols[0]].astype(str)
    # sanitize
    df = df.dropna(how="all")
    df["store"] = df["store"].astype(str).str.strip()
    df = df[df["store"].str.len() > 0]
    # alias Daily Order Target
    if "expected_orders_day" not in df.columns:
        for cand in ["Daily Order Target", "Orders/Day", "Orders Day"]:
            if cand in df.columns:
                df["expected_orders_day"] = pd.to_numeric(df[cand], errors="coerce")
                break
    # group by store (slabbed rows)
    # build aggregation: numeric expected_orders_day max; otherwise first non-null
    if "expected_orders_day" in df.columns:
        # Sometimes column becomes DataFrame if duplicated; collapse
        s = df["expected_orders_day"]
        if isinstance(s, pd.DataFrame):
            s = s.iloc[:,0]
        df["expected_orders_day"] = pd.to_numeric(s, errors="coerce")
    agg: Dict[str, Any] = {}
    for c in df.columns:
        if c == "store":
            continue
        if c == "expected_orders_day":
            agg[c] = "max"
        else:
            agg[c] = (lambda s: s.dropna().iloc[0] if not s.dropna().empty else None)
    out = df.groupby("store", as_index=False).agg(agg)
    return out


def compute_plan(r: pd.Series) -> Dict[str,Any]:
    def to_float(val, default):
        try:
            x = float(val)
            if math.isnan(x) or math.isinf(x):
                return default
            return x
        except Exception:
            return default
    expected = to_float(r.get("expected_orders_day"), 0.0)
    orders_per_rider = to_float(r.get("target_orders_per_rider"), 22.0)
    buffer_pct = 0.15
    riders_day = expected / max(1.0, orders_per_rider)
    riders_day_with_buffer = max(0.0, riders_day * (1.0 + buffer_pct))
    peak = str(r.get("peak_hours") or "").lower()
    morning_ratio = 0.6 if ("morning" in peak or "6am" in peak) else 0.5
    morning = math.ceil(riders_day_with_buffer * morning_ratio)
    evening = math.ceil(riders_day_with_buffer - morning)
    avg_km = to_float(r.get("avg_km_per_order"), 2.5)
    kwh_per_km = 0.03
    energy_kwh_day = expected * avg_km * kwh_per_km
    swaps_day = energy_kwh_day / 2.0
    sla_target = to_float(r.get("sla_target_min"), 30.0)
    headroom = max(0.0, (riders_day_with_buffer - riders_day) / max(1.0, riders_day))
    predicted_sla = max(15.0, sla_target - headroom*10.0)
    inr_per_order = to_float(r.get("inr_per_order"), 200.0)
    week0 = expected * inr_per_order * 6.5
    roi = [round(x,2) for x in [week0*0.9, week0*1.0, week0*1.1, week0*1.15]]
    return {
        "staffing": {"riders_per_day": math.ceil(riders_day_with_buffer), "target_orders_per_rider": orders_per_rider, "buffer_pct": round(buffer_pct*100,1), "shifts": [{"name":"Morning","riders": morning},{"name":"Evening","riders": evening}]},
        "energy": {"avg_km_per_order": avg_km, "kwh_per_km": kwh_per_km, "energy_kwh_day": round(energy_kwh_day,2), "swaps_day": round(swaps_day,1)},
        "sla": {"target_min": sla_target, "predicted_min": round(predicted_sla,1)},
        "roi": {"weekly_inr": roi, "assumptions": {"inr_per_order": inr_per_order}},
    }


def main():
    df = read_launch()
    stores: List[Dict[str,Any]] = []
    plans: Dict[str,Any] = {}
    for _, r in df.iterrows():
        store = str(r.get("store") or "").strip()
        if not store:
            continue
        # readiness score simple
        have = 0
        total = 5
        for k in ["expected_orders_day","peak_hours","sla_target_min","avg_km_per_order","inr_per_order"]:
            if k in df.columns and pd.notna(r.get(k)):
                have += 1
        readiness = round(min(100.0, (have/total)*60 + (15 if pd.notna(r.get("expected_orders_day")) else 0) + (25 if pd.notna(r.get("avg_km_per_order")) else 0)),1)
        stores.append({
            "store": store,
            "city": str(r.get("city") or "").strip() or None,
            "opening_date": None,
            "readiness_score": readiness,
            "risk": None if readiness >= 70 else ("needs staffing/energy check" if readiness >= 50 else "incomplete data"),
        })
        plan = compute_plan(r)
        plan.update({"store": store, "city": str(r.get("city") or "").strip() or None, "opening_date": None})
        plans[store] = plan
    STORES_JSON.write_text(json.dumps(stores, ensure_ascii=False))
    PLANS_JSON.write_text(json.dumps(plans, ensure_ascii=False))
    print(f"Wrote {STORES_JSON} and {PLANS_JSON}")


if __name__ == "__main__":
    main()


