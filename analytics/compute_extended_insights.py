import argparse
import pandas as pd
import numpy as np
import json, os

"""
Computes richer rider-facing insights per city/store:

Existing:
- Demand Score from earning/stability/ramp

New:
- Demand Saturation Score (orders per rider) — if total_orders available, else estimate
- Idle Time Risk Score (CV of earnings)
- New Rider Ramp-Up Time (proxy using NEW JOINER distribution)
- Best Shift (heuristic using cohort mix)
- Day-of-Week trend (if active_days present; else heuristic)
- Earnings Confidence (p25–p75)
- Recommended Riders/Day (target utilization)
- Top Performer Playbook (simple rules from top quartile)

Outputs:
- artifacts/demand_store_extended.csv
- artifacts/demand_store_extended.json
"""

def _safe_minmax(series: pd.Series) -> pd.Series:
    s = series.copy()
    if s.isna().all():
        return pd.Series([50.0]*len(s), index=s.index)
    s = s.fillna(s.median())
    mn, mx = s.min(), s.max()
    if mx == mn:
        return pd.Series([50.0]*len(s), index=s.index)
    return (s - mn) / (mx - mn) * 100.0

def _best_shift_from_mix(mix: dict) -> str:
    lsv = mix.get('LSV',0.0)
    nev = mix.get('NEV',0.0) + mix.get('NEW JOINER',0.0)
    if lsv >= 0.45 and (lsv - nev) >= 0.15:
        return "5–10 PM"
    if nev >= 0.45 and (nev - lsv) >= 0.15:
        return "10 AM–2 PM"
    return "12–8 PM"

def _star(score: float) -> str:
    if score >= 85: return "★★★★★"
    if score >= 70: return "★★★★☆"
    if score >= 55: return "★★★☆☆"
    if score >= 40: return "★★☆☆☆"
    return "★☆☆☆☆"

def _color(score: float) -> str:
    if score >= 70: return "green"
    if score >= 55: return "yellow"
    return "red"

def compute(df: pd.DataFrame, target_orders_per_rider_day: int = 22, avg_payout_per_order: float | None = None):
    # Base group
    g = df.groupby(['city','store'], dropna=True)

    # Core earning stats
    earning_median = g['final_with_gst'].median().rename('store_earning_index')
    earning_mean   = g['final_with_gst'].mean().rename('earning_mean')
    earning_std    = g['final_with_gst'].std().rename('earning_std')
    p25p75 = g['final_with_gst'].quantile([0.25,0.75]).unstack().rename(columns={0.25:'p25',0.75:'p75'})

    # Stability / Idle risk
    idle_risk = (earning_std / (earning_mean.replace({0:np.nan}))).rename('idle_time_risk')
    idle_risk = idle_risk.fillna(idle_risk.median())

    # New rider ramp score
    is_new = df['cee_category'].fillna("").str.upper().eq("NEW JOINER")
    ramp = df[is_new].groupby(['city','store'])['final_with_gst'].median().rename('new_rider_ramp_score')
    ramp = ramp.fillna(ramp.median())

    # Demand score (as before)
    earning_norm  = _safe_minmax(earning_median)
    stability_norm= _safe_minmax(1.0/(1.0 + earning_std.fillna(earning_std.median())))
    ramp_norm     = _safe_minmax(ramp)
    demand_score = (0.5*earning_norm + 0.3*stability_norm + 0.2*ramp_norm).rename('demand_score')

    # Cohort mix for best shift heuristic
    mix_tbl = df.groupby(['city','store','cee_category']).size().unstack(fill_value=0)
    mix_ratios = (mix_tbl.T / mix_tbl.sum(axis=1)).T
    best_shift_map = {idx: _best_shift_from_mix(row.to_dict()) for idx, row in mix_ratios.iterrows()}

    # Demand Saturation: orders per rider (if orders available)
    have_orders = 'total_orders' in df.columns
    riders_per_store = g['cee_id'].nunique().rename('riders_week')
    if have_orders:
        orders_week = g['total_orders'].sum().rename('orders_week')
        demand_saturation = (orders_week / riders_per_store.replace({0:np.nan})).rename('orders_per_rider_week')
    else:
        # Estimate from payouts if avg_payout_per_order provided, else skip
        orders_week = None
        if avg_payout_per_order:
            est_orders = (g['final_with_gst'].sum() / avg_payout_per_order).rename('orders_week')
            demand_saturation = (est_orders / riders_per_store.replace({0:np.nan})).rename('orders_per_rider_week')
        else:
            demand_saturation = pd.Series(index=earning_median.index, data=np.nan, name='orders_per_rider_week')

    # Recommended riders/day
    if have_orders:
        orders_per_day = (orders_week / 6.5).rename('orders_per_day')
        recommended_riders_day = (orders_per_day / target_orders_per_rider_day).rename('recommended_riders_day')
    else:
        if avg_payout_per_order:
            est_orders_week = (g['final_with_gst'].sum() / avg_payout_per_order).rename('orders_week')
            orders_per_day  = (est_orders_week / 6.5).rename('orders_per_day')
            recommended_riders_day = (orders_per_day / target_orders_per_rider_day).rename('recommended_riders_day')
        else:
            orders_per_day = pd.Series(index=earning_median.index, data=np.nan, name='orders_per_day')
            recommended_riders_day = pd.Series(index=earning_median.index, data=np.nan, name='recommended_riders_day')

    # Top performer playbook (from top quartile riders per store)
    q75 = g['final_with_gst'].quantile(0.75).rename('q75')
    playbook = {}
    for idx in earning_median.index:
        bs = best_shift_map.get(idx, "12–8 PM")
        q = q75.get(idx, np.nan)
        msg = f"Work {bs}; aim for 2 shifts/day. Focus on peak windows."
        if not np.isnan(q) and q >= earning_median.median():
            msg = f"High earners here work {bs} and 5 days/week."
        playbook[idx] = msg

    out = pd.concat([
        earning_median, earning_mean, earning_std, p25p75,
        ramp, demand_score, riders_per_store, demand_saturation,
        orders_per_day, recommended_riders_day
    ], axis=1)

    out = out.reset_index()
    out['best_shift'] = out.apply(lambda r: best_shift_map.get((r['city'], r['store']), "12–8 PM"), axis=1)
    out['stars'] = out['demand_score'].apply(_star)
    out['color'] = out['demand_score'].apply(_color)
    out['idle_time_risk'] = out['idle_time_risk'].fillna(out['idle_time_risk'].median()) if 'idle_time_risk' in out.columns else np.nan

    for c in ['store_earning_index','earning_mean','p25','p75','orders_per_day','recommended_riders_day','orders_per_rider_week','new_rider_ramp_score','demand_score']:
        if c in out.columns:
            out[c] = out[c].round(1)

    out['playbook'] = out.apply(lambda r: playbook.get((r['city'], r['store']), "Work 12–8 PM; steady flow."), axis=1)
    out = out.sort_values(['city','demand_score'], ascending=[True, False])
    return out

def main(input_csv: str, out_csv: str, out_json: str, target_orders_per_rider_day: int = 22, avg_payout_per_order: float | None = None):
    df = pd.read_csv(input_csv)
    needed = {'city','store','cee_category','final_with_gst'}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    res = compute(df, target_orders_per_rider_day=target_orders_per_rider_day, avg_payout_per_order=avg_payout_per_order)

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    os.makedirs(os.path.dirname(out_json), exist_ok=True)

    res.to_csv(out_csv, index=False)

    grouped = {}
    for city, sub in res.groupby('city'):
        grouped[city] = sub[['store','demand_score','stars','color','best_shift',
                             'p25','p75','store_earning_index','new_rider_ramp_score',
                             'idle_time_risk','orders_per_rider_week','orders_per_day',
                             'recommended_riders_day','riders_week','playbook']].to_dict(orient='records')
    with open(out_json, "w") as f:
        json.dump(grouped, f, indent=2)

    print(f"[compute_extended_insights] wrote {out_csv} and {out_json}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-i","--input", default="data/rider_week_clean.csv")
    ap.add_argument("-o","--out_csv", default="artifacts/demand_store_extended.csv")
    ap.add_argument("-j","--out_json", default="artifacts/demand_store_extended.json")
    ap.add_argument("--target_orders_per_rider_day", type=int, default=22)
    ap.add_argument("--avg_payout_per_order", type=float, default=None, help="If orders not available, estimate by payout/order")
    args = ap.parse_args()
    main(args.input, args.out_csv, args.out_json, args.target_orders_per_rider_day, args.avg_payout_per_order)


