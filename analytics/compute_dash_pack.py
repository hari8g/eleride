import argparse
import pandas as pd
import numpy as np
import json, os

"""
Builds a consolidated analytics pack JSON for multiple dashboard tabs.

Input: data/rider_week_clean.csv (from preprocess_xls)
Output: artifacts/dash_pack.json (grouped by city)
"""


def _nan_to_none(o):
    if isinstance(o, dict):
        return {k: _nan_to_none(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_nan_to_none(v) for v in o]
    if isinstance(o, float) and (np.isnan(o) or np.isinf(o)):
        return None
    return o


def build_pack(df: pd.DataFrame) -> dict:
    d = df.copy()
    # Ensure numeric
    numeric_cols = [
        'final_with_gst','total_with_arrears_and_deductions','base_pay','incentive_total',
        'surge_payout','peak_hour_payout','minimum_guarantee','management_fee','deductions_amount',
        'total_cash_adjustment','total_orders','attendance','online_hours','weekday_orders','weekend_orders',
        'distance_km'
    ]
    for c in numeric_cols:
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors='coerce')

    # Demand-like helper
    g = d.groupby(['city','store'], dropna=True)

    # Incentives breakdown per store
    g_index = g.size().index
    def _sum_or_zero(col):
        return g[col].sum() if col in d.columns else pd.Series(0, index=g_index)
    inc = pd.DataFrame({
        'base_pay': _sum_or_zero('base_pay'),
        'incentive_total': _sum_or_zero('incentive_total'),
        'surge_payout': _sum_or_zero('surge_payout'),
        'peak_hour_payout': _sum_or_zero('peak_hour_payout'),
        'minimum_guarantee': _sum_or_zero('minimum_guarantee'),
    }).reset_index()

    # Payouts waterfall
    pay = pd.DataFrame({
        'final_with_gst': _sum_or_zero('final_with_gst'),
        'management_fee': _sum_or_zero('management_fee'),
        'deductions_amount': _sum_or_zero('deductions_amount'),
        'total_cash_adjustment': _sum_or_zero('total_cash_adjustment'),
        'net_after_adj': _sum_or_zero('total_with_arrears_and_deductions'),
    }).reset_index()

    # Productivity
    def _sum_or_nan(col):
        return g[col].sum() if col in d.columns else pd.Series(np.nan, index=g_index)
    prod = pd.DataFrame({
        'total_orders': _sum_or_nan('total_orders'),
        'attendance': _sum_or_nan('attendance'),
        'online_hours': _sum_or_nan('online_hours'),
        'distance_km': _sum_or_nan('distance_km'),
    }).reset_index()
    if 'total_orders' in prod.columns:
        prod['orders_per_day'] = prod['total_orders'] / 6.5
    else:
        prod['orders_per_day'] = np.nan
    prod['avg_dist_per_order'] = np.where(prod['total_orders']>0, prod['distance_km']/prod['total_orders'], np.nan)

    # Weekend split
    wknd = pd.DataFrame({
        'weekday_orders': _sum_or_nan('weekday_orders'),
        'weekend_orders': _sum_or_nan('weekend_orders'),
    }).reset_index()

    # Ramp (new joiner vs experienced)
    d['is_new'] = d['cee_category'].astype(str).str.upper().eq('NEW JOINER') if 'cee_category' in d.columns else False
    ramp_new = d[d['is_new']].groupby(['city','store'])['final_with_gst'].median()
    ramp_exp = d[~d['is_new']].groupby(['city','store'])['final_with_gst'].median()
    ramp = pd.DataFrame({
        'new_median': ramp_new,
        'exp_median': ramp_exp,
    }).reset_index()
    ramp['delta'] = (ramp['new_median'] - ramp['exp_median']).round(1)

    # Risk (CV of earnings per store)
    earn_std = g['final_with_gst'].std()
    earn_mean = g['final_with_gst'].mean()
    risk = pd.DataFrame({'cv': (earn_std / earn_mean.replace({0: np.nan}))}).reset_index()

    # Cohort mix
    if 'cee_category' in d.columns:
        mix_tbl = d.groupby(['city','store','cee_category']).size().unstack(fill_value=0)
        mix_ratios = (mix_tbl.T / mix_tbl.sum(axis=1)).T.reset_index()
    else:
        mix_ratios = pd.DataFrame(columns=['city','store'])

    # Leaderboard (earning median)
    lb = pd.DataFrame({'earning_median': g['final_with_gst'].median()}).reset_index()

    # Merge frames into dict per city
    pack = {}
    for city, sub in d.groupby('city'):
        city_inc = inc[inc['city'] == city].drop(columns=['city']).to_dict(orient='records')
        city_pay = pay[pay['city'] == city].drop(columns=['city']).to_dict(orient='records')
        city_prod = prod[prod['city'] == city].drop(columns=['city']).to_dict(orient='records')
        city_wknd = wknd[wknd['city'] == city].drop(columns=['city']).to_dict(orient='records')
        city_ramp = ramp[ramp['city'] == city].drop(columns=['city']).to_dict(orient='records')
        city_risk = risk[risk['city'] == city].drop(columns=['city']).to_dict(orient='records')
        if not mix_ratios.empty:
            city_mix = mix_ratios[mix_ratios['city'] == city].drop(columns=['city']).to_dict(orient='records')
        else:
            city_mix = []
        city_lb = lb[lb['city'] == city].drop(columns=['city']).to_dict(orient='records')
        pack[city] = {
            'incentives': city_inc,
            'payouts': city_pay,
            'productivity': city_prod,
            'weekend': city_wknd,
            'ramp': city_ramp,
            'risk': city_risk,
            'cohort': city_mix,
            'leaderboard': city_lb,
        }
    return _nan_to_none(pack)


def main(input_csv: str, out_json: str):
    df = pd.read_csv(input_csv)
    if 'city' not in df.columns or 'store' not in df.columns:
        raise ValueError('city/store columns required')
    pack = build_pack(df)
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_json, 'w') as f:
        json.dump(pack, f, indent=2)
    print(f"[compute_dash_pack] wrote {out_json}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-i','--input', default='data/rider_week_clean.csv')
    ap.add_argument('-j','--out_json', default='artifacts/dash_pack.json')
    args = ap.parse_args()
    main(args.input, args.out_json)


