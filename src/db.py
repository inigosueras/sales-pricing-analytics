"""
db.py
-----
Owns the SQLite lifecycle: schema creation, registering + loading
datasets, and safely building the dynamic WHERE clauses used by the
standardized queries in sql/queries/.

MULTI-DATASET DESIGN: every uploaded file is registered as a row in
`datasets` and its rows are tagged with that dataset_id in `sales_data`.
Multiple uploads coexist in the same SQLite connection, so the app can
filter to one dataset, or compare several (e.g. retail vs pharma) side
by side using the same standardized queries.

Centralizing WHERE-clause construction here (rather than in Streamlit)
keeps SQL injection risk contained to one reviewed function, even though
inputs come from dropdowns, not free text.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"
SCHEMA_PATH = SQL_DIR / "schema.sql"
QUERIES_DIR = SQL_DIR / "queries"

DB_COLUMNS = [
    "dataset_id", "Date", "Product", "Category", "Country", "Revenue", "Quantity", "Cost",
    "Customer_Segment", "Margin", "Margin_Pct", "Avg_Price", "Unit_Cost",
    "Year", "Quarter", "Month", "YearMonth",
]


def get_connection(db_path: str = ":memory:") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """Idempotent: uses CREATE TABLE/INDEX IF NOT EXISTS, safe to call every session start."""
    ddl = SCHEMA_PATH.read_text()
    conn.executescript(ddl)
    conn.commit()


def register_dataset(
    conn: sqlite3.Connection, dataset_name: str, row_count: int, industry_label: str | None = None
) -> int:
    """Insert a row into `datasets` and return the new dataset_id."""
    cur = conn.execute(
        "INSERT INTO datasets (dataset_name, industry_label, uploaded_at, row_count) "
        "VALUES (?, ?, ?, ?)",
        (dataset_name, industry_label, datetime.now(timezone.utc).isoformat(), row_count),
    )
    conn.commit()
    return cur.lastrowid


def load_dataframe(
    conn: sqlite3.Connection,
    df: pd.DataFrame,
    dataset_name: str,
    industry_label: str | None = None,
) -> int:
    """
    Register a new dataset and load a fully cleaned + transformed
    DataFrame (output of transformer.run_full_pipeline) into sales_data,
    tagged with the new dataset_id. Existing datasets are left untouched
    — this is an APPEND, not a replace, enabling multi-dataset comparison.
    Returns the new dataset_id.
    """
    create_schema(conn)

    dataset_id = register_dataset(conn, dataset_name, row_count=len(df), industry_label=industry_label)

    out = df.copy()
    out["Date"] = out["Date"].dt.strftime("%Y-%m-%d")
    out["dataset_id"] = dataset_id
    out = out[DB_COLUMNS]
    out.to_sql("sales_data", conn, if_exists="append", index=False)
    conn.commit()
    return dataset_id


def list_datasets(conn: sqlite3.Connection) -> pd.DataFrame:
    """Returns all registered datasets — used to populate the dataset picker in Streamlit."""
    create_schema(conn)
    return pd.read_sql_query(
        "SELECT dataset_id, dataset_name, industry_label, uploaded_at, row_count "
        "FROM datasets ORDER BY uploaded_at DESC",
        conn,
    )


def delete_dataset(conn: sqlite3.Connection, dataset_id: int) -> None:
    """Remove a dataset and its rows (e.g. user wants to clear an upload)."""
    conn.execute("DELETE FROM sales_data WHERE dataset_id = ?", (dataset_id,))
    conn.execute("DELETE FROM datasets WHERE dataset_id = ?", (dataset_id,))
    conn.commit()


@dataclass
class Filters:
    dataset_ids: list[int] = field(default_factory=list)   # empty = all datasets
    date_from: str | None = None      # 'YYYY-MM-DD'
    date_to: str | None = None
    countries: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    segments: list[str] = field(default_factory=list)

    def to_where_clause(self) -> tuple[str, list]:
        """
        Builds a parameterized WHERE clause (using '?' placeholders) plus
        the matching list of parameter values, safe against SQL injection
        since values are never string-interpolated into the query text.
        """
        clauses: list[str] = []
        params: list = []

        # Qualified with the table name (not just an alias) so this clause
        # is unambiguous whether the query selects from sales_data alone
        # or joins it against datasets (both tables have a dataset_id
        # column — see sql/queries/compare_datasets.sql).
        if self.dataset_ids:
            placeholders = ",".join(["?"] * len(self.dataset_ids))
            clauses.append(f"sales_data.dataset_id IN ({placeholders})")
            params.extend(self.dataset_ids)
        if self.date_from:
            clauses.append("sales_data.Date >= ?")
            params.append(self.date_from)
        if self.date_to:
            clauses.append("sales_data.Date <= ?")
            params.append(self.date_to)
        if self.countries:
            placeholders = ",".join(["?"] * len(self.countries))
            clauses.append(f"sales_data.Country IN ({placeholders})")
            params.extend(self.countries)
        if self.categories:
            placeholders = ",".join(["?"] * len(self.categories))
            clauses.append(f"sales_data.Category IN ({placeholders})")
            params.extend(self.categories)
        if self.segments:
            placeholders = ",".join(["?"] * len(self.segments))
            clauses.append(f"sales_data.Customer_Segment IN ({placeholders})")
            params.extend(self.segments)

        if not clauses:
            return "", []
        return "WHERE " + " AND ".join(clauses), params


_ALLOWED_DIMENSIONS = {"Product", "Category", "Country", "Customer_Segment", "dataset_id"}


def run_multi_dimension_query(
    conn: sqlite3.Connection,
    filters: Filters | None,
    dimensions: list[str],
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Groups by 1–N dimensions at once (e.g. Country + Category + Product),
    like an Excel PivotTable with multiple row fields. Each dimension is
    validated against the same allowlist used by run_query — since SQLite
    can't parameterize column/identifier names, this allowlist check is
    what keeps dynamic GROUP BY safe from injection.
    """
    if not dimensions:
        raise ValueError("At least one dimension is required.")
    invalid = [d for d in dimensions if d not in _ALLOWED_DIMENSIONS]
    if invalid:
        raise ValueError(f"Invalid dimension(s): {invalid}. Must be from {_ALLOWED_DIMENSIONS}.")

    filters = filters or Filters()
    where_sql, params = filters.to_where_clause()
    dims_sql = ", ".join(dimensions)
    limit_sql = f"LIMIT {int(limit)}" if limit else ""

    sql = f"""
        SELECT
            {dims_sql},
            SUM(Revenue) AS revenue,
            SUM(Margin) AS margin,
            ROUND(100.0 * SUM(Margin) / NULLIF(SUM(Revenue), 0), 2) AS margin_pct,
            SUM(Quantity) AS units,
            ROUND(SUM(Revenue) / NULLIF(COUNT(*), 0), 2) AS avg_ticket
        FROM sales_data
        {where_sql}
        GROUP BY {dims_sql}
        ORDER BY revenue DESC
        {limit_sql}
    """
    return pd.read_sql_query(sql, conn, params=params)


def _load_query(name: str) -> str:
    path = QUERIES_DIR / f"{name}.sql"
    if not path.exists():
        raise FileNotFoundError(f"No SQL file found for query '{name}'")
    return path.read_text()


def run_query(
    conn: sqlite3.Connection,
    query_name: str,
    filters: Filters | None = None,
    dimension: str | None = None,
    limit: int | None = None,
) -> pd.DataFrame:
    """
    Load a .sql template from sql/queries/, inject the WHERE clause and
    (if applicable) a validated dimension/limit, and execute it safely.
    `dimension` is validated against an allowlist — never interpolated
    from raw user text — since SQLite doesn't support parameterizing
    identifiers (column names) the way it does values.
    """
    filters = filters or Filters()
    where_sql, params = filters.to_where_clause()

    template = _load_query(query_name)
    sql = template.replace("{where_clause}", where_sql)

    if "{dimension}" in sql:
        if dimension not in _ALLOWED_DIMENSIONS:
            raise ValueError(
                f"Invalid dimension '{dimension}'. Must be one of {_ALLOWED_DIMENSIONS}."
            )
        sql = sql.replace("{dimension}", dimension)

    if "{limit}" in sql:
        sql = sql.replace("{limit}", str(int(limit or 10)))

    return pd.read_sql_query(sql, conn, params=params)
