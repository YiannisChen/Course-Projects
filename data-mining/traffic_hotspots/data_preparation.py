"""
Data preparation module for traffic accident data.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load data from CSV
def load_data(file_path):
    try:
        df = pd.read_csv(file_path)
        logger.info(f"Successfully loaded data from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        raise

# Clean and parse coordinates
def clean_coordinates(df):
    try:
        df = df[df['Location'].notna()]
        df['Latitude'] = df['Location'].str.extract(r'\((\d+\.\d+),')[0].astype(float)
        df['Longitude'] = df['Location'].str.extract(r',\s*(-\d+\.\d+)\)')[0].astype(float)
        df = df.dropna(subset=['Latitude', 'Longitude'])
        df = df[
            (df['Latitude'] >= 33.7) & (df['Latitude'] <= 34.3) &
            (df['Longitude'] >= -118.7) & (df['Longitude'] <= -118.1)
        ]
        logger.info(f"Cleaned coordinates. Remaining rows: {len(df)}")
        return df
    except Exception as e:
        logger.error(f"Error cleaning coordinates: {str(e)}")
        raise

# Extract time features
def extract_temporal_features(df):
    try:
        df['Time Occurred'] = df['Time Occurred'].astype(str).str.zfill(4)
        df['Date Occurred'] = pd.to_datetime(
            df['Date Occurred'] + ' ' + df['Time Occurred'],
            format='%m/%d/%Y %H%M',
            errors='coerce'
        )
        df = df.dropna(subset=['Date Occurred'])
        df['Year'] = df['Date Occurred'].dt.year
        df['Month'] = df['Date Occurred'].dt.month
        df['Hour'] = df['Date Occurred'].dt.hour
        df['DayOfWeek'] = df['Date Occurred'].dt.dayofweek
        df['IsWeekend'] = df['DayOfWeek'].isin([5,6]).astype(int)
        logger.info("Temporal features extracted successfully")
        return df
    except Exception as e:
        logger.error(f"Error extracting temporal features: {str(e)}")
        raise

# Full preprocessing pipeline
def preprocess_data(file_path):
    try:
        df = load_data(file_path)
        df = clean_coordinates(df)
        df = extract_temporal_features(df)
        df['Severity'] = pd.cut(
            df['Victim Age'].fillna(df['Victim Age'].mean()),
            bins=[0, 18, 30, 50, 100],
            labels=['Child', 'Young', 'Adult', 'Elderly']
        )
        severity_map = {'Child': 0, 'Young': 1, 'Adult': 2, 'Elderly': 3}
        df['SeverityNum'] = df['Severity'].map(severity_map)
        df['SeverityNum'] = pd.to_numeric(df['SeverityNum'], errors='coerce')
        critical_columns = ['Latitude', 'Longitude', 'Year', 'Month', 'Hour', 'Severity', 'SeverityNum']
        df = df.dropna(subset=critical_columns)
        logger.info(f"Data preprocessing completed. Final dataset size: {len(df)} rows")
        return df
    except Exception as e:
        logger.error(f"Error in preprocessing pipeline: {str(e)}")
        raise

# Save processed data to CSV
def save_processed_data(df, output_path):
    try:
        df.to_csv(output_path, index=False)
        logger.info(f"Processed data saved to {output_path}")
    except Exception as e:
        logger.error(f"Error saving processed data: {str(e)}")
        raise 