import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.db import Filters, get_connection, list_datasets, load_dataframe, run_query, delete_dataset
from src.transformer import run_full_pipeline


def _sample_df(revenue_scale=1.0):
    raw = pd.DataFrame({
        "Date": ["2024-01-15", "2024-02-15", "2024-02-20"],
        "Product": ["Widget A", "Widget A", "Widget B"],
        "Category": ["Cat1", "Cat1", "Cat2"],
        "Country": ["Spain", "France", "Spain"],
        "Revenue": [1000.0 * revenue_scale, 500.0 * revenue_scale, 300.0 * revenue_scale],
        "Quantity": [100, 50, 30],
        "Cost": [600.0 * revenue_scale, 300.0 * revenue_scale, 200.0 * revenue_scale],
        "Customer_Segment": ["Retail", "Wholesale", "Retail"],
    })
    return run_full_pipeline(raw)


def make_conn_with_one_dataset():
    conn = get_connection(":memory:")
    load_dataframe(conn, _sample_df(), dataset_name="test_dataset.csv", industry_label="Retail")
    return conn


def test_load_registers_dataset_and_rows():
    conn = make_conn_with_one_dataset()
    datasets = list_datasets(conn)
    assert len(datasets) == 1
    assert datasets.iloc[0]["dataset_name"] == "test_dataset.csv"
    assert datasets.iloc[0]["row_count"] == 3

    result = run_query(conn, "kpis", Filters())
    assert result.iloc[0]["total_revenue"] == 1800.0


def test_multiple_datasets_coexist():
    conn = get_connection(":memory:")
    id1 = load_dataframe(conn, _sample_df(revenue_scale=1.0), dataset_name="retail.csv", industry_label="Retail")
    id2 = load_dataframe(conn, _sample_df(revenue_scale=2.0), dataset_name="pharma.csv", industry_label="Pharma")

    datasets = list_datasets(conn)
    assert len(datasets) == 2

    # Filtering to dataset 1 only should return only its revenue
    result1 = run_query(conn, "kpis", Filters(dataset_ids=[id1]))
    assert result1.iloc[0]["total_revenue"] == 1800.0

    result2 = run_query(conn, "kpis", Filters(dataset_ids=[id2]))
    assert result2.iloc[0]["total_revenue"] == 3600.0

    # No filter = combined across both datasets
    combined = run_query(conn, "kpis", Filters())
    assert combined.iloc[0]["total_revenue"] == 5400.0


def test_compare_datasets_query():
    conn = get_connection(":memory:")
    load_dataframe(conn, _sample_df(1.0), dataset_name="retail.csv", industry_label="Retail")
    load_dataframe(conn, _sample_df(2.0), dataset_name="pharma.csv", industry_label="Pharma")

    comparison = run_query(conn, "compare_datasets", Filters())
    assert len(comparison) == 2
    assert set(comparison["dataset_name"]) == {"retail.csv", "pharma.csv"}
    # Higher revenue_scale dataset should be ranked first (ORDER BY revenue DESC)
    assert comparison.iloc[0]["dataset_name"] == "pharma.csv"


def test_delete_dataset_removes_rows_only_for_that_dataset():
    conn = get_connection(":memory:")
    id1 = load_dataframe(conn, _sample_df(1.0), dataset_name="retail.csv")
    id2 = load_dataframe(conn, _sample_df(2.0), dataset_name="pharma.csv")

    delete_dataset(conn, id1)

    datasets = list_datasets(conn)
    assert len(datasets) == 1
    assert datasets.iloc[0]["dataset_name"] == "pharma.csv"

    remaining = run_query(conn, "kpis", Filters())
    assert remaining.iloc[0]["total_revenue"] == 3600.0


def test_filter_by_country():
    conn = make_conn_with_one_dataset()
    result = run_query(conn, "kpis", Filters(countries=["Spain"]))
    assert result.iloc[0]["total_revenue"] == 1300.0


def test_filter_by_date_range():
    conn = make_conn_with_one_dataset()
    result = run_query(conn, "kpis", Filters(date_from="2024-02-01", date_to="2024-02-28"))
    assert result.iloc[0]["total_revenue"] == 800.0


def test_top_products_dimension():
    conn = make_conn_with_one_dataset()
    result = run_query(conn, "top_products", Filters(), dimension="Product", limit=10)
    assert list(result["name"]) == ["Widget A", "Widget B"]


def test_invalid_dimension_rejected():
    conn = make_conn_with_one_dataset()
    with pytest.raises(ValueError):
        run_query(conn, "top_products", Filters(), dimension="Revenue; DROP TABLE sales_data;")


def test_sql_injection_in_filter_value_is_safe():
    conn = make_conn_with_one_dataset()
    malicious = Filters(countries=["Spain'; DROP TABLE sales_data; --"])
    result = run_query(conn, "kpis", malicious)
    assert result.iloc[0]["total_revenue"] is None or result.iloc[0]["total_revenue"] == 0
    check = run_query(conn, "kpis", Filters())
    assert check.iloc[0]["total_revenue"] == 1800.0
