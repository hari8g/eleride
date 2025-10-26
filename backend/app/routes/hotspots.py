from fastapi import APIRouter, HTTPException
from pathlib import Path
import pandas as pd
import requests
import os

router = APIRouter(prefix="/hotspots", tags=["hotspots"])

ZONES_CSV = Path("/data/zones.csv")
JOBS_ZONED_CSV = Path("/data/jobs_zoned.csv")
RIDER_CLEAN_CSV = Path("/data/rider_week_clean.csv")
GEOCODE_URL = "https://nominatim.openstreetmap.org/search"


@router.get("/")
def list_hotspots():
    # If clustered zones exist, use them
    if ZONES_CSV.exists() and JOBS_ZONED_CSV.exists():
        zones = pd.read_csv(ZONES_CSV)
        jobs = pd.read_csv(JOBS_ZONED_CSV)
        counts = jobs['zone_id'].value_counts(dropna=False).to_dict() if 'zone_id' in jobs.columns else {}
        features = []
        for _, r in zones.iterrows():
            zid = r.get('zone_id')
            lat = r.get('centroid_lat')
            lng = r.get('centroid_lng')
            if pd.isna(lat) or pd.isna(lng):
                continue
            count = int(counts.get(zid, 0))
            features.append({'label': f"Zone {int(zid)}" if not pd.isna(zid) else 'Zone', 'lat': float(lat), 'lng': float(lng), 'count': count})
        if features:
            return {'features': features}

    # Fallback: geocode store-based location_query to lat/lng
    if not RIDER_CLEAN_CSV.exists():
        raise HTTPException(status_code=404, detail="No data to derive hotspots")
    df = pd.read_csv(RIDER_CLEAN_CSV)
    if 'location_query' not in df.columns:
        raise HTTPException(status_code=400, detail="location_query not present; re-run preprocess")
    # frequency by location
    loc_counts = df['location_query'].value_counts().head(50)
    headers = { 'User-Agent': 'ev-orchestrator/1.0 (map-hotspots)' }
    features = []
    for loc, cnt in loc_counts.items():
        if not isinstance(loc, str) or not loc.strip():
            continue
        try:
            params = { 'q': loc, 'format': 'json', 'limit': 1 }
            resp = requests.get(GEOCODE_URL, params=params, headers=headers, timeout=5)
            if resp.ok:
                arr = resp.json()
                if arr:
                    lat = float(arr[0]['lat']); lng = float(arr[0]['lon'])
                    features.append({ 'label': loc, 'lat': lat, 'lng': lng, 'count': int(cnt) })
        except Exception:
            continue
    return { 'features': features }


