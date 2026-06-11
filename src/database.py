from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote_plus

import pandas as pd


def build_export_query(include_date_range: bool = False) -> str:
    """Build the fixed China-export query for the `axs` source table."""
    date_clause = ""
    if include_date_range:
        date_clause = """
          AND load_start_date >= :start_date
          AND load_start_date < :end_date
        """

    return f"""
        SELECT
            load_start_date,
            voy_intake_mt,
            COMMODITY,
            discharge_country
        FROM axs
        WHERE load_country = 'China'
          AND discharge_country <> 'China'
          AND load_start_date IS NOT NULL
          AND voy_intake_mt IS NOT NULL
          AND COMMODITY IS NOT NULL
          {date_clause}
        ORDER BY load_start_date DESC
    """


def create_connection_url(config: Mapping[str, Any]) -> str:
    """Create a SQLAlchemy URL from Streamlit database secrets."""
    required = ("host", "database", "user", "password")
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise ValueError(f"Missing database secrets: {', '.join(missing)}")

    port = config.get("port", 3306)
    return (
        f"mysql+pymysql://{quote_plus(str(config['user']))}:"
        f"{quote_plus(str(config['password']))}@{config['host']}:{port}/"
        f"{config['database']}?charset=utf8mb4"
    )


def load_export_data(
    config: Mapping[str, Any],
    start_date: Any,
    end_date: Any,
) -> pd.DataFrame:
    """Load scoped China-export rows for an inclusive dashboard date range."""
    from sqlalchemy import create_engine, text

    engine = create_engine(
        create_connection_url(config),
        pool_pre_ping=True,
        connect_args={"ssl": {"check_hostname": True}},
    )
    params = {
        "start_date": pd.Timestamp(start_date).date(),
        "end_date": (pd.Timestamp(end_date) + pd.Timedelta(days=1)).date(),
    }
    try:
        return pd.read_sql(text(build_export_query(include_date_range=True)), engine, params=params)
    finally:
        engine.dispose()
