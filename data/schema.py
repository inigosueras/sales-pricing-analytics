"""
Single source of truth for the required input schema.

Every other layer (validator, transformer, SQLite DDL, Power BI M-query
documentation) is written against this contract. If the schema needs to
change, it changes here first.
"""

from dataclasses import dataclass
from typing import Literal

ColumnType = Literal["date", "string", "float", "int"]


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    dtype: ColumnType
    required: bool = True
    allow_negative: bool = True
    allow_zero: bool = True


# Order matters: this is the canonical column order used when writing
# cleaned data back out and when generating the SQLite DDL.
REQUIRED_COLUMNS: list[ColumnSpec] = [
    ColumnSpec("Date", "date"),
    ColumnSpec("Product", "string"),
    ColumnSpec("Category", "string"),
    ColumnSpec("Country", "string"),
    ColumnSpec("Revenue", "float", allow_negative=False),
    ColumnSpec("Quantity", "float", allow_negative=False, allow_zero=False),
    ColumnSpec("Cost", "float", allow_negative=False),
    ColumnSpec("Customer_Segment", "string"),
]

REQUIRED_COLUMN_NAMES: list[str] = [c.name for c in REQUIRED_COLUMNS]

# Fields the transformer derives. Kept here too, so the DB DDL and the
# Streamlit column pickers stay in sync with what transformer.py actually
# produces.
DERIVED_COLUMNS: list[str] = [
    "Margin",          # Revenue - Cost
    "Margin_Pct",       # Margin / Revenue
    "Avg_Price",         # Revenue / Quantity
    "Unit_Cost",          # Cost / Quantity
    "Year",
    "Quarter",
    "Month",
    "YearMonth",           # e.g. 2025-03, used for trend grouping
]

TABLE_NAME = "sales_data"
