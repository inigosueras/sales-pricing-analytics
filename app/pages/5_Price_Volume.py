from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT))

from app.components.charts import price_volume_waterfall
from app.components.filters import render_sidebar_filters
from app.components.state import get_conn, has_data
from src.db import run_query
from src.transformer import compute_price_volume_decomposition

st.set_page_config(page_title="Price vs. Volume", page_icon="⚖️", layout="wide")
st.title("⚖️ Price vs. Volume Decomposition")
st.caption(
    "How much of the revenue change between two periods comes from selling at a "
    "different price, vs. selling a different quantity."
)

conn = get_conn()

if not has_data():
    st.info("No data loaded yet. Go to the Home page to upload a file or load a sample dataset.")
    st.stop()

filters = render_sidebar_filters(conn)
if not filters.dataset_ids:
    st.stop()

dimension = st.radio("Break down by", options=["Product", "Category", "Country"], horizontal=True)

# Pull row-level data (post-filter) to run the decomposition in pandas —
# needs individual dataset_id/date rows, not a pre-aggregated SQL result.
raw_rows = run_query(
    conn,
    "price_volume_decomposition",
    filters,
    dimension=dimension,
)

if raw_rows.empty or raw_rows["YearMonth"].nunique() < 2:
    st.warning(
        "Not enough periods in the current selection to compute a price/volume decomposition "
        "(need at least 2 distinct months)."
    )
    st.stop()

periods = sorted(raw_rows["YearMonth"].unique())
col1, col2 = st.columns(2)
prior_period = col1.selectbox("Prior period", options=periods, index=len(periods) - 2)
current_period = col2.selectbox("Current period", options=periods, index=len(periods) - 1)

# Reconstruct a row-level-equivalent frame usable by compute_price_volume_decomposition,
# which expects Revenue/Quantity/YearMonth columns keyed by the chosen dimension.
decomp_input = raw_rows.rename(columns={"dimension_value": dimension, "revenue": "Revenue", "quantity": "Quantity"})
decomp_df = compute_price_volume_decomposition(
    decomp_input, dimension=dimension, current_period=current_period, prior_period=prior_period
)

if decomp_df.empty:
    st.warning("No overlapping data between the selected periods.")
    st.stop()

st.plotly_chart(price_volume_waterfall(decomp_df), width='stretch')

st.markdown("---")
st.subheader("Decomposition Table")
display_df = decomp_df.copy()
for col in ["Revenue_t0", "Revenue_t1", "Revenue_Change", "Price_Effect", "Volume_Effect"]:
    display_df[col] = display_df[col].map(lambda v: f"${v:,.0f}")
st.dataframe(display_df, width='stretch', hide_index=True)
