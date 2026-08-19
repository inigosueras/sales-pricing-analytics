import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.validator import validate_dataframe


def make_valid_df():
    return pd.DataFrame({
        "Date": ["2024-01-01", "2024-01-02"],
        "Product": ["Widget A", "Widget B"],
        "Category": ["Cat1", "Cat2"],
        "Country": ["Spain", "France"],
        "Revenue": [100.0, 200.0],
        "Quantity": [10, 20],
        "Cost": [60.0, 120.0],
        "Customer_Segment": ["Retail", "Wholesale"],
    })


def test_valid_dataframe_passes():
    result = validate_dataframe(make_valid_df())
    assert result.is_valid
    assert result.row_count == 2


def test_missing_column_fails():
    df = make_valid_df().drop(columns=["Cost"])
    result = validate_dataframe(df)
    assert not result.is_valid
    assert any("Missing required column" in e for e in result.errors)


def test_negative_revenue_fails():
    df = make_valid_df()
    df.loc[0, "Revenue"] = -50
    result = validate_dataframe(df)
    assert not result.is_valid
    assert any("negative value" in e for e in result.errors)


def test_zero_quantity_fails():
    df = make_valid_df()
    df.loc[0, "Quantity"] = 0
    result = validate_dataframe(df)
    assert not result.is_valid
    assert any("zero value" in e for e in result.errors)


def test_non_numeric_revenue_fails():
    df = make_valid_df()
    df["Revenue"] = df["Revenue"].astype(object)
    df.loc[0, "Revenue"] = "not_a_number"
    result = validate_dataframe(df)
    assert not result.is_valid


def test_empty_dataframe_fails():
    result = validate_dataframe(pd.DataFrame())
    assert not result.is_valid


def test_extra_column_is_warning_not_error():
    df = make_valid_df()
    df["Salesperson"] = ["Alice", "Bob"]
    result = validate_dataframe(df)
    assert result.is_valid
    assert any("Unrecognized column" in w for w in result.warnings)
