"""Run the existing traffic-hotspot workflow against a local CSV file."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from traffic_hotspots.clustering import perform_clustering, perform_kmeans
from traffic_hotspots.data_preparation import preprocess_data
from traffic_hotspots.feature_engineering import calculate_grid_features, create_feature_matrix

REQUIRED_COLUMNS = {
    "DR Number", "Date Occurred", "Time Occurred", "Location", "Victim Age",
    "Victim Sex", "Victim Descent", "Premise Description",
}


def validate_required_columns(dataframe: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS - set(dataframe.columns))
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def analyze_file(path: str | Path, algorithm: str = "kmeans", n_clusters: int = 2) -> dict[str, int]:
    source = Path(path)
    raw = pd.read_csv(source)
    validate_required_columns(raw)
    prepared = preprocess_data(source)
    if prepared.empty:
        raise ValueError("No valid rows remain after preprocessing")
    grid_features = calculate_grid_features(prepared)
    if grid_features.empty:
        raise ValueError("No grid features could be calculated")
    feature_columns = ["accident_count", "weekend_ratio"]
    features, _ = create_feature_matrix(grid_features, feature_columns)
    if algorithm == "kmeans":
        if not 1 < n_clusters <= len(grid_features):
            raise ValueError(f"n_clusters must be between 2 and {len(grid_features)}")
        labels, _ = perform_kmeans(features, n_clusters=n_clusters)
    elif algorithm == "dbscan":
        labels, _ = perform_clustering(features, grid_features[["grid_lat", "grid_lon"]].to_numpy(), eps=3.0, min_samples=1)
    else:
        raise ValueError("algorithm must be 'kmeans' or 'dbscan'")
    return {
        "input_rows": len(raw),
        "processed_rows": len(prepared),
        "grid_cells": len(grid_features),
        "cluster_count": len(set(labels)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run traffic hotspot clustering on a CSV file.")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--algorithm", choices=("kmeans", "dbscan"), default="kmeans")
    parser.add_argument("--n-clusters", type=int, default=2)
    arguments = parser.parse_args()
    try:
        summary = analyze_file(arguments.csv_path, arguments.algorithm, arguments.n_clusters)
    except (OSError, ValueError, KeyError, pd.errors.ParserError) as error:
        parser.error(str(error))
    print(f"Input rows: {summary['input_rows']}")
    print(f"Processed rows: {summary['processed_rows']}")
    print(f"Grid cells: {summary['grid_cells']}")
    print(f"Clusters: {summary['cluster_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
