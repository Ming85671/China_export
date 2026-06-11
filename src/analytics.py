from __future__ import annotations

from collections.abc import Sequence
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


def exclude_commodities(
    data: pd.DataFrame,
    commodities: Sequence[str],
) -> pd.DataFrame:
    """Exclude named commodities using case-insensitive matching."""
    excluded = {commodity.strip().casefold() for commodity in commodities}
    if not excluded or data.empty:
        return data.copy()

    normalized_names = data["COMMODITY"].astype("string").str.strip().str.casefold()
    return data[~normalized_names.isin(excluded)].copy()


def calculate_metrics(data: pd.DataFrame, grain: str) -> dict[str, Any]:
    """Calculate headline values for the active filter scope."""
    if data.empty:
        return {
            "total_volume": 0.0,
            "period_change_pct": None,
            "commodity_count": 0,
            "largest_commodity": None,
        }

    periods = aggregate_by_period(data, grain)
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
