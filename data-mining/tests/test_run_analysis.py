from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from run_analysis import analyze_file, validate_required_columns
from traffic_hotspots.clustering import perform_clustering, perform_kmeans
from traffic_hotspots.data_preparation import (
    clean_coordinates,
    extract_temporal_features,
    format_time_occurred,
    preprocess_data,
)
from traffic_hotspots.feature_engineering import (
    calculate_grid_features,
    create_feature_matrix,
    prepare_individual_features,
)

FIXTURE = PROJECT_ROOT / "examples" / "sample_collisions.csv"

VALID_FIXTURE_IDS = {1, 2, 3, 4, 5, 7, 8, 13}


def test_format_time_occurred_accepts_common_csv_values():
    assert format_time_occurred(800) == "0800"
    assert format_time_occurred(800.0) == "0800"
    assert format_time_occurred("815") == "0815"
    assert format_time_occurred("1730") == "1730"
    assert format_time_occurred(0) == "0000"


def test_format_time_occurred_rejects_invalid_values():
    assert format_time_occurred(None) is None
    assert format_time_occurred(float("nan")) is None
    assert format_time_occurred("") is None
    assert format_time_occurred(2400) is None
    assert format_time_occurred(2360) is None
    assert format_time_occurred("noon") is None


def test_clean_coordinates_parses_lat_lon_and_filters_invalid_values():
    frame = pd.DataFrame(
        {
            "Location": [
                "(34.0500, -118.2500)",
                "( 34.05 , -118.25 )",
                "invalid",
                None,
                "(40.7128, -74.0060)",
                "(-118.2500, 34.0500)",
                "(34.9, -118.25)",
            ]
        }
    )
    cleaned = clean_coordinates(frame)
    assert len(cleaned) == 2
    assert cleaned.iloc[0]["Latitude"] == pytest.approx(34.05)
    assert cleaned.iloc[0]["Longitude"] == pytest.approx(-118.25)
    assert cleaned.iloc[1]["Latitude"] == pytest.approx(34.05)
    assert (cleaned["Latitude"].between(33.7, 34.3)).all()
    assert (cleaned["Longitude"].between(-118.7, -118.1)).all()


def test_extract_temporal_features_drops_malformed_dates_and_times_without_crashing():
    frame = pd.DataFrame(
        {
            "Date Occurred": ["05/01/2024", "13/40/2024", "05/04/2024", "05/06/2024"],
            "Time Occurred": [800.0, 1000.0, 2300.0, np.nan],
        }
    )
    parsed = extract_temporal_features(frame)
    assert list(parsed["Hour"]) == [8, 23]
    assert list(parsed["IsWeekend"]) == [0, 1]
    assert parsed.iloc[0]["Date Occurred"].day == 1
    assert parsed.iloc[0]["Date Occurred"].month == 5


def test_preprocess_data_filters_malformed_rows_and_builds_age_groups():
    prepared = preprocess_data(FIXTURE)
    assert set(prepared["DR Number"]) == VALID_FIXTURE_IDS
    assert "AgeGroup" in prepared.columns
    assert "AgeGroupNum" in prepared.columns
    assert "Severity" not in prepared.columns
    assert "SeverityNum" not in prepared.columns
    by_id = prepared.set_index("DR Number")
    assert by_id.loc[1, "AgeGroup"] == "Young"
    assert by_id.loc[2, "AgeGroup"] == "Adult"
    assert by_id.loc[7, "AgeGroup"] == "Child"
    assert by_id.loc[8, "AgeGroup"] == "Elderly"
    assert by_id.loc[7, "IsWeekend"] == 1
    assert by_id.loc[1, "Hour"] == 8
    assert by_id.loc[3, "Hour"] == 17


def test_grid_features_aggregate_counts_and_age_groups():
    prepared = preprocess_data(FIXTURE)
    grid = calculate_grid_features(prepared)
    assert len(grid) >= 2
    assert grid["accident_count"].sum() == len(prepared)
    assert set(["accident_count", "avg_age_group", "weekend_ratio", "peak_hour", "grid_lat", "grid_lon"]) <= set(grid.columns)
    assert "avg_severity" not in grid.columns
    assert (grid["accident_count"] >= 1).all()
    assert grid["weekend_ratio"].between(0, 1).all()
    assert grid["Grid"].str.contains("_").all()


def test_kmeans_is_deterministic_and_dbscan_returns_labels():
    prepared = preprocess_data(FIXTURE)
    grid = calculate_grid_features(prepared)
    features, names = create_feature_matrix(
        grid, ["accident_count", "avg_age_group", "weekend_ratio", "peak_hour"]
    )
    assert list(names) == ["accident_count", "avg_age_group", "weekend_ratio", "peak_hour"]
    assert features.shape == (len(grid), 4)
    first, _ = perform_kmeans(features, n_clusters=2)
    second, model = perform_kmeans(features, n_clusters=2)
    assert list(first) == list(second)
    assert len(set(first)) == 2
    assert model.n_clusters == 2
    dbscan_labels, dbscan = perform_clustering(
        features, grid[["grid_lat", "grid_lon"]].to_numpy(), eps=3.0, min_samples=1
    )
    assert len(dbscan_labels) == len(grid)
    assert set(dbscan.labels_) == set(dbscan_labels)


def test_individual_features_encode_circular_time_and_missing_age():
    prepared = preprocess_data(FIXTURE)
    prepared.loc[prepared.index[0], "Victim Age"] = np.nan

    features, names = prepare_individual_features(prepared, include_age_missing=True)

    assert {"HourSin", "HourCos", "WeekdaySin", "WeekdayCos", "AgeMissing"} <= set(names)
    assert "Hour" not in names
    assert "DayOfWeek" not in names
    assert "Premise Description" not in " ".join(names)
    assert np.isfinite(features).all()


def test_individual_features_can_exclude_missing_age_indicator_from_distance_features():
    prepared = preprocess_data(FIXTURE)
    prepared.loc[prepared.index[0], "Victim Age"] = np.nan

    _, names = prepare_individual_features(prepared, include_age_missing=False)

    assert "AgeMissing" not in names


def test_validate_required_columns_reports_missing_names():
    with pytest.raises(ValueError, match="Victim Age"):
        validate_required_columns(pd.DataFrame({"Location": []}))


def test_preprocess_data_reports_missing_required_column(tmp_path):
    path = tmp_path / "missing.csv"
    pd.DataFrame(
        {
            "DR Number": [1],
            "Date Occurred": ["05/01/2024"],
            "Time Occurred": [800],
            "Victim Age": [30],
        }
    ).to_csv(path, index=False)
    with pytest.raises(ValueError, match="Location"):
        preprocess_data(path)


def test_cli_analysis_returns_summary_and_runs_from_shell():
    summary = analyze_file(FIXTURE, algorithm="kmeans", n_clusters=2)
    assert summary["input_rows"] == 13
    assert summary["processed_rows"] == 8
    assert summary["cluster_count"] == 2
    assert summary["grid_cells"] >= 2
    dbscan_summary = analyze_file(FIXTURE, algorithm="dbscan")
    assert dbscan_summary["processed_rows"] == 8
    assert dbscan_summary["cluster_count"] >= 1
    completed = subprocess.run(
        [sys.executable, "run_analysis.py", str(FIXTURE)],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "Processed rows: 8" in completed.stdout
    assert "Clusters: 2" in completed.stdout
