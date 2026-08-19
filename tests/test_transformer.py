import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.transformer import (
    add_derived_fields,
    clean_dataframe,
    compute_price_volume_decomposition,
    compute_yoy_table,
    run_full_pipeline,
)


def make_raw_df():
    return pd.DataFrame({
        "Date": ["2023-01-15", "2024-01-15", "2024-02-15"],
        "Product": ["Widget A", "Widget A", "Widget B"],
        "Category": ["Cat1", "Cat1", "Cat2"],
        "Country": ["Spain", "Spain", "France"],
        "Revenue": [1000.0, 1200.0, 500.0],
        "Quantity": [100, 100, 50],
        "Cost": [600.0, 600.0, 300.0],
        "Customer_Segment": ["Retail", "Retail", "Wholesale"],
    })


def test_clean_dataframe_parses_dates():
    df = clean_dataframe(make_raw_df())
    assert pd.api.types.is_datetime64_any_dtype(df["Date"])


def test_clean_dataframe_enforces_correct_dtypes():
    # Simulate a raw CSV read: everything comes in as text/object
    raw = make_raw_df().astype(str)
    df = clean_dataframe(raw)
    assert pd.api.types.is_datetime64_any_dtype(df["Date"])
    assert pd.api.types.is_float_dtype(df["Revenue"])
    assert pd.api.types.is_float_dtype(df["Quantity"])
    assert pd.api.types.is_float_dtype(df["Cost"])
    for col in ["Product", "Category", "Country", "Customer_Segment"]:
        assert pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col])


def test_clean_dataframe_drops_zero_quantity():
    raw = make_raw_df()
    raw.loc[0, "Quantity"] = 0
    df = clean_dataframe(raw)
    assert len(df) == 2


def test_margin_calculation():
    df = run_full_pipeline(make_raw_df())
    row = df.iloc[0]
    assert row["Margin"] == row["Revenue"] - row["Cost"]
    assert round(row["Margin_Pct"], 4) == round((row["Revenue"] - row["Cost"]) / row["Revenue"], 4)


def test_avg_price_calculation():
    df = run_full_pipeline(make_raw_df())
    row = df.iloc[0]
    assert row["Avg_Price"] == row["Revenue"] / row["Quantity"]


def test_derived_date_parts():
    df = run_full_pipeline(make_raw_df())
    assert set(df["Year"]) == {2023, 2024}
    assert "YearMonth" in df.columns


def test_yoy_table_computes_prior_year():
    df = run_full_pipeline(make_raw_df())
    yoy = compute_yoy_table(df, freq="M")
    row_2024_01 = yoy[yoy["Period"] == "2024-01"].iloc[0]
    assert row_2024_01["Revenue_PriorYear"] == 1000.0
    assert round(row_2024_01["YoY_Pct"], 1) == 20.0


def test_price_volume_decomposition_sums_to_revenue_change():
    df = run_full_pipeline(make_raw_df())
    decomp = compute_price_volume_decomposition(df, dimension="Product")
    # Price_Effect + Volume_Effect should reconcile to Revenue_Change per row
    for _, row in decomp.iterrows():
        assert abs((row["Price_Effect"] + row["Volume_Effect"]) - row["Revenue_Change"]) < 1e-6
