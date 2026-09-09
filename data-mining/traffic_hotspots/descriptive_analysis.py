"""Descriptive summaries rendered by the Streamlit traffic-analysis app."""

from __future__ import annotations

import pandas as pd


DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
AGE_BINS = [0, 18, 25, 35, 45, 55, 65, float("inf")]
AGE_LABELS = ["0–17", "18–24", "25–34", "35–44", "45–54", "55–64", "65+"]


def _percent(counts: pd.Series, total: int) -> pd.Series:
    if not total:
        return pd.Series(0.0, index=counts.index)
    return (100 * counts / total).round(1)


def area_summary(records: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Return highest-count source-data areas, retaining an explicit missing value."""
    areas = records["Area Name"].fillna("Unknown / missing").replace("", "Unknown / missing")
    counts = areas.value_counts().rename_axis("Area Name").reset_index(name="Records")
    counts["Share"] = _percent(counts["Records"], len(records))
    return counts.head(limit)


def hourly_summary(records: pd.DataFrame) -> pd.DataFrame:
    """Return all clock hours so zero-count hours remain visible in the UI."""
    counts = records["Hour"].value_counts().reindex(range(24), fill_value=0).sort_index()
    summary = counts.rename_axis("Hour").reset_index(name="Records")
    summary["Share"] = _percent(summary["Records"], len(records))
    return summary


def day_summary(records: pd.DataFrame) -> pd.DataFrame:
    """Return Monday-through-Sunday record counts and selected-record shares."""
    counts = records["DayOfWeek"].value_counts().reindex(range(7), fill_value=0).sort_index()
    summary = counts.rename_axis("DayOfWeek").reset_index(name="Records")
    summary["Day"] = summary["DayOfWeek"].map(dict(enumerate(DAY_NAMES)))
    summary["Share"] = _percent(summary["Records"], len(records))
    return summary[["Day", "Records", "Share"]]


def time_period_summary(records: pd.DataFrame) -> pd.DataFrame:
    """Summarize stable, human-readable hour ranges."""
    periods = pd.cut(
        records["Hour"],
        bins=[-1, 5, 9, 15, 19, 23],
        labels=["00:00–05:59", "06:00–09:59", "10:00–15:59", "16:00–19:59", "20:00–23:59"],
    )
    counts = periods.value_counts(sort=False)
    summary = counts.rename_axis("Time Period").reset_index(name="Records")
    summary["Share"] = _percent(summary["Records"], len(records))
    return summary


def weekday_weekend_hourly_summary(records: pd.DataFrame) -> pd.DataFrame:
    """Return normalized hourly profiles to compare day types fairly."""
    day_type = records["IsWeekend"].map({0: "Weekday", 1: "Weekend"})
    grouped = records.assign(**{"Day Type": day_type}).groupby(["Day Type", "Hour"], observed=False).size()
    index = pd.MultiIndex.from_product([["Weekday", "Weekend"], range(24)], names=["Day Type", "Hour"])
    summary = grouped.reindex(index, fill_value=0).rename("Records").reset_index()
    totals = summary.groupby("Day Type")["Records"].transform("sum")
    summary["Share within Day Type"] = _percent(summary["Records"], 1).where(totals.eq(0), (100 * summary["Records"] / totals).round(1))
    return summary


def weekday_weekend_daily_averages(records: pd.DataFrame) -> dict[str, float]:
    """Compare daily means, avoiding an invalid five-day vs two-day total comparison."""
    day_counts = records.groupby("DayOfWeek").size()
    weekday = day_counts.reindex(range(5), fill_value=0).mean()
    weekend = day_counts.reindex([5, 6], fill_value=0).mean()
    return {"weekday_daily_average": round(float(weekday), 1), "weekend_daily_average": round(float(weekend), 1)}


def age_distribution(records: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, float | int | None]]:
    """Describe only plausible original ages; no imputed age is used here."""
    ages = pd.to_numeric(records["Victim Age"], errors="coerce")
    valid = ages[ages.between(1, 99)]
    groups = pd.cut(valid, bins=AGE_BINS, labels=AGE_LABELS, right=False)
    counts = groups.value_counts(sort=False).reindex(AGE_LABELS, fill_value=0)
    summary = counts.rename_axis("Age Group").reset_index(name="Records")
    summary["Share of Valid Ages"] = _percent(summary["Records"], len(valid))
    coverage = {
        "valid_age_records": int(len(valid)),
        "missing_or_invalid_records": int(len(records) - len(valid)),
        "valid_age_share": round(100 * len(valid) / len(records), 1) if len(records) else 0.0,
        "median_age": round(float(valid.median()), 1) if not valid.empty else None,
    }
    return summary, coverage


def category_summary(records: pd.DataFrame, column: str, limit: int = 10) -> tuple[pd.DataFrame, float]:
    """Return raw category codes and known-value shares without assigning meanings."""
    values = records[column].fillna("Unknown / missing").replace("", "Unknown / missing")
    unknown_rate = round(100 * (values == "Unknown / missing").mean(), 1)
    known = values[values != "Unknown / missing"]
    counts = known.value_counts().rename_axis("Code").reset_index(name="Records")
    counts["Share of Known Values"] = _percent(counts["Records"], len(known))
    return counts.head(limit), unknown_rate


def kmeans_cluster_profile(records: pd.DataFrame) -> pd.DataFrame:
    """Describe record clusters while keeping age missingness explicit."""
    ages = pd.to_numeric(records["Victim Age"], errors="coerce")
    profiled = records.assign(
        _ValidAge=ages.where(ages.between(1, 99)),
        _AgeMissing=ages.isna(),
    )
    summary = (
        profiled.groupby("Cluster")
        .agg(
            Records=("Cluster", "size"),
            **{
                "Share": ("Cluster", lambda values: round(100 * len(values) / len(profiled), 1)),
                "Median Valid Age": ("_ValidAge", "median"),
                "Modal Hour": ("Hour", lambda values: values.mode().iloc[0] if not values.mode().empty else None),
                "Weekend Share": ("IsWeekend", "mean"),
                "Age Missing Share": ("_AgeMissing", "mean"),
            },
        )
        .reset_index()
        .sort_values("Records", ascending=False)
    )
    summary["Median Valid Age"] = summary["Median Valid Age"].round(1)
    summary["Weekend Share"] = (100 * summary["Weekend Share"]).round(1)
    summary["Age Missing Share"] = (100 * summary["Age Missing Share"]).round(1)
    return summary
