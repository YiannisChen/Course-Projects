"""Streamlit interface for LA Traffic Collision Pattern Analysis."""

import logging

import pandas as pd
import plotly.express as px
import streamlit as st

from traffic_hotspots.clustering import perform_clustering, perform_kmeans
from traffic_hotspots.data_preparation import preprocess_data
from traffic_hotspots.feature_engineering import calculate_grid_features, create_feature_matrix, prepare_individual_features
from traffic_hotspots.visualization import create_cluster_map, create_heatmap, create_record_cluster_map


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

st.set_page_config(page_title="LA Traffic Collision Pattern Analysis", page_icon="📊", layout="wide")


def grid_cluster_summary(grid_data: pd.DataFrame) -> pd.DataFrame:
    return (
        grid_data.groupby("Cluster")
        .agg(
            Grid_Cells=("Grid", "count"),
            Total_Collisions=("accident_count", "sum"),
            Avg_Victim_Age=("avg_victim_age", "mean"),
            Most_Common_Hour=("peak_hour", lambda values: values.mode().iloc[0] if not values.mode().empty else None),
            Weekend_Ratio=("weekend_ratio", "mean"),
        )
        .reset_index()
        .sort_values("Total_Collisions", ascending=False)
    )


def record_cluster_summary(records: pd.DataFrame) -> pd.DataFrame:
    return (
        records.groupby("Cluster")
        .agg(
            Records=("Cluster", "size"),
            Avg_Age=("Victim Age", "mean"),
            Most_Common_Hour=("Hour", lambda values: values.mode().iloc[0] if not values.mode().empty else None),
            Most_Common_Day=("DayOfWeek", lambda values: values.mode().iloc[0] if not values.mode().empty else None),
            Most_Common_Sex=("Victim Sex", lambda values: values.mode().iloc[0] if not values.mode().empty else None),
            Most_Common_Descent=("Victim Descent", lambda values: values.mode().iloc[0] if not values.mode().empty else None),
        )
        .reset_index()
        .sort_values("Records", ascending=False)
    )


def render_figure(builder, data: pd.DataFrame) -> None:
    try:
        figure = builder(data)
        if not figure.data:
            raise ValueError("The visualization did not contain any map traces.")
        st.plotly_chart(figure, width="stretch")
    except Exception as error:
        logger.exception("Visualization failed")
        st.error(f"Unable to render this visualization: {error}")


def render_metrics(*, records: int, grid_cells: int | None, groups: int, noise_percent: float | None, years: tuple[int, int]) -> None:
    columns = st.columns(4)
    columns[0].metric("Records", f"{records:,}")
    columns[1].metric("Grid Cells" if grid_cells is not None else "Selected Years", f"{grid_cells:,}" if grid_cells is not None else f"{years[0]}–{years[1]}")
    columns[2].metric("Clusters / Groups", groups)
    columns[3].metric("Noise", f"{noise_percent:.1f}%" if noise_percent is not None else "Not applicable")


def grid_controls(dataset: pd.DataFrame, include_kmeans: bool = False) -> tuple[pd.DataFrame, float, int, int | None, tuple[int, int]]:
    st.sidebar.subheader("Time Filter")
    available_years = (int(dataset["Year"].min()), int(dataset["Year"].max()))
    if available_years[0] == available_years[1]:
        selected_years = available_years
        st.sidebar.caption(f"Year Range: {available_years[0]}")
    else:
        selected_years = st.sidebar.slider("Year Range", min_value=available_years[0], max_value=available_years[1], value=available_years)
    filtered = dataset[dataset["Year"].between(*selected_years)]

    st.sidebar.subheader("Spatial Aggregation")
    grid_size = st.sidebar.slider("Grid Size (degrees)", 0.001, 0.05, 0.01, step=0.001)
    grid_data = calculate_grid_features(filtered, size=grid_size)

    st.sidebar.subheader("Clustering")
    epsilon = st.sidebar.slider("DBSCAN Epsilon", 0.1, 1.2, 0.25, step=0.05)
    st.sidebar.caption("Standardized grid-feature distance")
    min_samples = st.sidebar.slider("Minimum Samples", 1, 50, 5)
    cluster_count = None
    if include_kmeans:
        cluster_count = st.sidebar.slider("K-Means Clusters", 2, min(20, len(grid_data)), min(8, len(grid_data)))
    return grid_data, epsilon, min_samples, cluster_count, selected_years


def run_dbscan(grid_data: pd.DataFrame, epsilon: float, min_samples: int) -> pd.DataFrame:
    features, _ = create_feature_matrix(grid_data, features=["accident_count", "weekend_ratio"])
    labels, _ = perform_clustering(features, grid_data[["grid_lat", "grid_lon"]].values, epsilon, min_samples)
    result = grid_data.copy()
    result["Cluster"] = labels
    return result


def render_dbscan(dataset: pd.DataFrame) -> None:
    grid_data, epsilon, min_samples, _, years = grid_controls(dataset)
    clustered = run_dbscan(grid_data, epsilon, min_samples)
    noise_percent = 100 * (clustered["Cluster"] == -1).mean()
    groups = clustered["Cluster"].nunique() - int((-1 in clustered["Cluster"].values))
    render_metrics(records=len(dataset[dataset["Year"].between(*years)]), grid_cells=len(clustered), groups=groups, noise_percent=noise_percent, years=years)

    st.subheader("Visualization")
    view = st.radio("View", ["Collision Intensity", "Cluster Map", "Cluster Summary"], horizontal=True, label_visibility="collapsed")
    if view == "Collision Intensity":
        st.caption("Marker color and size represent collisions per grid cell.")
        render_figure(create_heatmap, clustered)
    elif view == "Cluster Map":
        st.caption("Each point is a grid cell. Neutral, low-opacity points are DBSCAN noise.")
        render_figure(create_cluster_map, clustered)
    else:
        st.caption("Descriptive statistics for grid-pattern clusters; noise is retained as cluster -1.")
        summary = grid_cluster_summary(clustered)
        st.dataframe(summary, width="stretch", hide_index=True)
        st.plotly_chart(px.bar(summary, x="Cluster", y="Total_Collisions", title="Collisions per Grid Pattern Cluster"), width="stretch")


def render_kmeans(dataset: pd.DataFrame) -> None:
    st.sidebar.subheader("Clustering")
    cluster_count = st.sidebar.slider("Number of Clusters", 2, 20, 4)
    features, _ = prepare_individual_features(dataset)
    labels, _ = perform_kmeans(features, cluster_count)
    clustered = dataset.copy()
    clustered["Cluster"] = labels
    render_metrics(records=len(clustered), grid_cells=None, groups=clustered["Cluster"].nunique(), noise_percent=None, years=(int(dataset["Year"].min()), int(dataset["Year"].max())))

    st.subheader("Visualization")
    view = st.radio("View", ["Record Pattern Map", "Cluster Summary"], horizontal=True, label_visibility="collapsed")
    if view == "Record Pattern Map":
        st.caption("A deterministic 5,000-record display sample keeps the map readable; clustering uses all uploaded records.")
        render_figure(create_record_cluster_map, clustered.sample(n=min(5_000, len(clustered)), random_state=42))
    else:
        st.caption("Descriptive summaries of record-level exploratory clusters.")
        st.dataframe(record_cluster_summary(clustered), width="stretch", hide_index=True)


def render_compare(dataset: pd.DataFrame) -> None:
    grid_data, epsilon, min_samples, cluster_count, years = grid_controls(dataset, include_kmeans=True)
    dbscan_result = run_dbscan(grid_data, epsilon, min_samples)
    features, _ = create_feature_matrix(grid_data, features=["accident_count", "weekend_ratio"])
    kmeans_labels, _ = perform_kmeans(features, cluster_count)
    comparison = dbscan_result.rename(columns={"Cluster": "DBSCAN Cluster"})
    comparison["K-Means Cluster"] = kmeans_labels
    noise_percent = 100 * (comparison["DBSCAN Cluster"] == -1).mean()
    groups = comparison["DBSCAN Cluster"].nunique() - int((-1 in comparison["DBSCAN Cluster"].values))
    render_metrics(records=len(dataset[dataset["Year"].between(*years)]), grid_cells=len(comparison), groups=groups, noise_percent=noise_percent, years=years)

    st.subheader("Grid Comparison")
    st.caption("Both methods use the same grid-level feature matrix. The overlap table is descriptive, not an accuracy or agreement score.")
    left, right = st.columns(2)
    with left:
        st.markdown("**DBSCAN cluster summary**")
        st.dataframe(grid_cluster_summary(dbscan_result), width="stretch", hide_index=True)
    with right:
        st.markdown("**Descriptive overlap**")
        st.dataframe(pd.crosstab(comparison["DBSCAN Cluster"], comparison["K-Means Cluster"]), width="stretch")


def main() -> None:
    st.title("LA Traffic Collision Pattern Analysis")
    st.caption("Interactive clustering and spatial analysis of Los Angeles traffic collision records.")
    st.sidebar.header("Analysis Parameters")
    st.sidebar.subheader("Data")
    uploaded_file = st.sidebar.file_uploader("Upload traffic collision CSV", type=["csv"])
    if uploaded_file is None:
        st.info("Upload a compatible LA traffic-collision CSV to begin the analysis.")
        st.caption("The app processes only files you upload. Expected fields include date, time, location, latitude, and longitude.")
        return

    with st.spinner("Loading and preprocessing collision records..."):
        try:
            dataset = preprocess_data(uploaded_file)
        except Exception as error:
            logger.exception("Dataset preprocessing failed")
            st.error(f"Unable to preprocess the uploaded CSV: {error}")
            return
    if dataset.empty:
        st.error("No valid collision records remain after preprocessing. Check the uploaded CSV.")
        return

    st.sidebar.success("Dataset loaded")
    st.sidebar.caption(f"{len(dataset):,} valid records")
    algorithm = st.sidebar.selectbox("Clustering Algorithm", ["DBSCAN (Grid Patterns)", "K-Means (Record Patterns)", "Compare Grid Clustering"])
    try:
        if algorithm == "DBSCAN (Grid Patterns)":
            render_dbscan(dataset)
        elif algorithm == "K-Means (Record Patterns)":
            render_kmeans(dataset)
        else:
            render_compare(dataset)
    except Exception as error:
        logger.exception("Analysis failed")
        st.error(f"Unable to complete the selected analysis: {error}")


if __name__ == "__main__":
    main()
