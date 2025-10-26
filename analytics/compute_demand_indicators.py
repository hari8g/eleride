import argparse
import pandas as pd
import numpy as np
import json
import os

# This computes:
# 1) Store_Earning_Index  = median(final_with_gst) per store
# 2) Stability_Index      = 1 / (1 + std(final_with_gst)) per store  (bounded)
# 3) New_Rider_Ramp_Score = median(final_with_gst for NEW JOINER) per store
# Then normalizes each 0–100 and creates Demand_Score = 0.5*Earning + 0.3*Stability + 0.2*Ramp
# Also derives a 'Best Shift' heuristic by store using cee_category mix.

def _safe_minmax(series: pd.Series) -> pd.Series:
    s = series.fillna(series.median())
    mn, mx = s.min(), s.max()
    if pd.isna(mn) or pd.isna(mx) or mx == mn:
        return pd.Series([50.0]*len(s), index=s.index)  # flat 50 if no variation
    return (s - mn) / (mx - mn) * 100.0

def _best_shift_from_mix(mix):
    # mix is dict like {'LSV':0.4, 'NEV':0.3, 'NEW JOINER':0.3}
    lsv = mix.get('LSV', 0.0)
    nev = mix.get('NEV', 0.0) + mix.get('NEW JOINER', 0.0)
    # Simple heuristic:
    if lsv >= 0.45 and lsv - nev >= 0.15:
        return "5–10 PM"
    if nev >= 0.45 and nev - lsv >= 0.15:
        return "10 AM–2 PM"
    return "12–8 PM"

def compute(df: pd.DataFrame):
    # by store
    g = df.groupby(['city','store'], dropna=True)

    earning = g['final_with_gst'].median().rename('store_earning_index')
    stability = (1.0 / (1.0 + g['final_with_gst'].std())).rename('stability_index')
    # ramp: NEW JOINER median
    is_new = df['cee_category'].fillna("").str.upper().eq("NEW JOINER")
    ramp = df[is_new].groupby(['city','store'])['final_with_gst'].median().rename('new_rider_ramp_score')

    base = pd.concat([earning, stability, ramp], axis=1)

    # fill NaNs
    for c in base.columns:
        base[c] = base[c].fillna(base[c].median())

    # normalize 0–100
    base['earning_norm'] = _safe_minmax(base['store_earning_index'])
    base['stability_norm'] = _safe_minmax(base['stability_index'])
    base['ramp_norm'] = _safe_minmax(base['new_rider_ramp_score'])

    # composite
    base['demand_score'] = (0.5*base['earning_norm'] + 0.3*base['stability_norm'] + 0.2*base['ramp_norm']).round(1)

    # cohort mix per store for shift heuristic
    mix_tbl = df.groupby(['city','store','cee_category']).size().unstack(fill_value=0)
    mix_ratios = (mix_tbl.T / mix_tbl.sum(axis=1)).T
    best_shift = {}
    for idx, row in mix_ratios.iterrows():
        best_shift[idx] = _best_shift_from_mix(row.to_dict())

    base = base.reset_index()
    base['best_shift'] = base.apply(lambda r: best_shift.get((r['city'], r['store']), "12–8 PM"), axis=1)

    # helpful summaries for UI
    # weekly earning range from 25th–75th percentile
    q = df.groupby(['city','store'])['final_with_gst'].quantile([0.25,0.75]).unstack().rename(columns={0.25:'p25',0.75:'p75'})
    out = base.merge(q, on=['city','store'], how='left')

    # star rating & color
    def star(score):
        if score >= 85: return "★★★★★"
        if score >= 70: return "★★★★☆"
        if score >= 55: return "★★★☆☆"
        if score >= 40: return "★★☆☆☆"
        return "★☆☆☆☆"
    def color(score):
        if score >= 70: return "green"
        if score >= 55: return "yellow"
        return "red"
    out['stars'] = out['demand_score'].apply(star)
    out['color'] = out['demand_score'].apply(color)

    # round certain fields
    out['store_earning_index'] = out['store_earning_index'].round(0)
    out['new_rider_ramp_score'] = out['new_rider_ramp_score'].round(0)
    out['p25'] = out['p25'].round(0)
    out['p75'] = out['p75'].round(0)

    # sort by city, demand descending
    out = out.sort_values(['city','demand_score'], ascending=[True, False])
    return out

def main(input_csv: str, out_csv: str, out_json: str):
    df = pd.read_csv(input_csv)
    # sanity: ensure required columns
    needed = {'city','store','cee_category','final_with_gst'}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    res = compute(df)

    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    os.makedirs(os.path.dirname(out_json), exist_ok=True)

    res.to_csv(out_csv, index=False)

    # JSON grouped by city for frontend consumption
    grouped = {}
    for city, sub in res.groupby('city'):
        grouped[city] = sub[['store','demand_score','stars','color','best_shift','p25','p75','store_earning_index','new_rider_ramp_score']].to_dict(orient='records')
    with open(out_json, "w") as f:
        json.dump(grouped, f, indent=2)
    print(f"[compute_demand_indicators] wrote {out_csv} and {out_json}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-i","--input", default="data/rider_week_clean.csv")
    ap.add_argument("-o","--out_csv", default="artifacts/demand_store.csv")
    ap.add_argument("-j","--out_json", default="artifacts/demand_store.json")
    args = ap.parse_args()
    main(args.input, args.out_csv, args.out_json)


