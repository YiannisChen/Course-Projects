import pandas as pd
import pytest

from traffic_collision_analysis.visualization import create_cluster_map, create_heatmap, create_record_cluster_map


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


def _record_features():
    return pd.DataFrame(
        {
            "Latitude": [34.00, 34.02, 34.04, 34.06],
            "Longitude": [-118.20, -118.22, -118.24, -118.26],
            "Cluster": [0, 1, 0, 1],
            "Victim Age": [20, 30, 40, 50],
            "Hour": [8, 12, 17, 22],
            "DayOfWeek": [0, 1, 2, 3],
            "Victim Sex": ["M", "F", "M", "F"],
            "Victim Descent": ["A", "B", "A", "B"],
        }
    )


def test_collision_intensity_map_uses_supported_maplibre_trace():
    figure = create_heatmap(_grid_features())

    assert figure.data[0].type == "scattermap"
    assert figure.layout.map.style == "open-street-map"
    assert len(figure.data) > 0


def test_cluster_map_uses_supported_maplibre_trace():
    figure = create_cluster_map(_grid_features())

    assert {trace.type for trace in figure.data} == {"scattermap"}
    assert figure.layout.map.style == "open-street-map"
    assert len(figure.data) > 0


@pytest.mark.parametrize("builder", [create_heatmap, create_cluster_map])
def test_map_builders_reject_empty_grid_data(builder):
    with pytest.raises(ValueError, match="at least one grid cell"):
        builder(_grid_features().iloc[0:0])


def test_record_cluster_map_uses_a_la_center_and_discrete_maplibre_traces():
    figure = create_record_cluster_map(_record_features())

    assert figure.layout.map.center.lat == pytest.approx(34.03)
    assert figure.layout.map.center.lon == pytest.approx(-118.23)
    assert {trace.type for trace in figure.data} == {"scattermap"}
    assert {trace.name for trace in figure.data} == {"Cluster 0", "Cluster 1"}
    assert all(trace.marker.showscale is False for trace in figure.data)
