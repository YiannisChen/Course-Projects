import pandas as pd

from traffic_hotspots.visualization import create_cluster_map, create_heatmap


def _grid_features():
    return pd.DataFrame(
        {
            "grid_lat": [34.0, 34.01],
            "grid_lon": [-118.2, -118.21],
            "accident_count": [3, 4],
            "avg_age_group": [1.0, 2.0],
            "Cluster": [0, -1],
        }
    )


def test_collision_intensity_map_uses_supported_maplibre_trace():
    figure = create_heatmap(_grid_features())

    assert figure.data[0].type == "scattermap"
    assert figure.layout.map.style == "open-street-map"


def test_cluster_map_uses_supported_maplibre_trace():
    figure = create_cluster_map(_grid_features())

    assert {trace.type for trace in figure.data} == {"scattermap"}
    assert figure.layout.map.style == "open-street-map"
