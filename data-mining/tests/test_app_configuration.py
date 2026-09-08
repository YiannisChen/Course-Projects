from pathlib import Path


APP = (Path(__file__).resolve().parents[1] / "app.py").read_text()
CLI = (Path(__file__).resolve().parents[1] / "run_analysis.py").read_text()


def test_dbscan_control_describes_standardized_grid_feature_distance():
    assert 'DBSCAN Epsilon (standardized grid-feature distance)' in APP
    assert '0.1, 1.2, 0.25' in APP
    assert '"Minimum Samples", 1, 50, 5' in APP


def test_compare_mode_bounds_kmeans_clusters_to_available_grid_cells():
    assert 'max_k = min(20, len(grid_features))' in APP


def test_dbscan_uses_interpretable_grid_pattern_features():
    assert "features=['accident_count', 'weekend_ratio']" in APP
    assert "'avg_age_group', 'weekend_ratio', 'peak_hour'" not in APP


def test_cli_uses_the_same_dbscan_grid_features_as_the_interface():
    assert 'feature_columns = ["accident_count", "weekend_ratio"]' in CLI


def test_interface_uses_the_shared_fixed_grid_origin():
    assert "calculate_grid_features(df_filtered, size=grid_size)" in APP
    assert "lat_min=lat_min, lon_min=lon_min" not in APP


def test_interface_can_use_an_explicit_local_development_dataset_path():
    assert 'LOCAL_DATASET_ENV = "LA_TRAFFIC_CSV"' in APP
    assert 'source = uploaded_file or os.environ.get(LOCAL_DATASET_ENV)' in APP
