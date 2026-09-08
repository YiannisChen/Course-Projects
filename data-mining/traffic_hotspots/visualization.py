"""
Visualization module for traffic accident hotspots.
"""

import folium
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import pandas as pd
from typing import Dict, List, Any
import logging
import plotly.subplots as sp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create interactive map for accident hotspots
def create_hotspot_map(
    grid_features: pd.DataFrame,
    cluster_characteristics: Dict[int, Dict[str, str]],
    center_lat: float = 34.0522,
    center_lon: float = -118.2437,
    zoom_start: int = 11
) -> folium.Map:
    
    try:
        # Create base map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=zoom_start,
            tiles='CartoDB positron'
        )
        
        # Define color palette for clusters
        colors = {
            'Nightlife Hotspot': '#FF6B6B',
            'Commuter Hotspot': '#4ECDC4',
            'School Zone Hotspot': '#FFD166',
            'Senior Zone Hotspot': '#06D6A0',
            'General Hotspot': '#118AB2'
        }
        
        # Add grid cells to map
        for _, row in grid_features.iterrows():
            if row['cluster'] == -1:  # Skip noise points
                continue
                
            cluster_type = cluster_characteristics[row['cluster']]['type']
            color = colors.get(cluster_type, '#808080')
            
            # Create popup content
            popup_content = f"""
                <b>Cluster Type:</b> {cluster_type}<br>
                <b>Accidents:</b> {row['accident_count']}<br>
                <b>Weekend Ratio:</b> {row['weekend_ratio']:.2f}<br>
                <b>Peak Hour:</b> {int(row['peak_hour'])}:00
            """
            
            # Add circle marker
            folium.CircleMarker(
                location=[row['grid_lat'], row['grid_lon']],
                radius=row['accident_count'] / 5,  # Scale marker size
                color=color,
                fill=True,
                fill_opacity=0.6,
                popup=folium.Popup(popup_content, max_width=300)
            ).add_to(m)
            
        # Add legend
        legend_html = '''
            <div style="position: fixed; 
                        bottom: 50px; right: 50px; width: 150px; height: 180px; 
                        border:2px solid grey; z-index:9999; background-color:white;
                        padding: 10px; font-size: 14px;">
                <p><b>Hotspot Types:</b></p>
        '''
        
        for hotspot_type, color in colors.items():
            legend_html += f'''
                <p><i class="fa fa-circle" style="color:{color}"></i> {hotspot_type}</p>
            '''
            
        legend_html += '</div>'
        
        m.get_root().html.add_child(folium.Element(legend_html))
        
        logger.info("Hotspot map created successfully")
        return m
        
    except Exception as e:
        logger.error(f"Error creating hotspot map: {str(e)}")
        raise

# Create comparison chart for clusters
def create_cluster_comparison(cluster_stats: pd.DataFrame, cluster_characteristics: Dict[int, Dict[str, Any]]) -> go.Figure:
    # Support flexible column names for both DBSCAN and KMeans
    col_map = {
        'accident_count': None,
        'avg_severity': None,
        'weekend_ratio': None
    }
    # Try to find the best match for each metric
    for col in cluster_stats.columns:
        if col.lower() in ['accident_count', 'total_accidents']:
            col_map['accident_count'] = col
        if col.lower() in ['avg_severity', 'avg_severitynum']:
            col_map['avg_severity'] = col
        if col.lower() in ['weekend_ratio', 'avg_weekend_ratio']:
            col_map['weekend_ratio'] = col
    metrics = [k for k, v in col_map.items() if v is not None]
    if len(metrics) == 0:
        # Return a blank figure if no valid metrics
        fig = go.Figure()
        fig.update_layout(title='No valid metrics to plot for this clustering result.')
        return fig
    fig = sp.make_subplots(rows=len(metrics), cols=1, shared_xaxes=True, subplot_titles=[k.replace('_', ' ').title() for k in metrics])
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    for i, metric in enumerate(metrics):
        col = col_map[metric]
        fig.add_trace(go.Bar(
            x=cluster_stats.index,
            y=cluster_stats[col],
            name=metric.replace('_', ' ').title(),
            marker_color=colors[i % len(colors)],
            text=cluster_stats[col].round(2),
            textposition='auto',
        ), row=i+1, col=1)
    fig.update_layout(
        title='Cluster Characteristics Comparison',
        xaxis_title='Cluster',
        yaxis_title='Value',
        barmode='group',
        height=300*len(metrics),
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        )
    )
    return fig

# Plot accident trends by cluster
def create_time_series_plot(
    df: pd.DataFrame,
    cluster_labels: np.ndarray
) -> go.Figure:
    
    try:
        # Prepare data
        df['cluster'] = cluster_labels
        df['Date'] = pd.to_datetime(df['Date Occurred']).dt.date
        
        # Group by date and cluster
        time_series = df.groupby(['Date', 'cluster']).size().reset_index(name='count')
        
        # Create time series plot
        fig = px.line(
            time_series,
            x='Date',
            y='count',
            color='cluster',
            title='Accident Trends by Cluster',
            labels={
                'Date': 'Date',
                'count': 'Number of Accidents',
                'cluster': 'Cluster'
            }
        )
        
        # Update layout
        fig.update_layout(
            height=400,
            width=800,
            margin=dict(l=50, r=50, t=50, b=50),
            hovermode='x unified'
        )
        
        logger.info("Time series plot created successfully")
        return fig
        
    except Exception as e:
        logger.error(f"Error creating time series plot: {str(e)}")
        raise

# Create accident density heatmap
def create_heatmap(grid_features: pd.DataFrame) -> go.Figure:
    
    fig = go.Figure(go.Densitymapbox(
        lat=grid_features['grid_lat'],
        lon=grid_features['grid_lon'],
        z=grid_features['accident_count'],
        radius=10,
        colorscale='Hot',
        opacity=0.7
    ))
    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_center_lat=grid_features['grid_lat'].mean(),
        mapbox_center_lon=grid_features['grid_lon'].mean(),
        mapbox_zoom=11,
        margin={"r":0,"t":0,"l":0,"b":0},
        title="Heatmap: Color intensity shows the number of accidents in each grid cell. Brighter = more accidents."
    )
    return fig

# Show clusters on a map
def create_cluster_map(grid_features: pd.DataFrame) -> go.Figure:
   
    unique_clusters = grid_features['Cluster'].unique()
    colors = px.colors.qualitative.Set1 + px.colors.qualitative.Pastel
    color_map = {cluster: colors[i % len(colors)] for i, cluster in enumerate(sorted(unique_clusters))}
    fig = go.Figure()
    for cluster in unique_clusters:
        cluster_data = grid_features[grid_features['Cluster'] == cluster]
        fig.add_trace(go.Scattermapbox(
            lat=cluster_data['grid_lat'],
            lon=cluster_data['grid_lon'],
            mode='markers',
            marker=go.scattermapbox.Marker(
                size=10,
                color=color_map[cluster],
                opacity=0.7
            ),
            name=f'Cluster {cluster}',
            text=cluster_data.apply(
                lambda row: f"Accidents: {row['accident_count']}<br>Severity: {row['avg_severity']:.2f}",
                axis=1
            ),
            hoverinfo='text'
        ))
    fig.update_layout(
        mapbox_style="open-street-map",
        mapbox_center_lat=grid_features['grid_lat'].mean(),
        mapbox_center_lon=grid_features['grid_lon'].mean(),
        mapbox_zoom=11,
        margin={"r":0,"t":0,"l":0,"b":0},
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        title="Cluster Map: Each point is a grid cell, colored by cluster label."
    )
    return fig 