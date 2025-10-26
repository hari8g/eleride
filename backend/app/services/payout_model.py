from __future__ import annotations

from pathlib import Path
from typing import Optional
from joblib import load
import os
from math import radians, cos, sin, asin, sqrt

DEFAULT_MODEL_PATH = os.path.join("backend", "app", "models_artifacts", "payout_model_v1.joblib")


class PayoutModelService:
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path
        self._model = None
        if model_path and Path(model_path).exists():
            self._model = load(model_path)

    def estimate_price(
        self,
        *,
        energy_kwh: float,
        pickup_lat: float,
        pickup_lng: float,
        dropoff_lat: float,
        dropoff_lng: float,
    ) -> float:
        if self._model is None:
            return round(1.0 + 0.3 * energy_kwh, 2)
        # Determine expected feature dimension
        n_features = getattr(self._model, 'n_features_in_', 1)
        if n_features == 1:
            features = [energy_kwh]
        else:
            # Compute distance_km via haversine
            def haversine(lat1, lon1, lat2, lon2):
                lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
                c = 2 * asin(sqrt(a))
                return 6371 * c
            distance_km = haversine(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)
            # Use current hour and default zone_id -1 when not available
            from datetime import datetime, timezone
            hour = datetime.now(tz=timezone.utc).hour
            zone_id = -1.0
            features = [float(distance_km), float(hour), float(zone_id)]
        y = self._model.predict([features])
        return float(round(y[0], 2))


_global_service: Optional[PayoutModelService] = None


def get_payout_service() -> PayoutModelService:
    global _global_service
    if _global_service is None:
        model_path = DEFAULT_MODEL_PATH if Path(DEFAULT_MODEL_PATH).exists() else None
        _global_service = PayoutModelService(model_path=model_path)
    return _global_service


