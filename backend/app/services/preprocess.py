import pandas as pd
import numpy as np
from datetime import datetime
from math import radians, cos, sin, asin, sqrt
import logging

logger = logging.getLogger("preprocess")
logging.basicConfig(level=logging.INFO)

def haversine(lat1, lon1, lat2, lon2):
    if any(pd.isna(x) for x in [lat1, lon1, lat2, lon2]):
        return np.nan
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return 6371 * c

def parse_datetime(x):
    if pd.isna(x):
        return pd.NaT
    try:
        return pd.to_datetime(x, utc=True)
    except Exception:
        try:
            return pd.to_datetime(x)
        except Exception:
            return pd.NaT

# Mapping suggestions (extend if your Excel has other names)
COLUMN_MAP = {
    'order_id':'job_id','orderid':'job_id','job_id':'job_id',
    'timestamp':'created_at',
    'pickup_lat':'pickup_lat','pickup_long':'pickup_lng','pickup_lng':'pickup_lng',
    'drop_lat':'drop_lat','drop_long':'drop_lng','drop_lng':'drop_lng',
    'dropoff_lat':'drop_lat','dropoff_lng':'drop_lng',
    'created_at':'created_at','order_time':'created_at','createdon':'created_at',
    'scheduled_at':'scheduled_at','pickup_time':'scheduled_at',
    'completed_at':'completed_at','delivered_at':'completed_at','finish_time':'completed_at',
    'base_payout':'base_payout','base':'base_payout',
    'surge':'surge','bonus':'surge',
    'final_payout':'final_payout','total_payout':'final_payout','payout':'final_payout',
    'price_usd':'final_payout',
    'rider_id':'rider_id','driver_id':'rider_id',
    'cancellation_flag':'cancellation_flag','cancel_flag':'cancellation_flag',
    'cancellation_reason':'cancellation_reason'
}

REQUIRED_FIELDS = ['job_id','pickup_lat','pickup_lng','created_at']

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Lowercase source column names for matching
    lower_map = {c.lower(): c for c in df.columns}
    rename_map = {}
    for src_key, target in COLUMN_MAP.items():
        if src_key in lower_map:
            rename_map[lower_map[src_key]] = target
    df = df.rename(columns=rename_map)
    return df

def fill_missing_fields(df: pd.DataFrame) -> pd.DataFrame:
    # Ensure required columns exist (fill NAs if not)
    for c in ['job_id','pickup_lat','pickup_lng','drop_lat','drop_lng','created_at','scheduled_at','completed_at','base_payout','final_payout','surge','rider_id','cancellation_reason','store']:
        if c not in df.columns:
            df[c] = np.nan
    return df

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Normalizing column names...")
    df = normalize_columns(df)
    df = fill_missing_fields(df)
    # synthesize job_id if missing
    if 'job_id' not in df.columns or df['job_id'].isna().all():
        def make_id(row, idx):
            parts = []
            if 'cee_id' in row and not pd.isna(row['cee_id']):
                parts.append(str(row['cee_id']))
            if 'year' in row and not pd.isna(row['year']):
                parts.append(f"y{int(row['year'])}")
            if 'week' in row and not pd.isna(row['week']):
                parts.append(f"w{int(row['week'])}")
            parts.append(str(idx))
            return "-".join(parts)
        df = df.reset_index(drop=True)
        df['job_id'] = [make_id(df.loc[i], i) for i in range(len(df))]
    # ensure created_at exists
    if 'created_at' not in df.columns or df['created_at'].isna().all():
        if 'year' in df.columns and 'month' in df.columns:
            def mk_date(y, m):
                try:
                    return pd.to_datetime({'year':[int(y)],'month':[int(m)],'day':[1]}).iloc[0]
                except Exception:
                    return pd.Timestamp.utcnow()
            df['created_at'] = [mk_date(y, m) for y, m in zip(df.get('year', []), df.get('month', []))]
        else:
            df['created_at'] = pd.Timestamp.utcnow()
    # parse dates
    for d in ['created_at','scheduled_at','completed_at']:
        if d in df.columns:
            df[d] = df[d].apply(parse_datetime)
    # compute distances
    logger.info("Computing haversine distances...")
    df['distance_km'] = df.apply(lambda r: haversine(r.get('pickup_lat'), r.get('pickup_lng'), r.get('drop_lat'), r.get('drop_lng')), axis=1)
    # duration in seconds
    if 'completed_at' in df.columns and 'scheduled_at' in df.columns:
        df['duration_seconds'] = (df['completed_at'] - df['scheduled_at']).dt.total_seconds()
    else:
        df['duration_seconds'] = np.nan
    # standardize numeric payout fields (include Excel payout columns)
    payout_cols = [
        'base_payout','surge','final_payout','distance_km',
        'base_pay','incentive_total',
        'total_without_arrears','total_with_arrears','total_with_arrears_and_deductions',
        'total_with_management_fee','final_with_gst','final_with_gst_minus_settlement'
    ]
    for num in payout_cols:
        if num in df.columns:
            df[num] = pd.to_numeric(df[num], errors='coerce')
    # cancellations
    if 'cancellation_flag' not in df.columns:
        df['cancellation_flag'] = df['cancellation_reason'].notna().astype(int) if 'cancellation_reason' in df.columns else 0
    # dedupe by job_id
    if 'job_id' in df.columns:
        df = df.sort_values(by='created_at', na_position='first').drop_duplicates(subset=['job_id'], keep='last')
    # final column order
    cols = [
        'job_id','store','pickup_lat','pickup_lng','drop_lat','drop_lng','created_at','scheduled_at','completed_at',
        'distance_km','duration_seconds',
        # Core payouts
        'base_payout','surge','final_payout','base_pay','incentive_total',
        'total_without_arrears','total_with_arrears','total_with_arrears_and_deductions',
        'total_with_management_fee','final_with_gst','final_with_gst_minus_settlement',
        'rider_id','cancellation_flag','cancellation_reason'
    ]
    present = [c for c in cols if c in df.columns]
    return df[present]

def read_input(path: str) -> pd.DataFrame:
    if path.lower().endswith('.xlsx') or path.lower().endswith('.xls'):
        # if multiple sheets, pick first (customize if needed)
        df = pd.read_excel(path, sheet_name=0)
    else:
        df = pd.read_csv(path)
    return df

def run_preprocess(input_path: str, output_csv: str):
    logger.info(f"Reading input {input_path} ...")
    df = read_input(input_path)
    logger.info(f"Raw rows: {len(df)}")
    clean = clean_dataframe(df)
    logger.info(f"Clean rows: {len(clean)}")
    clean.to_csv(output_csv, index=False)
    logger.info(f"Wrote cleaned CSV to {output_csv}")
    return output_csv
