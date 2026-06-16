from __future__ import annotations

from collections.abc import Sequence
from math import floor, log10
from typing import Any

import pandas as pd


REQUIRED_COLUMNS = [
    "load_start_date",
    "voy_intake_mt",
    "COMMODITY",
    "discharge_country",
]

PERIOD_FREQUENCIES = {
    "Daily": "D",
    "Weekly": "W-MON",
    "Monthly": "MS",
}


def nice_axis_upper_bound(value: float) -> float:
    """Return a clean chart-axis limit that is strictly above the value."""
    if value <= 0:
        return 1.0

    magnitude = 10 ** floor(log10(value))
    scaled_value = value / magnitude
    for candidate in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if candidate > scaled_value:
            return candidate * magnitude

    return 10 * magnitude


def nice_axis_tick_step(upper_bound: float) -> float:
    """Return a clean tick interval that lands exactly on the upper bound."""
    if upper_bound <= 0:
        return 0.2

    magnitude = 10 ** floor(log10(upper_bound))
    scaled_upper_bound = round(upper_bound / magnitude, 10)
    step_factors = {
        1: 0.2,
        1.5: 0.3,
        2: 0.5,
        2.5: 0.5,
        3: 0.5,
        4: 1,
        5: 1,
        6: 1,
        8: 2,
        10: 2,
    }
    return step_factors.get(scaled_upper_bound, scaled_upper_bound / 5) * magnitude


def normalize_shipments(data: pd.DataFrame) -> pd.DataFrame:
    """Return clean shipment rows with consistent dates, volumes, and labels."""
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    result = data[REQUIRED_COLUMNS].copy()
    result["load_start_date"] = pd.to_datetime(
        result["load_start_date"], errors="coerce"
    )
    result["voy_intake_mt"] = pd.to_numeric(
        result["voy_intake_mt"], errors="coerce"
    )
    result["COMMODITY"] = result["COMMODITY"].astype("string").str.strip()
    result["discharge_country"] = (
        result["discharge_country"].astype("string").str.strip()
    )
    result = result.dropna(subset=REQUIRED_COLUMNS)
    result = result[
        (result["COMMODITY"] != "")
        & (result["discharge_country"] != "")
        & (result["voy_intake_mt"] >= 0)
    ]
    return result.sort_values("load_start_date", ascending=False).reset_index(drop=True)


def apply_filters(
    data: pd.DataFrame,
    start_date: Any,
    end_date: Any,
    commodities: Sequence[str] | None = None,
    destinations: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Filter normalized rows by inclusive date range and optional selections."""
    start = pd.Timestamp(start_date).normalize()
    end = pd.Timestamp(end_date).normalize() + pd.Timedelta(days=1)
    result = data[
        (data["load_start_date"] >= start) & (data["load_start_date"] < end)
    ]

    if commodities:
        result = result[result["COMMODITY"].isin(commodities)]
    if destinations:
        result = result[result["discharge_country"].isin(destinations)]

    return result.copy()


def aggregate_by_period(
    data: pd.DataFrame,
    grain: str,
    group_columns: Sequence[str] | None = None,
    as_of: Any | None = None,
) -> pd.DataFrame:
    """Aggregate shipment volume by the selected calendar period."""
    if grain not in PERIOD_FREQUENCIES:
        raise ValueError(f"Unsupported grain: {grain}")

    groups = list(group_columns or [])
    columns = ["period", *groups, "voy_intake_mt"]
    if data.empty:
        return pd.DataFrame(columns=columns)

    result = data.copy()
    if grain == "Weekly":
        result["period"] = (
            result["load_start_date"]
            .dt.to_period("W-SUN")
            .dt.start_time
        )
        reference_date = (
            pd.Timestamp.now().normalize()
            if as_of is None
            else pd.Timestamp(as_of).normalize()
        )
        current_week_start = reference_date.to_period("W-SUN").start_time
        result = result[result["period"] < current_week_start]
    elif grain == "Monthly":
        result["period"] = result["load_start_date"].dt.to_period("M").dt.start_time
    else:
        result["period"] = result["load_start_date"].dt.normalize()

    return (
        result.groupby(["period", *groups], as_index=False, dropna=False)[
            "voy_intake_mt"
        ]
        .sum()
        .sort_values(["period", *groups])
        .reset_index(drop=True)
    )


def top_commodities(data: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Rank commodities by shipment volume without grouping the remainder."""
    if data.empty:
        return pd.DataFrame(columns=["COMMODITY", "voy_intake_mt"])

    return (
        data.groupby("COMMODITY", as_index=False)["voy_intake_mt"]
        .sum()
        .sort_values("voy_intake_mt", ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )


def top_destinations(
    data: pd.DataFrame,
    limit: int = 20,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rank destination countries by shipment count and shipment volume."""
    shipment_columns = ["discharge_country", "shipment_count"]
    volume_columns = ["discharge_country", "voy_intake_mt"]
    if data.empty:
        return (
            pd.DataFrame(columns=shipment_columns),
            pd.DataFrame(columns=volume_columns),
        )

    grouped = (
        data.groupby("discharge_country", as_index=False)
        .agg(
            shipment_count=("discharge_country", "size"),
            voy_intake_mt=("voy_intake_mt", "sum"),
        )
    )
    by_shipments = (
        grouped.sort_values(
            ["shipment_count", "discharge_country"],
            ascending=[False, True],
        )
        .head(limit)
        .reset_index(drop=True)
    )
    by_volume = (
        grouped.sort_values(
            ["voy_intake_mt", "discharge_country"],
            ascending=[False, True],
        )
        .head(limit)
        .reset_index(drop=True)
    )
    return by_shipments[shipment_columns], by_volume[volume_columns]


def prepare_weekly_average_comparison(
    data: pd.DataFrame,
    start_date: Any,
    end_date: Any,
    as_of: Any | None = None,
) -> pd.DataFrame:
    """Align weekly daily-average shipment volume across six calendar years."""
    columns = [
        "week_start",
        "year",
        "week_seq",
        "x_date",
        "daily_average_mt",
        "four_week_average_mt",
    ]
    if data.empty:
        return pd.DataFrame(columns=columns)

    comparison_end = pd.Timestamp(end_date).normalize()
    comparison_year = comparison_end.year
    comparison_start = max(
        pd.Timestamp(start_date).normalize(),
        pd.Timestamp(comparison_year, 1, 1),
    )
    reference_date = (
        pd.Timestamp.now().normalize()
        if as_of is None
        else pd.Timestamp(as_of).normalize()
    )
    current_week_start = reference_date.to_period("W-SUN").start_time

    weekly = data.copy()
    weekly["week_start"] = (
        weekly["load_start_date"].dt.to_period("W-SUN").dt.start_time
    )
    weekly = weekly[weekly["week_start"] < current_week_start]
    weekly = (
        weekly.groupby("week_start", as_index=False)["voy_intake_mt"]
        .sum()
        .sort_values("week_start")
    )
    if weekly.empty:
        return pd.DataFrame(columns=columns)

    weekly["year"] = weekly["week_start"].dt.year
    weekly = weekly[
        weekly["year"].between(comparison_year - 5, comparison_year)
    ].copy()
    if weekly.empty:
        return pd.DataFrame(columns=columns)

    first_mondays = pd.to_datetime(weekly["year"].astype(str) + "-01-01")
    first_mondays += pd.to_timedelta((7 - first_mondays.dt.weekday) % 7, unit="D")
    weekly["week_seq"] = (
        (weekly["week_start"] - first_mondays).dt.days // 7
    ).astype(int)

    comparison_first_monday = pd.Timestamp(comparison_year, 1, 1)
    comparison_first_monday += pd.Timedelta(
        days=(7 - comparison_first_monday.weekday()) % 7
    )
    window_start_seq = max(
        0,
        int((comparison_start - comparison_first_monday).days // 7),
    )
    window_end_seq = int((comparison_end - comparison_first_monday).days // 7)
    weekly = weekly[
        weekly["week_seq"].between(window_start_seq, window_end_seq)
    ].copy()
    if weekly.empty:
        return pd.DataFrame(columns=columns)

    weekly["x_date"] = comparison_first_monday + pd.to_timedelta(
        weekly["week_seq"] * 7,
        unit="D",
    )
    weekly["daily_average_mt"] = weekly["voy_intake_mt"] / 7
    weekly["four_week_average_mt"] = weekly.groupby("year")[
        "daily_average_mt"
    ].transform(lambda values: values.rolling(window=4, min_periods=1).mean())
    return weekly[columns].sort_values(["year", "week_seq"]).reset_index(drop=True)


def weekly_historical_stats(
    weekly: pd.DataFrame,
    comparison_year: int,
) -> pd.DataFrame:
    """Summarize prior-year weekly daily averages for historical range bands."""
    columns = ["week_seq", "x_date", "min", "q25", "median", "q75", "max"]
    if weekly.empty:
        return pd.DataFrame(columns=columns)

    history = weekly[weekly["year"] < comparison_year]
    if history.empty:
        return pd.DataFrame(columns=columns)

    stats = (
        history.groupby(["week_seq", "x_date"])["daily_average_mt"]
        .agg(
            min="min",
            q25=lambda values: values.quantile(0.25),
            median="median",
            q75=lambda values: values.quantile(0.75),
            max="max",
        )
        .reset_index()
    )
    return stats[columns].sort_values("week_seq").reset_index(drop=True)


def calculate_metrics(
    data: pd.DataFrame,
    grain: str,
    as_of: Any | None = None,
) -> dict[str, Any]:
    """Calculate headline values for the active filter scope."""
    if data.empty:
        return {
            "total_volume": 0.0,
            "period_change_pct": None,
            "commodity_count": 0,
            "largest_commodity": None,
        }

    periods = aggregate_by_period(data, grain, as_of=as_of)
    period_change_pct = None
    if len(periods) >= 2:
        previous = periods.iloc[-2]["voy_intake_mt"]
        latest = periods.iloc[-1]["voy_intake_mt"]
        if previous:
            period_change_pct = ((latest - previous) / previous) * 100

    ranked = top_commodities(data, limit=1)
    return {
        "total_volume": float(data["voy_intake_mt"].sum()),
        "period_change_pct": period_change_pct,
        "commodity_count": int(data["COMMODITY"].nunique()),
        "largest_commodity": ranked.iloc[0]["COMMODITY"],
    }
