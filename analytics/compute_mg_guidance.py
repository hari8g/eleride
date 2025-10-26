import argparse
import json
import math
import os
import pandas as pd
import numpy as np

"""
Compute Minimum Guarantee (MG) guidance per driver:
- mg_target_per_day = minimum_guarantee / mg_eligible_days
- current_per_day = earning_mean / 6.5 (fallback to earning_median/6.5)
- mg_gap = max(0, mg_target_per_day - current_per_day)
- per_ride_median from earnings_per_ride.json (by city/store), fallback heuristics if missing
- extra_orders = ceil(mg_gap / per_ride_median)
- extra_shifts = ceil(extra_orders / target_orders_per_shift)
Outputs:
- artifacts/mg_guidance.csv
- artifacts/mg_guidance.json (grouped by city)
"""


def load_per_ride_map(per_ride_json_path: str) -> dict:
    if not os.path.exists(per_ride_json_path):
        return {}
    with open(per_ride_json_path, 'r') as f:
        data = json.load(f)
    # map[(city, store)] -> per_ride_median
    out = {}
    for city, rows in data.items():
        for r in rows:
            key = (str(city).upper(), str(r.get('store','')).upper())
            out[key] = float(r.get('per_ride_median') or r.get('per_ride_avg') or 60.0)
    return out


def compute(df: pd.DataFrame, per_ride_map: dict, target_orders_per_shift: int = 10) -> pd.DataFrame:
    d = df.copy()
    for c in ['final_with_gst','minimum_guarantee','mg_eligible_days']:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors='coerce')
    d['city'] = d['city'].astype(str).str.upper()
    d['store'] = d['store'].astype(str).str.upper()
    # group by driver within city
    gb = d.groupby(['city','cee_id'], dropna=True)
    earning_mean = gb['final_with_gst'].mean().rename('earning_mean')
    earning_median = gb['final_with_gst'].median().rename('earning_median')
    mg_sum = (gb['minimum_guarantee'].sum() if 'minimum_guarantee' in d.columns else pd.Series(index=earning_mean.index, data=np.nan)).rename('minimum_guarantee_sum')
    mg_days = (gb['mg_eligible_days'].sum() if 'mg_eligible_days' in d.columns else pd.Series(index=earning_mean.index, data=np.nan)).rename('mg_eligible_days_sum')
    # predominant store
    top_store = gb['store'].agg(lambda s: s.mode().iat[0] if not s.mode().empty else (s.iloc[0] if len(s) else '')).rename('store')
    cee_name = gb['cee_name'].agg(lambda s: s.dropna().iloc[0] if len(s.dropna()) else '').rename('cee_name')

    out = pd.concat([earning_mean, earning_median, mg_sum, mg_days, top_store, cee_name], axis=1).reset_index()
    # targets
    out['mg_target_per_day'] = np.where(out.get('mg_eligible_days_sum', pd.Series(0)).fillna(0)>0, out.get('minimum_guarantee_sum', pd.Series(0)).fillna(0)/out.get('mg_eligible_days_sum', pd.Series(1)).fillna(1), np.nan)
    out['current_per_day'] = np.where(out['earning_mean'].notna(), out['earning_mean']/6.5, out['earning_median']/6.5)
    out['mg_gap'] = np.maximum(0.0, (out['mg_target_per_day'] - out['current_per_day']).fillna(0))
    # per-ride
    def per_ride(row):
        key = (row['city'], row['store'])
        return float(per_ride_map.get(key, 60.0))
    out['per_ride_median'] = out.apply(per_ride, axis=1)
    out['extra_orders'] = out.apply(lambda r: int(math.ceil(r['mg_gap']/r['per_ride_median'])) if r['per_ride_median']>0 else 0, axis=1)
    out['extra_shifts'] = out.apply(lambda r: int(math.ceil(r['extra_orders']/target_orders_per_shift)) if r['extra_orders']>0 else 0, axis=1)
    out['recommendation'] = out.apply(lambda r: (
        f"Increase earnings by ₹{int(round(r['mg_gap']))}/day: target +{r['extra_orders']} orders (~{r['extra_shifts']} shift(s)), focus on {r['store'].title()} best shift."
    ) if r['mg_gap']>0 else "Already at/above MG target.", axis=1)
    # round display
    for c in ['mg_target_per_day','current_per_day','mg_gap','per_ride_median']:
        out[c] = out[c].round(1)
    return out


def main(input_csv: str, per_ride_json: str, out_csv: str, out_json: str, target_orders_per_shift: int = 10):
    df = pd.read_csv(input_csv)
    needed = {'city','store','cee_id','cee_name','final_with_gst'}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    per_ride_map = load_per_ride_map(per_ride_json)
    res = compute(df, per_ride_map, target_orders_per_shift=target_orders_per_shift)
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    res.to_csv(out_csv, index=False)
    grouped = {}
    for city, sub in res.groupby('city'):
        grouped[city] = sub[['cee_id','cee_name','store','mg_target_per_day','current_per_day','mg_gap','per_ride_median','extra_orders','extra_shifts','recommendation']].to_dict(orient='records')
    with open(out_json, 'w') as f:
        json.dump(grouped, f, indent=2)
    print(f"[compute_mg_guidance] wrote {out_csv} and {out_json}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-i','--input', default='data/rider_week_clean.csv')
    ap.add_argument('-e','--per_ride_json', default='artifacts/earnings_per_ride.json')
    ap.add_argument('-o','--out_csv', default='artifacts/mg_guidance.csv')
    ap.add_argument('-j','--out_json', default='artifacts/mg_guidance.json')
    ap.add_argument('--orders_per_shift', type=int, default=10)
    args = ap.parse_args()
    main(args.input, args.per_ride_json, args.out_csv, args.out_json, target_orders_per_shift=args.orders_per_shift)


