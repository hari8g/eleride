import argparse
import pandas as pd
import numpy as np
from datetime import datetime
import os
import re

# Minimal preprocessing for weekly rider payout XLS:
# - Reads first sheet
# - Normalizes key columns used downstream
# - Keeps optional cols if present (e.g., total_orders, online_hours) to improve insights

BASE_COLS = [
    'year','month','week','city','store','cee_id','cee_name',
    'cee_employment_category','cee_category',
    'final_with_gst','total_with_arrears_and_deductions'
]

OPTIONAL_COLS = [
    'total_orders','online_hours','active_days','avg_shift_hours',
    'weekday_orders','weekend_orders',
    # incentives/payouts
    'base_pay','incentive_total','surge_payout','peak_hour_payout','minimum_guarantee',
    'management_fee','deductions_amount','total_cash_adjustment',
    # distance
    'distance_km',
    # mg
    'mg_eligible_days'
]

ALIASES = {
    'final_with_gst': ['final_with_gst','finalwithgst','final_withgst','final'],
    'total_with_arrears_and_deductions': ['total_with_arrears_and_deductions','total_arrears','total_with_arrears'],
    'cee_category': ['cee_category','category'],
    'cee_employment_category': ['cee_employment_category','employment_category'],
    'total_orders': ['orders','total_orders','deliveries','total_deliveries','delivered_orders'],
    'online_hours': ['online_hours','active_hours','duty_hours'],
    'active_days': ['active_days','working_days'],
    'avg_shift_hours': ['avg_shift_hours','avg_hours'],
    'mg_eligible_days': ['mg_eligible_days','mg_eligible','mgdays']
    ,
    # distance column in XLS is 'y'
    'distance_km': ['distance_km','distance','dist_km','y']
}

def canonicalize(df: pd.DataFrame) -> pd.DataFrame:
    lower = {c.lower(): c for c in df.columns}
    rename = {}
    for target, aliases in ALIASES.items():
        for a in aliases:
            if a in lower and target not in df.columns:
                rename[lower[a]] = target
                break
    if rename:
        df = df.rename(columns=rename)
    return df

def load_first_sheet(path: str) -> pd.DataFrame:
    if path.lower().endswith((".xls",".xlsx")):
        x = pd.ExcelFile(path)
        return x.parse(x.sheet_names[0])
    return pd.read_csv(path)

def run(input_path: str, output_csv: str):
    df = load_first_sheet(input_path)
    df = canonicalize(df)

    # keep columns if present
    keep = [c for c in BASE_COLS if c in df.columns] + [c for c in OPTIONAL_COLS if c in df.columns]
    # ensure required categorical keys
    for c in ['city','store','cee_category','cee_employment_category']:
        if c not in df.columns:
            df[c] = np.nan
    df['city'] = df['city'].astype(str).str.upper()
    df['store'] = df['store'].astype(str).str.upper()
    df['cee_category'] = df['cee_category'].astype(str).str.upper()
    df['cee_employment_category'] = df['cee_employment_category'].astype(str).str.upper()

    # numeric coercions
    for num in ['final_with_gst','total_with_arrears_and_deductions','total_orders','online_hours','active_days','avg_shift_hours','weekday_orders','weekend_orders','base_pay','incentive_total','surge_payout','peak_hour_payout','minimum_guarantee','management_fee','deductions_amount','total_cash_adjustment','mg_eligible_days']:
        if num in df.columns:
            df[num] = pd.to_numeric(df[num], errors='coerce')

    # derive total_orders if absent but weekday/weekend present
    if 'total_orders' not in df.columns and {'weekday_orders','weekend_orders'}.issubset(set(df.columns)):
        df['total_orders'] = (df['weekday_orders'].fillna(0) + df['weekend_orders'].fillna(0))
        keep.append('total_orders')

    # drop rows without city/store
    df = df.dropna(subset=['city','store'])

    # trim output
    # derive a map-friendly location string from store + city
    def extract_location(store: str, city: str) -> str:
        s = str(store or '').upper()
        city_str = (str(city or '')).title()
        # split tokens, drop obvious brand/code prefixes
        tokens = re.split(r"[-_]+", s)
        drop = {"T1EX","BSPUN","BS","BS1","BS2","BS3","BS4","BGS1","BGS2","BGS3"}
        tokens = [t for t in tokens if t and t not in drop]
        # pick last alpha-dominant token as area
        area = ''
        for t in reversed(tokens):
            if re.search(r"[A-Z]", t) and len(t) >= 3:
                area = t
                break
        area = area.title()
        if area and city_str:
            return f"{area}, {city_str}, India"
        return (area or city_str) or ''

    df['location_query'] = df.apply(lambda r: extract_location(r.get('store'), r.get('city')), axis=1)
    if 'location_query' not in keep:
        keep.append('location_query')

    out = df[[c for c in keep if c in df.columns]].copy()
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    out.to_csv(output_csv, index=False)
    print(f"[preprocess_xls] wrote {output_csv} with {len(out)} rows and {len(out.columns)} columns")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-i","--input", required=True, help="Path to XLS/XLSX/CSV file")
    ap.add_argument("-o","--output", default="data/rider_week_clean.csv", help="Output CSV")
    args = ap.parse_args()
    run(args.input, args.output)


