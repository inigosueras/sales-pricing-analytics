"""
transformer.py
--------------
Takes a validated raw DataFrame and produces a clean, analysis-ready
DataFrame with all derived fields computed. This is the layer that
encodes actual pricing-analytics domain logic (margin, YoY, price/volume
decomposition), separate from validation and separate from storage.
"""

from __future__ import annotations

import pandas as pd

from src.normalizer import normalize_categorical_columns


def clean_dataframe(
    df: pd.DataFrame, normalize_categories: bool = True, fuzzy_threshold: float = 0.88
) -> pd.DataFrame:
    """
    Normalize types and handle missing values. Assumes the frame has
    already passed validator.validate_dataframe (no missing columns,
    no unparseable values) — this step is about coercion and defaults,
    not error detection.

    normalize_categories=True (default) additionally groups near-duplicate
    text values in Product/Category/Country/Customer_Segment — e.g.
    "on-line", "Online ", "ON_LINE" all collapse to one canonical label —
    using src/normalizer.py. The resulting reports (what got merged with
    what) are attached to df.attrs['normalization_reports'] for the
    caller to inspect or display.
    """
    df = df.copy()

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    for col in ["Revenue", "Quantity", "Cost"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    for col in ["Product", "Category", "Country", "Customer_Segment"]:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"": "Unknown", "nan": "Unknown"})

    reports = []
    if normalize_categories:
        df, reports = normalize_categorical_columns(df, fuzzy_threshold=fuzzy_threshold)

    # Drop rows that are unusable even after coercion (e.g. unparseable date
    # or zero quantity, which would break price-per-unit calculations)
    before = len(df)
    df = df.dropna(subset=["Date", "Revenue", "Quantity", "Cost"])
    df = df[df["Quantity"] != 0]
    dropped = before - len(df)

    df = df.reset_index(drop=True)
    if dropped:
        df.attrs["rows_dropped"] = dropped
    if reports:
        df.attrs["normalization_reports"] = reports

    return df


def add_derived_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all derived commercial/pricing metrics used across the
    dashboard. Kept separate from clean_dataframe so it can be unit
    tested against a known-clean frame.
    """
    df = df.copy()

    df["Margin"] = df["Revenue"] - df["Cost"]
    df["Margin_Pct"] = (df["Margin"] / df["Revenue"]).replace(
        [float("inf"), float("-inf")], 0
    ).fillna(0)
    df["Avg_Price"] = df["Revenue"] / df["Quantity"]
    df["Unit_Cost"] = df["Cost"] / df["Quantity"]

    df["Year"] = df["Date"].dt.year
    df["Quarter"] = df["Date"].dt.to_period("Q").astype(str)
    df["Month"] = df["Date"].dt.month
    df["YearMonth"] = df["Date"].dt.to_period("M").astype(str)

    return df


def compute_yoy_table(df: pd.DataFrame, freq: str = "M") -> pd.DataFrame:
    """
    Build a period-over-period-and-year-over-year revenue table.
    freq: 'M' for monthly, 'Q' for quarterly.
    Returns columns: Period, Revenue, Revenue_PriorYear, YoY_Pct
    """
    period_col = "YearMonth" if freq == "M" else "Quarter"

    grouped = (
        df.groupby(period_col, as_index=False)
        .agg(Revenue=("Revenue", "sum"), Quantity=("Quantity", "sum"))
        .sort_values(period_col)
    )

    # Build a prior-year lookup key to join against
    if freq == "M":
        grouped["_period_dt"] = pd.to_datetime(grouped["YearMonth"])
        grouped["_prior_key"] = (
            grouped["_period_dt"] - pd.DateOffset(years=1)
        ).dt.to_period("M").astype(str)
    else:
        grouped["_year"] = grouped["Quarter"].str[:4].astype(int)
        grouped["_q"] = grouped["Quarter"].str[-2:]
        grouped["_prior_key"] = (grouped["_year"] - 1).astype(str) + grouped["_q"]

    revenue_lookup = dict(zip(grouped[period_col], grouped["Revenue"]))
    grouped["Revenue_PriorYear"] = grouped["_prior_key"].map(revenue_lookup)
    grouped["YoY_Pct"] = (
        (grouped["Revenue"] - grouped["Revenue_PriorYear"]) / grouped["Revenue_PriorYear"]
    ) * 100

    return grouped[[period_col, "Revenue", "Quantity", "Revenue_PriorYear", "YoY_Pct"]].rename(
        columns={period_col: "Period"}
    )


def compute_price_volume_decomposition(
    df: pd.DataFrame, dimension: str = "Product", current_period: str = None, prior_period: str = None
) -> pd.DataFrame:
    """
    Classic price/volume/mix decomposition of revenue change between two
    periods (YearMonth values), grouped by a dimension (e.g. Product,
    Category, Country).

    Revenue_Change = Price_Effect + Volume_Effect
      Price_Effect  = (Price_t1 - Price_t0) * Qty_t1
      Volume_Effect = (Qty_t1 - Qty_t0) * Price_t0

    If current/prior period are not supplied, uses the latest two
    available YearMonth values in the data.
    """
    periods = sorted(df["YearMonth"].unique())
    if len(periods) < 2:
        return pd.DataFrame(
            columns=[dimension, "Revenue_t0", "Revenue_t1", "Revenue_Change", "Price_Effect", "Volume_Effect"]
        )

    t0 = prior_period or periods[-2]
    t1 = current_period or periods[-1]

    agg0 = (
        df[df["YearMonth"] == t0]
        .groupby(dimension)
        .agg(Revenue_t0=("Revenue", "sum"), Quantity_t0=("Quantity", "sum"))
    )
    agg1 = (
        df[df["YearMonth"] == t1]
        .groupby(dimension)
        .agg(Revenue_t1=("Revenue", "sum"), Quantity_t1=("Quantity", "sum"))
    )

    merged = agg0.join(agg1, how="outer").fillna(0)
    merged["Price_t0"] = (merged["Revenue_t0"] / merged["Quantity_t0"]).fillna(0)
    merged["Price_t1"] = (merged["Revenue_t1"] / merged["Quantity_t1"]).fillna(0)

    merged["Price_Effect"] = (merged["Price_t1"] - merged["Price_t0"]) * merged["Quantity_t1"]
    merged["Volume_Effect"] = (merged["Quantity_t1"] - merged["Quantity_t0"]) * merged["Price_t0"]
    merged["Revenue_Change"] = merged["Revenue_t1"] - merged["Revenue_t0"]

    return merged.reset_index()[
        [dimension, "Revenue_t0", "Revenue_t1", "Revenue_Change", "Price_Effect", "Volume_Effect"]
    ].sort_values("Revenue_Change", ascending=False)


def run_full_pipeline(
    df: pd.DataFrame, normalize_categories: bool = True, fuzzy_threshold: float = 0.88
) -> pd.DataFrame:
    """Convenience wrapper: clean (incl. category normalization) + derive in one call."""
    return add_derived_fields(
        clean_dataframe(df, normalize_categories=normalize_categories, fuzzy_threshold=fuzzy_threshold)
    )
