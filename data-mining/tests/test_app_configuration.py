from pathlib import Path


APP = (Path(__file__).resolve().parents[1] / "app.py").read_text()
CLI = (Path(__file__).resolve().parents[1] / "run_analysis.py").read_text()


def test_dbscan_control_uses_a_short_label_and_separate_distance_caption():
    assert '"DBSCAN Epsilon"' in APP
    assert 'Standardized grid-feature distance' in APP
    assert 'DBSCAN Epsilon (standardized grid-feature distance)' not in APP
    assert '0.1, 1.2, 0.25' in APP
    assert '"Minimum Samples", 1, 50, 5' in APP


def test_compare_mode_bounds_kmeans_clusters_to_available_grid_cells():
    assert 'min(20, len(grid_data))' in APP


def test_dbscan_uses_interpretable_grid_pattern_features():
    assert 'features=["accident_count", "weekend_ratio"]' in APP
    assert "'avg_age_group', 'weekend_ratio', 'peak_hour'" not in APP


def test_cli_uses_the_same_dbscan_grid_features_as_the_interface():
    assert 'feature_columns = ["accident_count", "weekend_ratio"]' in CLI


def test_interface_uses_the_shared_fixed_grid_origin():
    assert "calculate_grid_features(filtered, size=grid_size)" in APP
    assert "lat_min=lat_min, lon_min=lon_min" not in APP


def test_interface_requires_an_uploaded_file_and_has_no_local_dataset_fallback():
    assert 'LOCAL_DATASET_ENV' not in APP
    assert 'os.environ.get(' not in APP
    assert 'preprocess_data(uploaded_file)' in APP
    assert 'Upload a compatible LA traffic-collision CSV to begin the analysis.' in APP


def test_interface_includes_descriptive_patterns_and_model_guidance_views():
    assert 'Overview / Descriptive Patterns' in APP
    assert 'Top 10 Areas by Collision Records' in APP
    assert 'DBSCAN parameter evidence' in APP
    assert 'K-Means model evidence' in APP
