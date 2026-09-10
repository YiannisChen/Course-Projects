"""
Clustering module for traffic collision pattern analysis.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.preprocessing import StandardScaler
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def combine_dbscan_features(X, coords, spatial_weight=0.5):
    """Build the standardized feature space used by DBSCAN and its evaluation."""
    feature_scaler = StandardScaler()
    coordinate_scaler = StandardScaler()
    return np.hstack([
        feature_scaler.fit_transform(X),
        coordinate_scaler.fit_transform(coords) * spatial_weight,
    ])


# Run DBSCAN clustering on features and coordinates
def perform_clustering(X, coords, eps=0.5, min_samples=5, spatial_weight=0.5):
    try:
        X_combined = combine_dbscan_features(X, coords, spatial_weight)
        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        labels = dbscan.fit_predict(X_combined)
        logger.info(f"Clustering completed with {len(np.unique(labels))} clusters")
        return labels, dbscan
    except Exception as e:
        logger.error(f"Error performing clustering: {str(e)}")
        raise

# Run K-Means clustering
def perform_kmeans(X, n_clusters=8):
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    labels = kmeans.fit_predict(X)
    return labels, kmeans
