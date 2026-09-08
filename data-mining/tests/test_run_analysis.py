from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from run_analysis import analyze_file, validate_required_columns
from traffic_hotspots.data_preparation import preprocess_data
from traffic_hotspots.feature_engineering import calculate_grid_features, create_feature_matrix
from traffic_hotspots.clustering import perform_clustering, perform_kmeans

FIXTURE = PROJECT_ROOT / "examples" / "sample_collisions.csv"

def test_preprocessing_filters_invalid_coordinates_and_extracts_time_features():
    prepared = preprocess_data(FIXTURE)
    assert len(prepared) == 5
    assert {"Latitude", "Longitude", "Hour", "DayOfWeek", "IsWeekend", "SeverityNum"} <= set(prepared.columns)

def test_grid_features_and_existing_clusterers_run():
    prepared = preprocess_data(FIXTURE)
    grid = calculate_grid_features(prepared)
    features, _ = create_feature_matrix(grid, ["accident_count", "avg_severity", "weekend_ratio", "peak_hour"])
    labels, _ = perform_clustering(features, grid[["grid_lat", "grid_lon"]].to_numpy(), eps=3.0, min_samples=1)
    kmeans_labels, _ = perform_kmeans(features, n_clusters=2)
    assert len(labels) == len(grid)
    assert len(kmeans_labels) == len(grid)

def test_validate_required_columns_reports_missing_names():
    with pytest.raises(ValueError, match="Victim Age"):
        validate_required_columns(pd.DataFrame({"Location": []}))

def test_cli_analysis_returns_summary_and_runs_from_shell():
    summary = analyze_file(FIXTURE, algorithm="kmeans", n_clusters=2)
    assert summary["input_rows"] == 6
    assert summary["processed_rows"] == 5
    assert summary["cluster_count"] == 2
    completed = subprocess.run([sys.executable, "run_analysis.py", str(FIXTURE)], cwd=PROJECT_ROOT, text=True, capture_output=True, check=True)
    assert "Processed rows: 5" in completed.stdout
