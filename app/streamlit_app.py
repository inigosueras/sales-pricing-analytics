"""
streamlit_app.py
-----------------
Entry point of the app. Handles: file upload, validation feedback,
loading sample datasets, and a manager table to view/remove datasets
already loaded into this session.

Run with: streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from app.components.state import get_conn, has_data
from src.db import delete_dataset, list_datasets, load_dataframe
from src.transformer import run_full_pipeline
from src.validator import validate_dataframe

st.set_page_config(
    page_title="Universal Sales & Pricing Analytics Tool",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Universal Sales & Pricing Analytics Tool")
st.caption(
    "Upload a sales file with the required column structure and get a complete "
    "commercial analytics dashboard — automatically, no configuration needed."
)

conn = get_conn()

# ---------------------------------------------------------------------------
# Required schema reminder
# ---------------------------------------------------------------------------
with st.expander("📋 Required column structure", expanded=not has_data()):
    st.markdown(
        "Your CSV or Excel file must contain exactly these columns "
        "(any additional columns will be ignored):"
    )
    st.code(
        "Date | Product | Category | Country | Revenue | Quantity | Cost | Customer_Segment",
        language=None,
    )
    st.markdown(
        "- `Date`: sale date  ·  `Revenue`, `Cost`: monetary values (no negatives)  ·  "
        "`Quantity`: units sold (no zeros)\n"
        "- Text columns (`Product`, `Category`, `Country`, `Customer_Segment`) are "
        "automatically cleaned: extra spaces, casing, and near-duplicate spellings "
        "(e.g. *'Online'*, *'on-line'*, *'ONLINE '*) are merged automatically."
    )

# ---------------------------------------------------------------------------
# Sample datasets — quick start
# ---------------------------------------------------------------------------
st.subheader("Quick start with sample data")
sample_cols = st.columns(3)
samples = [
    ("Retail", "retail_sales.csv", sample_cols[0]),
    ("Pharma", "pharma_sales.csv", sample_cols[1]),
    ("Manufacturing", "manufacturing_sales.csv", sample_cols[2]),
]
for label, fname, col in samples:
    with col:
        if st.button(f"Load {label} sample", width='stretch'):
            sample_path = ROOT / "data" / "samples" / fname
            raw_df = __import__("pandas").read_csv(sample_path)
            result = validate_dataframe(raw_df)
            if result.is_valid:
                clean_df = run_full_pipeline(raw_df)
                load_dataframe(conn, clean_df, dataset_name=fname, industry_label=label)
                st.success(f"Loaded {fname} ({len(clean_df):,} rows).")
                st.rerun()
            else:
                st.error(result.summary())

st.markdown("---")

# ---------------------------------------------------------------------------
# File upload
# ---------------------------------------------------------------------------
st.subheader("Upload your own file")
industry_label = st.text_input(
    "Label for this dataset (optional)", placeholder="e.g. Retail EU, Q3 Pharma..."
)
uploaded_file = st.file_uploader("CSV or Excel file", type=["csv", "xlsx", "xls"])

if uploaded_file is not None:
    import pandas as pd

    try:
        if uploaded_file.name.lower().endswith(".csv"):
            raw_df = pd.read_csv(uploaded_file)
        else:
            raw_df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"Could not read the file: {e}")
        raw_df = None

    if raw_df is not None:
        result = validate_dataframe(raw_df)

        if result.is_valid:
            st.success(f"✅ Validation passed — {result.row_count:,} rows.")
            if result.warnings:
                with st.expander(f"⚠️ {len(result.warnings)} warning(s) (non-blocking)"):
                    for w in result.warnings:
                        st.write(f"- {w}")

            if st.button("Load into dashboard", type="primary"):
                clean_df = run_full_pipeline(raw_df)
                label = industry_label.strip() or None
                load_dataframe(conn, clean_df, dataset_name=uploaded_file.name, industry_label=label)
                st.success(f"Loaded {uploaded_file.name} ({len(clean_df):,} rows). Go to the pages on the left to explore it.")
                st.rerun()
        else:
            st.error(f"❌ Validation failed — {len(result.errors)} error(s) found. Fix these and re-upload:")
            for e in result.errors:
                st.write(f"- {e}")
            if result.warnings:
                with st.expander(f"Also see {len(result.warnings)} warning(s)"):
                    for w in result.warnings:
                        st.write(f"- {w}")

st.markdown("---")

# ---------------------------------------------------------------------------
# Dataset manager
# ---------------------------------------------------------------------------
st.subheader("Datasets loaded in this session")
datasets_df = list_datasets(conn)

if datasets_df.empty:
    st.info("No datasets loaded yet. Use the quick-start buttons or upload a file above.")
else:
    for _, row in datasets_df.iterrows():
        c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 1])
        c1.write(f"**{row['dataset_name']}**")
        c2.write(row["industry_label"] or "—")
        c3.write(f"{row['row_count']:,} rows")
        c4.write(str(row["uploaded_at"])[:19].replace("T", " "))
        if c5.button("🗑️", key=f"del_{row['dataset_id']}", help="Remove this dataset"):
            delete_dataset(conn, int(row["dataset_id"]))
            st.rerun()

    st.caption(
        "👈 Use the pages in the sidebar to explore Overview, Trends, Products & Categories, "
        "Geography, Price/Volume, and Segments. Use the filter panel on each page to select "
        "which dataset(s) to analyze."
    )
