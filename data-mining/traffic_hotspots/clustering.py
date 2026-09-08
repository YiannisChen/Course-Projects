"""
Clustering module for traffic accident hotspots.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans, AgglomerativeClustering
from sklearn.preprocessing import StandardScaler
from typing import Tuple, Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Run DBSCAN clustering on features and coordinates
def perform_clustering(X, coords, eps=0.5, min_samples=5, spatial_weight=0.5):
    try:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        coords_scaled = scaler.fit_transform(coords)
        X_combined = np.hstack([
            X_scaled,
            coords_scaled * spatial_weight
        ])
        dbscan = DBSCAN(eps=eps, min_samples=min_samples)
        labels = dbscan.fit_predict(X_combined)
        logger.info(f"Clustering completed with {len(np.unique(labels))} clusters")
        return labels, dbscan
    except Exception as e:
        logger.error(f"Error performing clustering: {str(e)}")
        raise

# Summarize cluster statistics
def analyze_clusters(grid_features, labels):
    try:
        grid_features['cluster'] = labels
        cluster_stats = grid_features.groupby('cluster').agg({
            'accident_count': ['count', 'mean', 'sum'],
            'weekend_ratio': 'mean',
            'peak_hour': 'mean',
            'avg_victim_age': 'mean',
            'most_common_severity': lambda x: x.value_counts().index[0]
        }).reset_index()
        cluster_stats.columns = [
            'cluster',
            'grid_count',
            'avg_accidents_per_grid',
            'total_accidents',
            'avg_weekend_ratio',
            'avg_peak_hour',
            'avg_victim_age',
            'most_common_severity'
        ]
        logger.info("Cluster analysis completed successfully")
        return cluster_stats
    except Exception as e:
        logger.error(f"Error analyzing clusters: {str(e)}")
        raise

# Generate human-readable cluster descriptions
def get_cluster_characteristics(cluster_stats):
    try:
        characteristics = {}
        for _, row in cluster_stats.iterrows():
            cluster_id = row['cluster']
            if cluster_id == -1:
                continue
            if row['avg_weekend_ratio'] > 0.5 and row['avg_peak_hour'] > 20:
                cluster_type = "Nightlife Hotspot"
            elif row['avg_weekend_ratio'] < 0.3 and row['avg_peak_hour'] in [8, 17]:
                cluster_type = "Commuter Hotspot"
            elif row['most_common_severity'] == 'Child':
                cluster_type = "School Zone Hotspot"
            elif row['most_common_severity'] == 'Elderly':
                cluster_type = "Senior Zone Hotspot"
            else:
                cluster_type = "General Hotspot"
            characteristics[cluster_id] = {
                'type': cluster_type,
                'description': (
                    f"{cluster_type} with {row['total_accidents']} total accidents, "
                    f"averaging {row['avg_accidents_per_grid']:.1f} accidents per grid cell. "
                    f"Peak hour: {int(row['avg_peak_hour'])}:00, "
                    f"Weekend ratio: {row['avg_weekend_ratio']:.2f}"
                )
            }
        logger.info("Cluster characteristics generated successfully")
        return characteristics
    except Exception as e:
        logger.error(f"Error generating cluster characteristics: {str(e)}")
        raise

# Run K-Means clustering
def perform_kmeans(X, n_clusters=8):
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    labels = kmeans.fit_predict(X)
    return labels, kmeans

# Run Agglomerative clustering
def perform_agglomerative(X, n_clusters=8):
    agg = AgglomerativeClustering(n_clusters=n_clusters)
    labels = agg.fit_predict(X)
    return labels, agg 