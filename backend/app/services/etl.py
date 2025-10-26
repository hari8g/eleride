import logging
from .preprocess import run_preprocess
from .zones import cluster_jobs, assign_zone_to_jobs
from .model_train import train_payout_model
from ..db import SessionLocal
from .. import crud, schemas
import pandas as pd

logger = logging.getLogger("etl")
logging.basicConfig(level=logging.INFO)

def ingest_to_db(clean_csv_path: str):
    """Read the cleaned CSV and insert rows into the jobs table (idempotent)."""
    df = pd.read_csv(clean_csv_path, parse_dates=['created_at','scheduled_at','completed_at'])
    db = SessionLocal()
    inserted = 0
    try:
        for _, r in df.iterrows():
            external_job_id = str(r.get("job_id")) if not pd.isna(r.get("job_id")) else None
            if not external_job_id:
                continue
            if crud.get_job_by_external_id(db, external_job_id):
                continue

            ts = r.get("created_at")
            if pd.isna(ts):
                ts = pd.Timestamp.utcnow()

            price = r.get("final_payout")
            if pd.isna(price):
                price = r.get("base_payout")
            if pd.isna(price):
                price = r.get("price_usd")

            dist = r.get("distance_km")
            energy = r.get("energy_kwh")
            if pd.isna(energy):
                energy = (float(dist) * 0.2) if dist is not None and not pd.isna(dist) else 10.0

            zone_val = r.get("zone_id")
            zone = None
            if zone_val is not None and not pd.isna(zone_val):
                try:
                    zone = str(int(zone_val))
                except Exception:
                    zone = str(zone_val)

            job_in = schemas.JobCreate(
                external_job_id=external_job_id,
                timestamp=pd.to_datetime(ts).to_pydatetime(),
                pickup_lat=float(r.get("pickup_lat")) if not pd.isna(r.get("pickup_lat")) else 0.0,
                pickup_lng=float(r.get("pickup_lng")) if not pd.isna(r.get("pickup_lng")) else 0.0,
                dropoff_lat=float(r.get("drop_lat")) if not pd.isna(r.get("drop_lat")) else 0.0,
                dropoff_lng=float(r.get("drop_lng")) if not pd.isna(r.get("drop_lng")) else 0.0,
                energy_kwh=float(energy),
                price_usd=float(price) if price is not None and not pd.isna(price) else None,
                zone=zone,
            )
            crud.create_job(db, job_in)
            inserted += 1
    finally:
        db.close()
    logger.info("Ingested %d rows into DB", inserted)
    return inserted

def run_full_etl(input_path: str, cleaned_csv_out: str = "/data/jobs_clean.csv", k_clusters: int = 12, train_model: bool = True):
    # 1. Preprocess
    cleaned = run_preprocess(input_path, cleaned_csv_out)
    # 2. Zone clustering (produce jobs_zoned.csv and zones.csv)
    zones_csv, jobs_zoned_csv = cluster_jobs(cleaned, k=k_clusters)
    # 3. Optionally train payout model
    if train_model:
        model_path = train_payout_model(jobs_zoned_csv)
        logger.info("Payout model trained at %s", model_path)
    # 4. Insert into DB
    ingest_to_db(jobs_zoned_csv)
    return {"cleaned_csv": cleaned, "jobs_zoned_csv": jobs_zoned_csv, "zones_csv": zones_csv}
