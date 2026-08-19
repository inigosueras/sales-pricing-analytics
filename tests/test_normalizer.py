import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.normalizer import (
    build_canonical_mapping,
    normalize_categorical_columns,
    normalize_column,
)


def test_exact_case_and_whitespace_variants_merge():
    # The user's motivating example: "on-line", "online", "online " (trailing space)
    s = pd.Series(["Online", "on-line", "online ", "ON_LINE", "Online"], name="Customer_Segment")
    mapping, report = build_canonical_mapping(s, fuzzy=True)
    canonical_values = set(mapping.values())
    assert len(canonical_values) == 1
    assert report.changed_count == 1


def test_canonical_label_is_most_frequent_original_spelling():
    # "Online" appears 3 times, "on-line" once, "ONLINE" once -> canonical should be "Online"
    s = pd.Series(["Online", "Online", "Online", "on-line", "ONLINE"], name="Customer_Segment")
    mapping, _ = build_canonical_mapping(s)
    assert mapping["on-line"] == "Online"
    assert mapping["ONLINE"] == "Online"


def test_distinct_categories_are_not_merged():
    s = pd.Series(["Retail", "Wholesale", "Government Tender"], name="Customer_Segment")
    mapping, report = build_canonical_mapping(s, fuzzy=True)
    assert len(set(mapping.values())) == 3
    assert report.changed_count == 0


def test_short_country_codes_are_not_fuzzy_merged():
    # Safety guard: short strings must never be merged by fuzzy matching,
    # only by exact normalization — "US" and "UK" must stay distinct.
    s = pd.Series(["US", "UK", "USA"], name="Country")
    mapping, _ = build_canonical_mapping(s, fuzzy=True, fuzzy_threshold=0.7)
    assert mapping["US"] != mapping["UK"]
    assert mapping["US"] != mapping["USA"]


def test_fuzzy_typo_grouping_when_enabled():
    # A near-duplicate spelling should merge with fuzzy=True at a permissive threshold
    s = pd.Series(["Wholesale", "Wholesale", "Wholesle"], name="Customer_Segment")  # missing 'a'
    mapping, report = build_canonical_mapping(s, fuzzy=True, fuzzy_threshold=0.85)
    assert mapping["Wholesle"] == "Wholesale"


def test_fuzzy_disabled_keeps_typo_separate():
    s = pd.Series(["Wholesale", "Wholesale", "Wholesle"], name="Customer_Segment")
    mapping, _ = build_canonical_mapping(s, fuzzy=False)
    assert mapping["Wholesle"] != mapping["Wholesale"]


def test_normalize_column_applies_mapping_to_dataframe():
    df = pd.DataFrame({"Customer_Segment": ["Online", "on-line", "online "]})
    out, report = normalize_column(df, "Customer_Segment")
    assert out["Customer_Segment"].nunique() == 1
    assert report.column == "Customer_Segment"


def test_normalize_categorical_columns_covers_all_default_columns():
    df = pd.DataFrame({
        "Product": ["Widget A", "widget a"],
        "Category": ["Cat1", "cat1 "],
        "Country": ["Spain", "spain"],
        "Customer_Segment": ["Online", "ONLINE"],
        "Revenue": [100, 200],  # untouched, non-categorical column
    })
    out, reports = normalize_categorical_columns(df)
    assert len(reports) == 4
    assert out["Product"].nunique() == 1
    assert out["Category"].nunique() == 1
    assert out["Country"].nunique() == 1
    assert out["Customer_Segment"].nunique() == 1
    assert list(out["Revenue"]) == [100, 200]
