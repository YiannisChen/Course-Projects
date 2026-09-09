import sys
from pathlib import Path

import pandas as pd
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from traffic_hotspots.descriptive_analysis import (
    age_distribution,
    area_summary,
    day_summary,
    hourly_summary,
    kmeans_cluster_profile,
)
from traffic_hotspots.model_evaluation import dbscan_metrics, kmeans_metrics, local_eps_stability, shared_non_noise_ari
from traffic_hotspots.clustering import combine_dbscan_features


def _records() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Area Name": ["Central", "Central", "West", None, "West"],
            "Hour": [17, 17, 19, 2, 8],
            "DayOfWeek": [0, 5, 6, 1, 4],
            "IsWeekend": [0, 1, 1, 0, 0],
            "Victim Age": [24, 0, 35, 101, None],
            "Victim Sex": ["M", "F", None, "M", "F"],
            "Victim Descent": ["H", "W", "H", None, "W"],
            "Cluster": [0, 0, 1, 1, 1],
        }
    )


def test_area_summary_retains_missing_area_values_and_selected_record_share():
    summary = area_summary(_records(), limit=10)

    assert list(summary.columns) == ["Area Name", "Records", "Share"]
    assert summary.loc[0, "Area Name"] == "Central"
    assert summary.loc[0, "Records"] == 2
    assert summary["Records"].sum() == 5
    assert summary["Share"].sum() == 100
    assert "Unknown / missing" in set(summary["Area Name"])


def test_hour_and_day_summaries_cover_complete_clock_and_week():
    hourly = hourly_summary(_records())
    days = day_summary(_records())

    assert list(hourly["Hour"]) == list(range(24))
    assert hourly.loc[hourly["Hour"] == 17, "Records"].item() == 2
    assert hourly["Share"].sum() == 100
    assert list(days["Day"]) == ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    assert days["Records"].sum() == 5
    assert days["Share"].sum() == 100


def test_age_distribution_uses_only_original_plausible_ages():
    distribution, coverage = age_distribution(_records())

    assert coverage == {"valid_age_records": 2, "missing_or_invalid_records": 3, "valid_age_share": 40.0, "median_age": 29.5}
    assert distribution.loc[distribution["Age Group"] == "18–24", "Records"].item() == 1
    assert distribution.loc[distribution["Age Group"] == "35–44", "Records"].item() == 1
    assert distribution["Records"].sum() == 2


def test_kmeans_profile_reports_missing_age_share_without_imputing_age():
    profile = kmeans_cluster_profile(_records())

    cluster_one = profile.set_index("Cluster").loc[1]
    assert cluster_one["Records"] == 3
    assert cluster_one["Age Missing Share"] == 33.3
    assert cluster_one["Median Valid Age"] == 35.0
    assert cluster_one["Weekend Share"] == 33.3


def test_dbscan_metrics_exclude_noise_for_internal_scores_and_report_coverage():
    features = np.array([[0.0], [0.1], [5.0], [5.1], [10.0]])
    labels = np.array([0, 0, 1, 1, -1])

    metrics = dbscan_metrics(features, labels)

    assert metrics["clusters"] == 2
    assert metrics["noise_percent"] == 20.0
    assert metrics["coverage_percent"] == 80.0
    assert metrics["largest_cluster_share"] == 50.0
    assert metrics["silhouette"] is not None
    assert metrics["davies_bouldin"] is not None


def test_shared_non_noise_ari_uses_only_cells_clustered_in_both_runs():
    first = np.array([0, 0, 1, 1, -1])
    second = np.array([3, 3, 4, -1, 8])

    assert shared_non_noise_ari(first, second) == 1.0


def test_local_eps_stability_tolerates_floating_point_eps_values():
    labels = {
        (0.2, 5): np.array([0, 0, 1, 1]),
        (0.225, 5): np.array([3, 3, 4, 4]),
        (0.25, 5): np.array([2, 2, 9, 9]),
    }

    stability = local_eps_stability(labels, [0.2, 0.225, 0.25])

    assert stability[(0.225, 5)] == 1.0


def test_kmeans_metrics_reports_all_internal_scores_for_multiple_groups():
    features = np.array([[0.0], [0.1], [5.0], [5.1]])
    labels = np.array([0, 0, 1, 1])

    metrics = kmeans_metrics(features, labels, inertia=0.02)

    assert metrics["inertia"] == 0.02
    assert metrics["silhouette"] is not None
    assert metrics["calinski_harabasz"] is not None
    assert metrics["davies_bouldin"] is not None


def test_dbscan_evaluation_uses_the_same_combined_distance_space_as_clustering():
    features = np.array([[1.0, 0.0], [2.0, 1.0]])
    coordinates = np.array([[34.0, -118.2], [34.1, -118.3]])

    combined = combine_dbscan_features(features, coordinates)

    assert combined.shape == (2, 4)
    assert np.allclose(combined[:, :2].mean(axis=0), [0.0, 0.0])
    assert np.allclose(combined[:, 2:].std(axis=0), [0.5, 0.5])
