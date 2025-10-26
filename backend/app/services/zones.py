"""
zones.py
-- KMeans clustering of pickup coordinates to produce zones and assign zone_id
"""
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
import logging

logger = logging.getLogger("zones")
logging.basicConfig(level=logging.INFO)

def cluster_jobs(clean_csv_path: str, k: int = 12, jobs_zoned_out: str = "/data/jobs_zoned.csv", zones_out: str = "/data/zones.csv"):
    df = pd.read_csv(clean_csv_path)
    # filter rows that have pickup coords
    coords = df[['pickup_lat','pickup_lng']].dropna()
    if coords.empty:
        logger.warning("No pickup coordinates found for clustering.")
        df['zone_id'] = np.nan
        df.to_csv(jobs_zoned_out, index=False)
        pd.DataFrame([], columns=['zone_id','centroid_lat','centroid_lng']).to_csv(zones_out, index=False)
        return zones_out, jobs_zoned_out
    X = coords.values
    k = min(k, len(X))
    km = KMeans(n_clusters=k, random_state=42, n_init='auto')
    labels = km.fit_predict(X)
    zone_series = pd.Series(index=coords.index, data=labels)
    df['zone_id'] = np.nan
    df.loc[coords.index, 'zone_id'] = zone_series.values
    centroids = km.cluster_centers_
    centroid_df = pd.DataFrame(centroids, columns=['centroid_lat','centroid_lng'])
    centroid_df['zone_id'] = centroid_df.index
    centroid_df.to_csv(zones_out, index=False)
    df.to_csv(jobs_zoned_out, index=False)
    logger.info("Created %d zones, wrote %s and %s", k, zones_out, jobs_zoned_out)
    return zones_out, jobs_zoned_out

def assign_zone_to_jobs(df: pd.DataFrame, centroid_df: pd.DataFrame):
    # simple nearest-centroid assignment (if needed)
    from sklearn.metrics import pairwise_distances_argmin_min
    centroids = centroid_df[['centroid_lat','centroid_lng']].values
    coords = df[['pickup_lat','pickup_lng']].fillna(0).values
    idx, dist = pairwise_distances_argmin_min(coords, centroids)
    df['zone_id'] = idx
    return df
