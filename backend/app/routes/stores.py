from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from pathlib import Path
import pandas as pd


CLEAN_CSV = Path("/data/jobs_clean.csv")


class Store(BaseModel):
    id: str
    name: str


class StoreSummary(BaseModel):
    store: str
    demand_jobs: int
    total_base_payout: float
    total_final_payout: float
    total_incentives: float
    avg_final_payout: float


class StoreDemand(BaseModel):
    store: str
    demand_jobs: int


router = APIRouter(prefix="/stores", tags=["stores"])


def _load_clean() -> pd.DataFrame:
    if not CLEAN_CSV.exists():
        raise HTTPException(status_code=404, detail="No cleaned data available. Run ETL first.")
    df = pd.read_csv(CLEAN_CSV)
    return df


@router.get("/", response_model=List[Store])
def list_stores():
    df = _load_clean()
    stores = []
    if "store" in df.columns:
        uniq = (
            df["store"].dropna().astype(str).unique().tolist()
        )
        for s in uniq:
            stores.append(Store(id=s, name=s))
    return stores

# Non-trailing-slash to avoid 307
@router.get("", response_model=List[Store])
def list_stores_noslash():
    return list_stores()


@router.get("/{store}/summary", response_model=StoreSummary)
def store_summary(store: str):
    df = _load_clean()
    if "store" not in df.columns:
        raise HTTPException(status_code=404, detail="Store column not found in data")
    df_store = df[df["store"].astype(str) == store]
    demand = int(len(df_store))
    if demand == 0:
        return StoreSummary(
            store=store,
            demand_jobs=0,
            total_base_payout=0.0,
            total_final_payout=0.0,
            total_incentives=0.0,
            avg_final_payout=0.0,
        )
    # prefer final_with_gst_minus_settlement or final_with_gst as total final INR
    df_store = df_store.copy()
    for col in ["base_payout","final_payout","base_pay","incentive_total","final_with_gst","final_with_gst_minus_settlement"]:
        if col in df_store.columns:
            df_store[col] = pd.to_numeric(df_store[col], errors="coerce")

    # Compute totals in INR
    total_final_series = None
    if "final_with_gst_minus_settlement" in df_store.columns:
        total_final_series = df_store["final_with_gst_minus_settlement"]
    elif "final_with_gst" in df_store.columns:
        total_final_series = df_store["final_with_gst"]
    elif "final_payout" in df_store.columns:
        total_final_series = df_store["final_payout"]
    else:
        total_final_series = pd.Series(dtype=float)

    base_series = df_store.get("base_payout", pd.Series(dtype=float))
    if base_series.empty and "base_pay" in df_store.columns:
        base_series = df_store["base_pay"]

    incent_series = df_store.get("incentive_total", pd.Series(dtype=float))
    if incent_series.empty and not total_final_series.empty and not base_series.empty:
        incent_series = total_final_series.fillna(0) - base_series.fillna(0)

    import numpy as np
    def _finite_or_zero(x: float) -> float:
        try:
            return float(x) if np.isfinite(x) else 0.0
        except Exception:
            return 0.0

    total_base = _finite_or_zero(base_series.fillna(0).sum()) if not base_series.empty else 0.0
    total_final = _finite_or_zero(total_final_series.fillna(0).sum()) if not total_final_series.empty else 0.0
    if not incent_series.empty:
        total_incentives = _finite_or_zero(incent_series.fillna(0).sum())
    else:
        total_incentives = max(0.0, total_final - total_base)

    avg_final_val = _finite_or_zero(total_final_series.replace([np.inf, -np.inf], np.nan).dropna().mean()) if not total_final_series.empty else 0.0
    if avg_final_val == 0.0 and not base_series.empty:
        avg_final_val = _finite_or_zero(base_series.replace([np.inf, -np.inf], np.nan).dropna().mean())
    return StoreSummary(
        store=store,
        demand_jobs=demand,
        total_base_payout=round(total_base, 2),
        total_final_payout=round(total_final, 2),
        total_incentives=round(total_incentives, 2),
        avg_final_payout=round(avg_final_val, 2),
    )


@router.get("/demand", response_model=List[StoreDemand])
def demand_by_store():
    df = _load_clean()
    if "store" not in df.columns:
        return []
    counts = df["store"].astype(str).value_counts()
    out: List[StoreDemand] = []
    for store_name, cnt in counts.items():
        out.append(StoreDemand(store=store_name, demand_jobs=int(cnt)))
    return out


