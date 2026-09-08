"""
Feature engineering module for traffic accident data.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, List
import logging
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Assign grid cell based on coordinates
def assign_grid(
    lat: float,
    lon: float,
    lat_min: float = 33.7,
    lon_min: float = -118.7,
    size: float = 0.01
) -> str:
    
    try:
        # Check for NaN values
        if pd.isna(lat) or pd.isna(lon):
            return None
            
        grid_x = int((float(lat) - lat_min) / size)
        grid_y = int((float(lon) - lon_min) / size)
        return f"{grid_x}_{grid_y}"
    except Exception as e:
        logger.error(f"Error assigning grid: {str(e)}")
        return None

# Calculate features for each grid cell
def calculate_grid_features(
    df: pd.DataFrame,
    lat_min: float = 33.7,
    lon_min: float = -118.7,
    size: float = 0.01
) -> pd.DataFrame:
    
    try:
        # Assign grid cells
        df['Grid'] = df.apply(
            lambda x: assign_grid(x['Latitude'], x['Longitude'], lat_min, lon_min, size),
            axis=1
        )
        
        # Remove rows with invalid grid assignments
        df = df.dropna(subset=['Grid'])
        
        # Calculate grid-level features
        grid_features = df.groupby('Grid').agg({
            'DR Number': 'count',  # Total accidents
            'Victim Age': 'mean',  # Average victim age
            'IsWeekend': 'mean',   # Weekend accident ratio
            'Hour': lambda x: pd.Series.mode(x)[0] if not x.empty else None,  # Most common hour
            'SeverityNum': 'mean',  # Average severity (numeric)
            'Severity': lambda x: x.value_counts().index[0] if not x.empty else None  # Most common severity (category)
        }).reset_index()
        
        # Add grid center coordinates
        grid_features[['grid_x', 'grid_y']] = grid_features['Grid'].str.split('_', expand=True)
        grid_features['grid_lat'] = lat_min + grid_features['grid_x'].astype(int) * size
        grid_features['grid_lon'] = lon_min + grid_features['grid_y'].astype(int) * size
        
        # Rename columns for clarity
        grid_features = grid_features.rename(columns={
            'DR Number': 'accident_count',
            'Victim Age': 'avg_victim_age',
            'IsWeekend': 'weekend_ratio',
            'Hour': 'peak_hour',
            'SeverityNum': 'avg_severity',
            'Severity': 'most_common_severity'
        })
        
        # Remove any remaining rows with NaN values
        grid_features = grid_features.dropna()
        
        logger.info("Grid features calculated successfully")
        return grid_features
        
    except Exception as e:
        logger.error(f"Error calculating grid features: {str(e)}")
        raise

# Create feature matrix for clustering
def create_feature_matrix(
    grid_features: pd.DataFrame,
    features: List[str] = ['accident_count', 'weekend_ratio', 'peak_hour']
) -> Tuple[np.ndarray, List[str]]:
    
    try:
        # Select features and convert to numpy array
        X = grid_features[features].values
        
        logger.info(f"Feature matrix created with {len(features)} features")
        return X, features
        
    except Exception as e:
        logger.error(f"Error creating feature matrix: {str(e)}")
        raise

# Prepare features for individual accident clustering
def prepare_individual_features(df: pd.DataFrame) -> (pd.DataFrame, list):
    
    # Select features
    features = [
        'Hour', 'DayOfWeek', 'IsWeekend', 'Victim Age',
        'Victim Sex', 'Victim Descent', 'Premise Description'
    ]
    df = df.copy()
    # Define categorical and numeric columns
    categorical = ['Victim Sex', 'Victim Descent', 'Premise Description']
    numeric = ['Hour', 'DayOfWeek', 'IsWeekend', 'Victim Age']
    # Fill missing values: numeric with mean, categorical with 'Unknown'
    for col in numeric:
        df[col] = df[col].fillna(df[col].mean())
    for col in categorical:
        df[col] = df[col].fillna('Unknown')
    df = df[features]
    # Build transformer
    preprocessor = ColumnTransformer([
        ('num', StandardScaler(), numeric),
        ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical)
    ])
    X = preprocessor.fit_transform(df)
    # Get feature names
    cat_features = preprocessor.named_transformers_['cat'].get_feature_names_out(categorical)
    feature_names = numeric + list(cat_features)
    return X, feature_names 