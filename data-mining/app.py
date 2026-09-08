"""
Main Streamlit application for Traffic Accident Hotspot Analysis.
"""

import streamlit as st
import pandas as pd
import numpy as np
import logging
from traffic_hotspots.data_preparation import preprocess_data
from traffic_hotspots.feature_engineering import assign_grid, calculate_grid_features, create_feature_matrix, prepare_individual_features
from traffic_hotspots.clustering import perform_clustering, perform_kmeans, perform_agglomerative
from traffic_hotspots.visualization import create_heatmap, create_cluster_map, create_cluster_comparison

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="LA Traffic Accident Hotspots",
    page_icon="��",
    layout="wide"
)

# Main Streamlit app for accident hotspot analysis
def main():
    st.title("Traffic Accident Hotspot Analysis")
    st.sidebar.header("Analysis Parameters")
    algorithm = st.sidebar.selectbox(
        "Clustering Algorithm",
        ["DBSCAN (Spatial Hotspots)", "K-Means (Accident Patterns)", "Compare Clustering"]
    )
    uploaded_file = st.sidebar.file_uploader("Upload Traffic Collision Data (CSV)", type=['csv'])
    if uploaded_file is not None:
        try:
            df = preprocess_data(uploaded_file)
            if len(df) == 0:
                st.error("No valid data found after preprocessing. Please check your data file.")
                return
            if algorithm == "DBSCAN (Spatial Hotspots)":
                min_year = int(df['Year'].min())
                max_year = int(df['Year'].max())
                year_range = st.sidebar.slider("Select Year Range", min_value=min_year, max_value=max_year, value=(min_year, max_year))
                df_filtered = df[(df['Year'] >= year_range[0]) & (df['Year'] <= year_range[1])]
                grid_size = st.sidebar.slider("Grid Size (degrees)", 0.001, 0.05, 0.01, step=0.001)
                lat_min = df_filtered['Latitude'].min()
                lon_min = df_filtered['Longitude'].min()
                df_filtered['Grid'] = df_filtered.apply(lambda row: assign_grid(row['Latitude'], row['Longitude'], lat_min, lon_min, grid_size), axis=1)
                grid_features = calculate_grid_features(df_filtered, lat_min=lat_min, lon_min=lon_min, size=grid_size)
                if len(grid_features) == 0:
                    st.error("No valid grid features could be calculated.")
                    return
                eps = st.sidebar.slider("DBSCAN Epsilon", 0.001, 0.5, 0.05, step=0.001)
                min_samples = st.sidebar.slider("Minimum Samples", 1, 50, 3)
                X, feature_names = create_feature_matrix(grid_features, features=['accident_count', 'avg_severity', 'weekend_ratio', 'peak_hour'])
                coords = grid_features[['grid_lat', 'grid_lon']].values
                labels, dbscan = perform_clustering(X, coords, eps, min_samples)
                grid_features['Cluster'] = labels
                cluster_data = grid_features
                cluster_type = 'grid'
            elif algorithm == "K-Means (Accident Patterns)":
                n_clusters = st.sidebar.slider("Number of Clusters", 2, 20, 8)
                X, feature_names = prepare_individual_features(df)
                labels, model = perform_kmeans(X, n_clusters)
                df['Cluster'] = labels
                st.write("Unique clusters:", df['Cluster'].unique())
                st.write("Cluster counts:", df['Cluster'].value_counts())
                cluster_data = df
                cluster_type = 'individual'
            elif algorithm == "Compare Clustering":
                min_year = int(df['Year'].min())
                max_year = int(df['Year'].max())
                year_range = st.sidebar.slider("Select Year Range", min_value=min_year, max_value=max_year, value=(min_year, max_year))
                df_filtered = df[(df['Year'] >= year_range[0]) & (df['Year'] <= year_range[1])]
                grid_size = st.sidebar.slider("Grid Size (degrees)", 0.001, 0.05, 0.01, step=0.001)
                lat_min = df_filtered['Latitude'].min()
                lon_min = df_filtered['Longitude'].min()
                df_filtered['Grid'] = df_filtered.apply(lambda row: assign_grid(row['Latitude'], row['Longitude'], lat_min, lon_min, grid_size), axis=1)
                grid_features = calculate_grid_features(df_filtered, lat_min=lat_min, lon_min=lon_min, size=grid_size)
                if len(grid_features) == 0:
                    st.error("No valid grid features could be calculated.")
                    return
                eps = st.sidebar.slider("DBSCAN Epsilon", 0.001, 0.5, 0.05, step=0.001)
                min_samples = st.sidebar.slider("Minimum Samples", 1, 50, 3)
                n_clusters = st.sidebar.slider("K-Means Clusters", 2, 20, 8)
                X, feature_names = create_feature_matrix(grid_features, features=['accident_count', 'avg_severity', 'weekend_ratio', 'peak_hour'])
                coords = grid_features[['grid_lat', 'grid_lon']].values
                dbscan_labels, _ = perform_clustering(X, coords, eps, min_samples)
                kmeans_labels, _ = perform_kmeans(X, n_clusters)
                comparison_df = grid_features.copy()
                comparison_df['DBSCAN_Cluster'] = dbscan_labels
                comparison_df['KMeans_Cluster'] = kmeans_labels
                # --- DBSCAN Cluster-level summary (exclude noise) ---
                dbscan_summary = comparison_df[comparison_df['DBSCAN_Cluster'] != -1].groupby('DBSCAN_Cluster').agg(
                    Grid_Cells=('Grid', 'count'),
                    Total_Accidents=('accident_count', 'sum'),
                    Avg_Victim_Age=('avg_victim_age', 'mean'),
                    Most_Common_Hour=('peak_hour', lambda x: x.mode().iloc[0] if not x.mode().empty else None),
                    Avg_Weekend_Ratio=('weekend_ratio', 'mean')
                ).reset_index().rename(columns={'DBSCAN_Cluster': 'Cluster'})
                dbscan_summary = dbscan_summary.sort_values('Total_Accidents', ascending=False).head(20)
                st.subheader("DBSCAN Cluster Summary (Top 20, Excluding Noise)")
                st.markdown("Each row summarizes a DBSCAN cluster: number of grid cells, total accidents, average victim age, most common hour, and average weekend ratio. Noise cluster (-1) is excluded.")
                st.dataframe(dbscan_summary)
                # Bar chart for DBSCAN clusters
                import plotly.express as px
                if not dbscan_summary.empty:
                    bar_fig = px.bar(
                        dbscan_summary,
                        x='Cluster',
                        y='Total_Accidents',
                        title='Accident Count per DBSCAN Cluster (Top 20, Excluding Noise)',
                        labels={'Cluster': 'Cluster', 'Total_Accidents': 'Accident Count'}
                    )
                    st.plotly_chart(bar_fig)
                else:
                    st.info("No DBSCAN clusters found (excluding noise). Try adjusting parameters.")
                # --- KMeans Cluster-level summary ---
                kmeans_summary = comparison_df.groupby('KMeans_Cluster').agg(
                    Grid_Cells=('Grid', 'count'),
                    Total_Accidents=('accident_count', 'sum'),
                    Avg_Victim_Age=('avg_victim_age', 'mean'),
                    Most_Common_Hour=('peak_hour', lambda x: x.mode().iloc[0] if not x.mode().empty else None),
                    Avg_Weekend_Ratio=('weekend_ratio', 'mean')
                ).reset_index().rename(columns={'KMeans_Cluster': 'Cluster'})
                kmeans_summary = kmeans_summary.sort_values('Total_Accidents', ascending=False).head(20)
                st.subheader("KMeans Cluster Summary (Top 20)")
                st.markdown("Each row summarizes a KMeans cluster: number of grid cells, total accidents, average victim age, most common hour, and average weekend ratio.")
                st.dataframe(kmeans_summary)
                if not kmeans_summary.empty:
                    kmeans_bar = px.bar(
                        kmeans_summary,
                        x='Cluster',
                        y='Total_Accidents',
                        title='Accident Count per KMeans Cluster (Top 20)',
                        labels={'Cluster': 'Cluster', 'Total_Accidents': 'Accident Count'}
                    )
                    st.plotly_chart(kmeans_bar)
                # --- Optional: Crosstab heatmap ---
                st.subheader("DBSCAN vs KMeans Cluster Overlap (Crosstab)")
                crosstab = pd.crosstab(comparison_df['DBSCAN_Cluster'], comparison_df['KMeans_Cluster'])
                st.dataframe(crosstab)
                st.markdown("This table shows how grid cells are distributed across DBSCAN and KMeans clusters.")
                if len(comparison_df['DBSCAN_Cluster'].unique()) > 20:
                    st.info("Table truncated: showing only top 20 DBSCAN clusters by accident count.")
                return
            st.subheader("Visualization")
            visualization_type = st.radio("Select Visualization Type", ["Heatmap", "Cluster Map", "Cluster Comparison"])
            if visualization_type == "Heatmap":
                if cluster_type == 'grid':
                    fig = create_heatmap(cluster_data)
                    st.plotly_chart(fig)
                else:
                    st.info("Heatmap is only available for grid-based (DBSCAN) clustering.")
            elif visualization_type == "Cluster Map":
                if cluster_type == 'grid':
                    fig = create_cluster_map(cluster_data)
                    st.plotly_chart(fig)
                    st.subheader("Cluster Statistics Table")
                    stats_table = cluster_data.groupby('Cluster').agg({
                        'accident_count': 'sum',
                        'avg_victim_age': 'mean',
                        'peak_hour': lambda x: x.mode().iloc[0] if not x.mode().empty else None,
                        'weekend_ratio': 'mean'
                    }).reset_index()
                    stats_table = stats_table.rename(columns={
                        'accident_count': 'Accident Count',
                        'avg_victim_age': 'Avg Victim Age',
                        'peak_hour': 'Most Common Hour',
                        'weekend_ratio': 'Weekend Ratio'
                    })
                    st.dataframe(stats_table)
                    st.subheader("Accident Count per Cluster (Bar Chart)")
                    import plotly.express as px
                    bar_fig = px.bar(
                        stats_table,
                        x='Cluster',
                        y='Accident Count',
                        title='Accident Count per Cluster',
                        labels={'Cluster': 'Cluster', 'Accident Count': 'Accident Count'}
                    )
                    st.plotly_chart(bar_fig)
                else:
                    import plotly.express as px
                    hover_cols = ['Victim Age', 'Hour', 'DayOfWeek', 'IsWeekend', 'Victim Sex', 'Victim Descent', 'Premise Description']
                    hover_cols = [col for col in hover_cols if col in cluster_data.columns]
                    plot_df = cluster_data.sample(n=5000) if len(cluster_data) > 5000 else cluster_data
                    try:
                        fig = px.scatter_mapbox(
                            plot_df,
                            lat='Latitude', lon='Longitude',
                            color='Cluster',
                            hover_data=hover_cols,
                            zoom=10, height=600,
                            mapbox_style="open-street-map",
                            title="Accident Pattern Clusters (Individual Accidents)"
                        )
                        st.plotly_chart(fig)
                    except Exception as plot_err:
                        st.error(f"Error plotting cluster map: {plot_err}")
                        st.write(plot_df.head())
                    st.subheader("K-Means Cluster Summary Table")
                    summary = cluster_data.groupby('Cluster').agg({
                        'Victim Age': 'mean',
                        'Hour': lambda x: x.mode().iloc[0] if not x.mode().empty else None,
                        'DayOfWeek': lambda x: x.mode().iloc[0] if not x.mode().empty else None,
                        'Victim Sex': lambda x: x.mode().iloc[0] if not x.mode().empty else None,
                        'Victim Descent': lambda x: x.mode().iloc[0] if not x.mode().empty else None,
                        'Premise Description': lambda x: x.mode().iloc[0] if not x.mode().empty else None
                    })
                    summary = summary.rename(columns={
                        'Victim Age': 'Avg Age',
                        'Hour': 'Most Common Hour',
                        'DayOfWeek': 'Most Common Day',
                        'Victim Sex': 'Most Common Sex',
                        'Victim Descent': 'Most Common Descent',
                        'Premise Description': 'Most Common Premise'
                    })
                    st.dataframe(summary)
            else:
                if cluster_type == 'grid':
                    cluster_stats = cluster_data.groupby('Cluster').agg({
                        'accident_count': 'sum',
                        'avg_severity': 'mean',
                        'weekend_ratio': 'mean'
                    })
                else:
                    cluster_stats = cluster_data.groupby('Cluster').agg({
                        'Victim Age': 'mean',
                        'Hour': 'mean',
                        'DayOfWeek': 'mean',
                        'IsWeekend': 'mean'
                    })
                cluster_characteristics = {cluster: {} for cluster in cluster_stats.index}
                if len(cluster_stats) > 0:
                    fig = create_cluster_comparison(cluster_stats, cluster_characteristics)
                    st.plotly_chart(fig)
                else:
                    st.info("No clusters found to compare.")
            st.subheader("Statistics")
            if cluster_type == 'grid':
                st.metric("Total Accidents", len(df_filtered))
                st.metric("Grid Cells", len(grid_features))
                st.metric("Clusters", len(cluster_data['Cluster'].unique()))
            else:
                st.metric("Total Accidents", len(df))
                st.metric("Clusters", len(cluster_data['Cluster'].unique()))
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            logger.error(f"Error in main application: {str(e)}")

if __name__ == "__main__":
    main()

else:
    st.info("Please upload a CSV file containing traffic collision data to begin the analysis.") 