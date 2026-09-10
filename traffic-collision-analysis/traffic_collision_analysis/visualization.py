"""
Visualization module for traffic collision pattern analysis.
"""

import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a collision-intensity map compatible with current MapLibre traces.
def create_heatmap(grid_features: pd.DataFrame) -> go.Figure:
    if grid_features.empty:
        raise ValueError("Collision intensity maps require at least one grid cell.")

    marker_size = 6 + 18 * np.sqrt(
        grid_features['accident_count'] / grid_features['accident_count'].max()
    )
    fig = go.Figure(go.Scattermap(
        lat=grid_features['grid_lat'],
        lon=grid_features['grid_lon'],
        mode='markers',
        marker=dict(
            size=marker_size,
            color=grid_features['accident_count'],
            colorscale='Hot',
            opacity=0.7,
            showscale=True,
            colorbar=dict(title='Collisions'),
        ),
        text=grid_features['accident_count'].map(lambda count: f'Collisions: {count}'),
        hoverinfo='text',
    ))
    fig.update_layout(
        map=dict(
            style="open-street-map",
            center=dict(
                lat=grid_features['grid_lat'].mean(),
                lon=grid_features['grid_lon'].mean(),
            ),
            zoom=11,
        ),
        margin={"r":0,"t":44,"l":0,"b":0},
        height=600,
        title="Collision Intensity Map",
    )
    return fig

# Show clusters on a map
def create_cluster_map(grid_features: pd.DataFrame) -> go.Figure:
    if grid_features.empty:
        raise ValueError("Cluster maps require at least one grid cell.")

    unique_clusters = grid_features['Cluster'].unique()
    colors = px.colors.qualitative.Set1 + px.colors.qualitative.Pastel
    non_noise = [cluster for cluster in sorted(unique_clusters) if cluster != -1]
    color_map = {-1: "#9CA3AF"}
    color_map.update({cluster: colors[i % len(colors)] for i, cluster in enumerate(non_noise)})
    fig = go.Figure()
    for cluster in unique_clusters:
        cluster_data = grid_features[grid_features['Cluster'] == cluster]
        fig.add_trace(go.Scattermap(
            lat=cluster_data['grid_lat'],
            lon=cluster_data['grid_lon'],
            mode='markers',
            marker=dict(
                size=8 if cluster == -1 else 10,
                color=color_map[cluster],
                opacity=0.30 if cluster == -1 else 0.72,
            ),
            name=f'Cluster {cluster}',
            text=cluster_data.apply(
                lambda row: f"Accidents: {row['accident_count']}<br>Age group: {row['avg_age_group']:.2f}",
                axis=1
            ),
            hoverinfo='text'
        ))
    fig.update_layout(
        map=dict(
            style="open-street-map",
            center=dict(
                lat=grid_features['grid_lat'].mean(),
                lon=grid_features['grid_lon'].mean(),
            ),
            zoom=11,
        ),
        margin={"r":0,"t":44,"l":0,"b":0},
        height=600,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        title="Grid Pattern Clusters"
    )
    return fig


def create_record_cluster_map(records: pd.DataFrame) -> go.Figure:
    """Render record-level K-Means labels as discrete MapLibre traces."""
    if records.empty:
        raise ValueError("Record pattern maps require at least one collision record.")

    colors = px.colors.qualitative.Set2 + px.colors.qualitative.Dark24
    figure = go.Figure()
    hover_columns = [
        column
        for column in ["Victim Age", "Hour", "DayOfWeek", "Victim Sex", "Victim Descent"]
        if column in records.columns
    ]
    for index, cluster in enumerate(sorted(records["Cluster"].unique())):
        cluster_records = records[records["Cluster"] == cluster]
        hover_text = cluster_records.apply(
            lambda row: "<br>".join(f"{column}: {row[column]}" for column in hover_columns),
            axis=1,
        )
        figure.add_trace(
            go.Scattermap(
                lat=cluster_records["Latitude"],
                lon=cluster_records["Longitude"],
                mode="markers",
                name=f"Cluster {cluster}",
                marker={"size": 7, "color": colors[index % len(colors)], "opacity": 0.72, "showscale": False},
                text=hover_text,
                hoverinfo="text",
            )
        )

    figure.update_layout(
        map={
            "style": "open-street-map",
            "center": {"lat": records["Latitude"].mean(), "lon": records["Longitude"].mean()},
            "zoom": 10,
        },
        height=600,
        margin={"r": 0, "t": 44, "l": 0, "b": 0},
        legend={"title": "K-Means cluster", "yanchor": "top", "y": 0.99, "xanchor": "left", "x": 0.01},
        title="Record Pattern Clusters",
    )
    return figure
