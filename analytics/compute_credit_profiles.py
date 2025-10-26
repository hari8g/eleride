import argparse
import pandas as pd
import numpy as np
import json, os

"""
Compute driver credit profiles per city based on earning potential and history:
- Earning potential: median(final_with_gst)
- Stability: inverse CV (mean/std)
- Activity: orders_per_day from total_orders / 6.5
- Attendance proxy: attendance / 6.5
- Tenure proxy: active_days if present else attendance

Outputs:
- artifacts/credit_profiles.csv
- artifacts/credit_profiles.json (grouped by city)
"""


def _safe(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors='coerce')
    return s


def _minmax(s: pd.Series) -> pd.Series:
    s = s.copy()
    if s.isna().all():
        return pd.Series([50.0]*len(s), index=s.index)
    s = s.fillna(s.median())
    mn, mx = s.min(), s.max()
    if mx == mn:
        return pd.Series([50.0]*len(s), index=s.index)
    return (s - mn) / (mx - mn) * 100.0


def compute(df: pd.DataFrame):
    d = df.copy()
    # Ensure fields
    for c in ['final_with_gst','total_orders','attendance','active_days']:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors='coerce')
    d['city'] = d['city'].astype(str)
    d['store'] = d['store'].astype(str)
    d['cee_id'] = d.get('cee_id', pd.Series(dtype=float))
    d['cee_name'] = d.get('cee_name', pd.Series(dtype=str))

    # Group by driver within city
    gb = d.groupby(['city','cee_id'], dropna=True)
    earning_median = gb['final_with_gst'].median().rename('earning_median')
    earning_mean = gb['final_with_gst'].mean().rename('earning_mean')
    earning_std = gb['final_with_gst'].std().fillna(0).rename('earning_std')
    cv = (earning_std / earning_mean.replace({0: np.nan})).rename('cv')
    total_orders = gb['total_orders'].sum().rename('total_orders') if 'total_orders' in d.columns else pd.Series(index=earning_median.index, data=np.nan)
    attendance = gb['attendance'].sum().rename('attendance') if 'attendance' in d.columns else pd.Series(index=earning_median.index, data=np.nan)
    active_days = gb['active_days'].sum().rename('active_days') if 'active_days' in d.columns else pd.Series(index=earning_median.index, data=np.nan)
    orders_per_day = (total_orders / 6.5).rename('orders_per_day')
    attendance_per_week = (attendance / 6.5).rename('attendance_per_week')

    # Predominant store per driver (mode by frequency)
    top_store = gb['store'].agg(lambda s: s.mode().iat[0] if not s.mode().empty else (s.iloc[0] if len(s) else '')).rename('store')
    cee_name = gb['cee_name'].agg(lambda s: s.dropna().iloc[0] if len(s.dropna()) else '').rename('cee_name')

    out = pd.concat([
        earning_median, earning_mean, earning_std, cv,
        total_orders, orders_per_day, attendance, attendance_per_week, active_days,
        top_store, cee_name
    ], axis=1)

    # Normalize components to build score
    earn_norm = _minmax(out['earning_median'])
    stability_norm = _minmax(1.0/(1.0 + out['cv'].fillna(out['cv'].median())))
    activity_norm = _minmax(out['orders_per_day'])
    attendance_norm = _minmax(out['attendance_per_week'])

    score = (0.45*earn_norm + 0.25*stability_norm + 0.2*activity_norm + 0.1*attendance_norm).round(1)
    out['credit_score'] = score

    def band(s: float) -> str:
        if pd.isna(s):
            return 'Unknown'
        if s >= 80: return 'A+'
        if s >= 70: return 'A'
        if s >= 60: return 'B'
        if s >= 50: return 'C'
        return 'D'
    out['band'] = out['credit_score'].apply(band)

    out = out.reset_index()
    # Round presentable fields
    for c in ['earning_median','orders_per_day','attendance_per_week']:
        if c in out.columns:
            out[c] = out[c].round(1)
    out['earning_std'] = out['earning_std'].round(1)

    return out


def main(input_csv: str, out_csv: str, out_json: str):
    df = pd.read_csv(input_csv)
    needed = {'city','store','cee_id','cee_name','final_with_gst'}
    missing = needed - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    res = compute(df)
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    res.to_csv(out_csv, index=False)

    grouped = {}
    for city, sub in res.groupby('city'):
        grouped[city] = sub[['cee_id','cee_name','store','credit_score','band','earning_median','orders_per_day','attendance_per_week']].to_dict(orient='records')
    with open(out_json, 'w') as f:
        json.dump(grouped, f, indent=2)
    print(f"[compute_credit_profiles] wrote {out_csv} and {out_json}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-i','--input', default='data/rider_week_clean.csv')
    ap.add_argument('-o','--out_csv', default='artifacts/credit_profiles.csv')
    ap.add_argument('-j','--out_json', default='artifacts/credit_profiles.json')
    args = ap.parse_args()
    main(args.input, args.out_csv, args.out_json)


