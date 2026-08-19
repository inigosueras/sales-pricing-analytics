-- Schema for the cleaned, transformed sales dataset — MULTI-DATASET version.
-- Mirrors data/schema.py (REQUIRED_COLUMNS + DERIVED_COLUMNS).
--
-- Design: each uploaded file becomes one row in `datasets` and its rows are
-- tagged with that dataset_id in `sales_data`. Tables are created once
-- (IF NOT EXISTS) and datasets are appended, never dropped, so multiple
-- uploads can coexist and be compared/filtered side by side.

CREATE TABLE IF NOT EXISTS datasets (
    dataset_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_name   TEXT NOT NULL,        -- e.g. original filename, or user-given label
    industry_label TEXT,                 -- optional free-text tag ("Retail", "Pharma"...)
    uploaded_at    TEXT NOT NULL,        -- ISO 8601 timestamp
    row_count      INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS sales_data (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id        INTEGER NOT NULL REFERENCES datasets(dataset_id),
    Date              TEXT NOT NULL,      -- ISO 8601 (YYYY-MM-DD)
    Product           TEXT NOT NULL,
    Category          TEXT NOT NULL,
    Country           TEXT NOT NULL,
    Revenue           REAL NOT NULL,
    Quantity          REAL NOT NULL,
    Cost              REAL NOT NULL,
    Customer_Segment  TEXT NOT NULL,

    -- Derived fields (computed in src/transformer.py, written as-is)
    Margin            REAL NOT NULL,
    Margin_Pct        REAL NOT NULL,
    Avg_Price         REAL NOT NULL,
    Unit_Cost         REAL NOT NULL,
    Year              INTEGER NOT NULL,
    Quarter           TEXT NOT NULL,
    Month             INTEGER NOT NULL,
    YearMonth         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sales_dataset ON sales_data (dataset_id);
CREATE INDEX IF NOT EXISTS idx_sales_date ON sales_data (Date);
CREATE INDEX IF NOT EXISTS idx_sales_country ON sales_data (Country);
CREATE INDEX IF NOT EXISTS idx_sales_category ON sales_data (Category);
CREATE INDEX IF NOT EXISTS idx_sales_segment ON sales_data (Customer_Segment);
CREATE INDEX IF NOT EXISTS idx_sales_yearmonth ON sales_data (YearMonth);
