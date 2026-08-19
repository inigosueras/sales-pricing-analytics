"""
metrics.py
----------
The public API the Streamlit app (and anything else) calls. Wraps
src/db.run_query with typed, purpose-specific functions so the app layer
never writes SQL or touches sqlite3 connections directly.
"""

from __future__ import annotations

import sqlite3

import pandas as pd

from src.db import Filters, run_query


def get_kpis(conn: sqlite3.Connection, filters: Filters) -> dict:
    df = run_query(conn, "kpis", filters)
    if df.empty or df.iloc[0]["total_revenue"] is None:
        return {
            "total_revenue": 0, "total_margin": 0, "margin_pct": 0,
            "avg_ticket": 0, "total_units": 0, "distinct_products": 0,
            "distinct_countries": 0,
        }
    return df.iloc[0].to_dict()


def get_monthly_trend(conn: sqlite3.Connection, filters: Filters) -> pd.DataFrame:
    return run_query(conn, "trend_yoy", filters)


def get_trend_with_yoy(conn: sqlite3.Connection, filters: Filters, freq: str = "M") -> pd.DataFrame:
    """
    Monthly or quarterly revenue trend with a prior-year comparison,
    built from the same pre-aggregated monthly SQL result (avoids a
    second query). freq='M' keeps monthly periods; freq='Q' rolls them
    up into quarters first.
    Returns columns: Period, Revenue, Quantity, Revenue_PriorYear, YoY_Pct
    """
    monthly = run_query(conn, "trend_yoy", filters)
    if monthly.empty:
        return pd.DataFrame(columns=["Period", "Revenue", "Quantity", "Revenue_PriorYear", "YoY_Pct"])

    df = monthly.copy()
    df["_dt"] = pd.to_datetime(df["YearMonth"])

    if freq == "Q":
        df["Period"] = df["_dt"].dt.to_period("Q").astype(str)
        df = df.groupby("Period", as_index=False).agg(Revenue=("revenue", "sum"), Quantity=("units", "sum"))
        df["_year"] = df["Period"].str[:4].astype(int)
        df["_q"] = df["Period"].str[-2:]
        df["_prior_key"] = (df["_year"] - 1).astype(str) + df["_q"]
    else:
        df = df.rename(columns={"YearMonth": "Period", "revenue": "Revenue", "units": "Quantity"})
        df["_prior_dt"] = pd.to_datetime(df["Period"]) - pd.DateOffset(years=1)
        df["_prior_key"] = df["_prior_dt"].dt.to_period("M").astype(str)

    revenue_lookup = dict(zip(df["Period"], df["Revenue"]))
    df["Revenue_PriorYear"] = df["_prior_key"].map(revenue_lookup)
    df["YoY_Pct"] = ((df["Revenue"] - df["Revenue_PriorYear"]) / df["Revenue_PriorYear"]) * 100

    return df[["Period", "Revenue", "Quantity", "Revenue_PriorYear", "YoY_Pct"]].sort_values("Period")


def get_top_n(
    conn: sqlite3.Connection, filters: Filters, dimension: str = "Product", limit: int = 10
) -> pd.DataFrame:
    return run_query(conn, "top_products", filters, dimension=dimension, limit=limit)


def get_geo_distribution(conn: sqlite3.Connection, filters: Filters) -> pd.DataFrame:
    return run_query(conn, "geo_distribution", filters)


def get_segment_analysis(conn: sqlite3.Connection, filters: Filters) -> pd.DataFrame:
    return run_query(conn, "segment_analysis", filters)


def get_price_volume_raw(
    conn: sqlite3.Connection, filters: Filters, dimension: str = "Product"
) -> pd.DataFrame:
    """Raw revenue/quantity by dimension x period; decomposition math applied by caller."""
    return run_query(conn, "price_volume_decomposition", filters, dimension=dimension)


def get_filter_options(conn: sqlite3.Connection, filters: Filters | None = None) -> dict:
    """
    Distinct values for building sidebar filter widgets. When `filters`
    restricts to specific dataset_ids, options are scoped to those
    datasets only — e.g. picking "Pharma" shouldn't offer "OEM" as a
    segment option.
    """
    filters = filters or Filters()
    where_sql, params = filters.to_where_clause()
    base = f"FROM sales_data {where_sql}"

    countries = pd.read_sql_query(
        f"SELECT DISTINCT Country {base} ORDER BY Country", conn, params=params
    )["Country"].tolist()
    categories = pd.read_sql_query(
        f"SELECT DISTINCT Category {base} ORDER BY Category", conn, params=params
    )["Category"].tolist()
    segments = pd.read_sql_query(
        f"SELECT DISTINCT Customer_Segment {base} ORDER BY Customer_Segment", conn, params=params
    )["Customer_Segment"].tolist()
    date_bounds = pd.read_sql_query(
        f"SELECT MIN(Date) AS min_date, MAX(Date) AS max_date {base}", conn, params=params
    ).iloc[0]
    return {
        "countries": countries,
        "categories": categories,
        "segments": segments,
        "min_date": date_bounds["min_date"],
        "max_date": date_bounds["max_date"],
    }


def get_datasets(conn: sqlite3.Connection) -> pd.DataFrame:
    """List all registered datasets — powers the dataset picker in Streamlit."""
    from src.db import list_datasets
    return list_datasets(conn)


def compare_datasets(conn: sqlite3.Connection, filters: Filters | None = None) -> pd.DataFrame:
    """Side-by-side KPI comparison across all (or selected) registered datasets."""
    return run_query(conn, "compare_datasets", filters or Filters())
