import argparse
import pandas as pd
import numpy as np
import json, os

"""
Compute per-ride earning potential per city/store.

Inputs: data/rider_week_clean.csv (from preprocess_xls)
Uses columns: city, store, final_with_gst, total_orders (optional)

Outputs:
- artifacts/earnings_per_ride.csv
- artifacts/earnings_per_ride.json (grouped by city)
"""


def compute(df: pd.DataFrame, fallback_avg_payout_per_order: float | None = None):
    # Only rows with final_with_gst
    df = df.copy()
    df['final_with_gst'] = pd.to_numeric(df.get('final_with_gst'), errors='coerce')
    if 'total_orders' in df.columns:
        df['total_orders'] = pd.to_numeric(df['total_orders'], errors='coerce')
    else:
        df['total_orders'] = np.nan

    # per-ride by rider if orders present
    df['per_ride'] = np.where(df['total_orders'] > 0, df['final_with_gst'] / df['total_orders'], np.nan)

    # group by city/store
    g = df.groupby(['city','store'], dropna=True)

    # aggregate from observed per_ride
    per_ride_series = g['per_ride'].apply(lambda s: s.dropna())
    stats = g['per_ride'].agg(['count','mean','median','std'])
    q = g['per_ride'].quantile([0.25,0.75]).unstack().rename(columns={0.25:'p25',0.75:'p75'})
    out = stats.join(q)

    # if per-ride unavailable (no orders), fallback estimation using cohort average from store
    # compute store-level avg using riders with orders; if missing entirely and fallback provided, use fallback
    store_avg = out['mean']

    # build final table
    out = out.reset_index()
    out = out.rename(columns={'count':'num_samples','mean':'per_ride_avg','median':'per_ride_median','std':'per_ride_std'})

    # fill NaNs with medians across stores or fallback
    for c in ['per_ride_avg','per_ride_median','per_ride_std','p25','p75']:
        if c in out.columns:
            if out[c].isna().all() and fallback_avg_payout_per_order is not None:
                out[c] = fallback_avg_payout_per_order
            else:
                out[c] = out[c].fillna(out[c].median())

    # round
    for c in ['per_ride_avg','per_ride_median','per_ride_std','p25','p75']:
        if c in out.columns:
            out[c] = out[c].round(1)

    return out


def main(input_csv: str, out_csv: str, out_json: str, fallback_avg_payout_per_order: float | None = None):
    df = pd.read_csv(input_csv)
    needed = {'city','store','final_with_gst'}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    res = compute(df, fallback_avg_payout_per_order=fallback_avg_payout_per_order)

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    res.to_csv(out_csv, index=False)

    grouped = {}
    for city, sub in res.groupby('city'):
        grouped[city] = sub[['store','per_ride_avg','per_ride_median','p25','p75','per_ride_std','num_samples']].to_dict(orient='records')
    with open(out_json, 'w') as f:
        json.dump(grouped, f, indent=2)
    print(f"[compute_per_ride_earnings] wrote {out_csv} and {out_json}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('-i','--input', default='data/rider_week_clean.csv')
    ap.add_argument('-o','--out_csv', default='artifacts/earnings_per_ride.csv')
    ap.add_argument('-j','--out_json', default='artifacts/earnings_per_ride.json')
    ap.add_argument('--fallback_avg_payout_per_order', type=float, default=None)
    args = ap.parse_args()
    main(args.input, args.out_csv, args.out_json, args.fallback_avg_payout_per_order)


