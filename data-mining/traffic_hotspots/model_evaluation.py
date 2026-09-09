"""Small, deterministic clustering-evaluation helpers for the Streamlit app."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, calinski_harabasz_score, davies_bouldin_score, silhouette_score

from traffic_hotspots.clustering import combine_dbscan_features, perform_clustering


def _internal_scores(features: np.ndarray, labels: np.ndarray) -> tuple[float | None, float | None, float | None]:
    unique = np.unique(labels)
    if len(unique) < 2 or len(features) <= len(unique):
        return None, None, None
    return (
        round(float(silhouette_score(features, labels)), 3),
        round(float(calinski_harabasz_score(features, labels)), 1),
        round(float(davies_bouldin_score(features, labels)), 3),
    )


def dbscan_metrics(features: np.ndarray, labels: np.ndarray) -> dict[str, float | int | None]:
    """Report coverage/balance plus internal scores on non-noise cells only."""
    labels = np.asarray(labels)
    non_noise = labels != -1
    clustered_labels = labels[non_noise]
    clustered_features = features[non_noise]
    cluster_sizes = pd.Series(clustered_labels).value_counts() if len(clustered_labels) else pd.Series(dtype=int)
    silhouette, _, davies_bouldin = _internal_scores(clustered_features, clustered_labels)
    largest_share = 100 * cluster_sizes.max() / len(clustered_labels) if len(clustered_labels) else 0.0
    return {
        "clusters": int(len(cluster_sizes)),
        "noise_percent": round(100 * (1 - non_noise.mean()), 1),
        "coverage_percent": round(100 * non_noise.mean(), 1),
        "largest_cluster_share": round(float(largest_share), 1),
        "median_cluster_size": float(cluster_sizes.median()) if len(cluster_sizes) else None,
        "silhouette": silhouette,
        "davies_bouldin": davies_bouldin,
    }


def shared_non_noise_ari(first: np.ndarray, second: np.ndarray) -> float | None:
    """ARI on the cells marked non-noise by both DBSCAN solutions."""
    first = np.asarray(first)
    second = np.asarray(second)
    mask = (first != -1) & (second != -1)
    if mask.sum() < 2:
        return None
    return round(float(adjusted_rand_score(first[mask], second[mask])), 3)


def local_eps_stability(
    labels_by_setting: dict[tuple[float, int], np.ndarray], eps_values: Iterable[float]
) -> dict[tuple[float, int], float | None]:
    """Mean shared-non-noise ARI with immediately adjacent eps values per min_samples."""
    eps_values = list(eps_values)
    stability: dict[tuple[float, int], float | None] = {}
    for setting, labels in labels_by_setting.items():
        epsilon, min_samples = setting
        neighbors = [
            other_labels
            for (other_epsilon, other_min_samples), other_labels in labels_by_setting.items()
            if other_min_samples == min_samples
            and np.isclose(abs(other_epsilon - epsilon), 0.025, atol=1e-9)
        ]
        scores = [score for neighbor in neighbors if (score := shared_non_noise_ari(labels, neighbor)) is not None]
        stability[setting] = round(sum(scores) / len(scores), 3) if scores else None
    return stability


def evaluate_dbscan_grid(
    features: np.ndarray,
    coordinates: np.ndarray,
    eps_values: Iterable[float],
    min_samples_values: Iterable[int],
) -> tuple[pd.DataFrame, dict[tuple[float, int], np.ndarray]]:
    """Evaluate a compact parameter matrix on the same grid-feature space as the UI."""
    evaluation_space = combine_dbscan_features(features, coordinates)
    rows: list[dict[str, float | int | None]] = []
    labels_by_setting: dict[tuple[float, int], np.ndarray] = {}
    for min_samples in min_samples_values:
        for epsilon in eps_values:
            labels, _ = perform_clustering(features, coordinates, epsilon, min_samples)
            labels_by_setting[(float(epsilon), int(min_samples))] = labels
            rows.append({"eps": float(epsilon), "min_samples": int(min_samples), **dbscan_metrics(evaluation_space, labels)})
    return pd.DataFrame(rows), labels_by_setting


def kmeans_metrics(features: np.ndarray, labels: np.ndarray, inertia: float) -> dict[str, float | None]:
    silhouette, calinski_harabasz, davies_bouldin = _internal_scores(features, labels)
    return {
        "inertia": round(float(inertia), 3),
        "silhouette": silhouette,
        "calinski_harabasz": calinski_harabasz,
        "davies_bouldin": davies_bouldin,
    }


def evaluate_kmeans_sample(features: np.ndarray, cluster_counts: Iterable[int]) -> pd.DataFrame:
    """Evaluate K values on one deterministic feature sample supplied by the caller."""
    rows: list[dict[str, float | int | None]] = []
    for count in cluster_counts:
        model = KMeans(n_clusters=count, random_state=42, n_init=10)
        labels = model.fit_predict(features)
        rows.append({"K": int(count), **kmeans_metrics(features, labels, model.inertia_)})
    return pd.DataFrame(rows)
