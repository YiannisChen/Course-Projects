"""
Data preparation module for traffic accident data.
"""

import logging

import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = (
    "Location",
    "Date Occurred",
    "Time Occurred",
    "Victim Age",
)

LOCATION_PATTERN = r"\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)"
LA_LAT_MIN = 33.7
LA_LAT_MAX = 34.3
LA_LON_MIN = -118.7
LA_LON_MAX = -118.1
AGE_GROUP_BINS = [0, 18, 30, 50, 100]
AGE_GROUP_LABELS = ["Child", "Young", "Adult", "Elderly"]
AGE_GROUP_MAP = {"Child": 0, "Young": 1, "Adult": 2, "Elderly": 3}


def load_data(file_path):
    try:
        df = pd.read_csv(file_path)
        logger.info(f"Successfully loaded data from {file_path}")
        return df
    except Exception as e:
        logger.error(f"Error loading data: {str(e)}")
        raise


def format_time_occurred(value):
    """Normalize a Time Occurred cell to HHMM, or None if it is not a valid clock time."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, bool):
        return None
    text = str(value).strip()
    if text.lower() in {"", "nan", "none", "nat"}:
        return None
    if text.endswith(".0") and text[:-2].lstrip("-").isdigit():
        text = text[:-2]
    if not text.isdigit() or not 1 <= len(text) <= 4:
        return None
    text = text.zfill(4)
    hour = int(text[:2])
    minute = int(text[2:])
    if hour > 23 or minute > 59:
        return None
    return text


def clean_coordinates(df):
    try:
        df = df.copy()
        if "Location" not in df.columns:
            raise ValueError("Missing required columns: Location")
        df = df[df["Location"].notna()].copy()
        extracted = df["Location"].astype(str).str.extract(LOCATION_PATTERN)
        df["Latitude"] = pd.to_numeric(extracted[0], errors="coerce")
        df["Longitude"] = pd.to_numeric(extracted[1], errors="coerce")
        df = df.dropna(subset=["Latitude", "Longitude"])
        df = df[
            (df["Latitude"] >= LA_LAT_MIN) & (df["Latitude"] <= LA_LAT_MAX) &
            (df["Longitude"] >= LA_LON_MIN) & (df["Longitude"] <= LA_LON_MAX)
        ]
        logger.info(f"Cleaned coordinates. Remaining rows: {len(df)}")
        return df
    except Exception as e:
        logger.error(f"Error cleaning coordinates: {str(e)}")
        raise


def extract_temporal_features(df):
    try:
        df = df.copy()
        parsed_dates = pd.to_datetime(df["Date Occurred"], errors="coerce")
        time_text = df["Time Occurred"].map(format_time_occurred)
        combined = parsed_dates.dt.strftime("%Y-%m-%d") + " " + time_text.fillna("")
        df["Date Occurred"] = pd.to_datetime(combined, format="%Y-%m-%d %H%M", errors="coerce")
        df = df.dropna(subset=["Date Occurred"])
        df["Year"] = df["Date Occurred"].dt.year
        df["Month"] = df["Date Occurred"].dt.month
        df["Hour"] = df["Date Occurred"].dt.hour
        df["DayOfWeek"] = df["Date Occurred"].dt.dayofweek
        df["IsWeekend"] = df["DayOfWeek"].isin([5, 6]).astype(int)
        logger.info("Temporal features extracted successfully")
        return df
    except Exception as e:
        logger.error(f"Error extracting temporal features: {str(e)}")
        raise


def preprocess_data(file_path):
    try:
        df = load_data(file_path)
        missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(missing)}")
        df = clean_coordinates(df)
        df = extract_temporal_features(df)
        df["AgeGroup"] = pd.cut(
            df["Victim Age"].fillna(df["Victim Age"].mean()),
            bins=AGE_GROUP_BINS,
            labels=AGE_GROUP_LABELS,
            include_lowest=True,
        )
        df["AgeGroupNum"] = pd.to_numeric(df["AgeGroup"].map(AGE_GROUP_MAP), errors="coerce")
        critical_columns = ["Latitude", "Longitude", "Year", "Month", "Hour", "AgeGroup", "AgeGroupNum"]
        df = df.dropna(subset=critical_columns)
        logger.info(f"Data preprocessing completed. Final dataset size: {len(df)} rows")
        return df
    except Exception as e:
        logger.error(f"Error in preprocessing pipeline: {str(e)}")
        raise


def save_processed_data(df, output_path):
    try:
        df.to_csv(output_path, index=False)
        logger.info(f"Processed data saved to {output_path}")
    except Exception as e:
        logger.error(f"Error saving processed data: {str(e)}")
        raise
