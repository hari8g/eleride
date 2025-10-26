"""
model_train.py
-- Train a simple payout model and save an artifact using joblib
"""
import pandas as pd
from sklearn.linear_model import LinearRegression
import joblib
import logging
import os
import numpy as np

logger = logging.getLogger("model_train")
logging.basicConfig(level=logging.INFO)

MODEL_DIR = "backend/app/models_artifacts"
MODEL_PATH = os.path.join(MODEL_DIR, "payout_model_v1.joblib")

def prepare_features(df: pd.DataFrame):
    df = df.copy()
    df['hour'] = pd.to_datetime(df['created_at'], errors='coerce').dt.hour.fillna(0).astype(int)
    df['zone_id'] = df['zone_id'].fillna(-1)
    df['distance_km'] = df['distance_km'].fillna(df['distance_km'].median() if not df['distance_km'].isna().all() else 1.0)
    X = df[['distance_km','hour','zone_id']].astype(float).fillna(0)
    return X

def train_payout_model(jobs_zoned_csv: str):
    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR, exist_ok=True)
    df = pd.read_csv(jobs_zoned_csv, parse_dates=['created_at'])
    # target: final_payout or base_payout fallback
    df['target'] = df['final_payout'].fillna(df['base_payout']).astype(float)
    df = df.dropna(subset=['target'])
    if df.empty:
        logger.warning("No training rows found; creating dummy model.")
        model = LinearRegression()
        model.intercept_ = 0.0
        model.coef_ = np.array([0.0,0.0,0.0])
        joblib.dump(model, MODEL_PATH)
        return MODEL_PATH
    X = prepare_features(df)
    y = df['target']
    model = LinearRegression()
    model.fit(X, y)
    joblib.dump(model, MODEL_PATH)
    logger.info("Trained payout model saved to %s", MODEL_PATH)
    return MODEL_PATH
