from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd
from typing import List, Optional
from pathlib import Path


ZONES_CSV = Path("/data/zones.csv")
JOBS_ZONED_CSV = Path("/data/jobs_zoned.csv")


class Zone(BaseModel):
    id: str
    name: str
    centroid_lat: Optional[float] = None
    centroid_lng: Optional[float] = None


class ZoneSummary(BaseModel):
    zone_id: str
    demand_jobs: int
    total_base_payout: float
    total_final_payout: float
    total_incentives: float
    avg_final_payout: float


router = APIRouter(prefix="/zones", tags=["zones"])


def _load_zones() -> List[Zone]:
    if not ZONES_CSV.exists():
        # No zones computed; return NA fallback
        return [Zone(id="NA", name="Not assigned")] 
    df = pd.read_csv(ZONES_CSV)
    if df.empty:
        return [Zone(id="NA", name="Not assigned")]
    zones: List[Zone] = []
    for _, r in df.iterrows():
        zones.append(
            Zone(
                id=str(int(r["zone_id"])) if not pd.isna(r.get("zone_id")) else "NA",
                name=f"Zone {int(r['zone_id'])}" if not pd.isna(r.get("zone_id")) else "Not assigned",
                centroid_lat=float(r.get("centroid_lat")) if not pd.isna(r.get("centroid_lat")) else None,
                centroid_lng=float(r.get("centroid_lng")) if not pd.isna(r.get("centroid_lng")) else None,
            )
        )
    # Always include NA option for rows without zone
    zones.append(Zone(id="NA", name="Not assigned"))
    # Deduplicate by id, preserve order
    seen = set()
    unique: List[Zone] = []
    for z in zones:
        if z.id in seen:
            continue
        seen.add(z.id)
        unique.append(z)
    return unique


@router.get("/", response_model=List[Zone])
def list_zones():
    return _load_zones()


@router.get("/{zone_id}/summary", response_model=ZoneSummary)
def zone_summary(zone_id: str):
    if not JOBS_ZONED_CSV.exists():
        raise HTTPException(status_code=404, detail="No zoned jobs available. Run ETL first.")
    df = pd.read_csv(JOBS_ZONED_CSV)
    # Coerce numerics
    for col in ["base_payout", "final_payout"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if zone_id == "NA":
        df_zone = df[df["zone_id"].isna()] if "zone_id" in df.columns else df
    else:
        try:
            zid = int(zone_id)
            df_zone = df[df["zone_id"] == zid] if "zone_id" in df.columns else df.head(0)
        except ValueError:
            df_zone = df.head(0)

    demand = int(len(df_zone))
    total_base = float(df_zone.get("base_payout", pd.Series()).fillna(0).sum()) if demand else 0.0
    total_final = float(df_zone.get("final_payout", pd.Series()).fillna(0).sum()) if demand else 0.0
    total_incentives = max(0.0, round(total_final - total_base, 2))
    avg_final = float(df_zone.get("final_payout", pd.Series()).dropna().mean()) if demand else 0.0
    if pd.isna(avg_final):
        avg_final = float(df_zone.get("base_payout", pd.Series()).dropna().mean()) if demand else 0.0

    return ZoneSummary(
        zone_id=zone_id,
        demand_jobs=demand,
        total_base_payout=round(total_base, 2),
        total_final_payout=round(total_final, 2),
        total_incentives=round(total_incentives, 2),
        avg_final_payout=round(avg_final if not pd.isna(avg_final) else 0.0, 2),
    )


