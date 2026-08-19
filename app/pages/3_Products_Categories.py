from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT))

from app.components.charts import top_n_bar_chart
from app.components.filters import render_sidebar_filters
from app.components.state import get_conn, has_data
from src.metrics import get_top_n

st.set_page_config(page_title="Products & Categories", page_icon="🏆", layout="wide")
st.title("🏆 Top Products & Categories")

conn = get_conn()

if not has_data():
    st.info("No data loaded yet. Go to the Home page to upload a file or load a sample dataset.")
    st.stop()

filters = render_sidebar_filters(conn)
if not filters.dataset_ids:
    st.stop()

col1, col2 = st.columns([1, 1])
dimension = col1.radio("Rank by", options=["Product", "Category"], horizontal=True)
metric = col2.radio("Sort by", options=["revenue", "margin", "units"], horizontal=True)

top_df = get_top_n(conn, filters, dimension=dimension, limit=10)

if top_df.empty:
    st.warning("No data matches the current filters.")
    st.stop()

st.plotly_chart(
    top_n_bar_chart(top_df, value_col=metric, title=f"Top 10 {dimension}s by {metric.title()}"),
    width='stretch',
)

st.markdown("---")
st.subheader("Full Ranking Table")
display_df = top_df.rename(columns={"name": dimension}).copy()
display_df["revenue"] = display_df["revenue"].map(lambda v: f"${v:,.0f}")
display_df["margin"] = display_df["margin"].map(lambda v: f"${v:,.0f}")
display_df["margin_pct"] = display_df["margin_pct"].map(lambda v: f"{v:.1f}%")
display_df["units"] = display_df["units"].map(lambda v: f"{v:,.0f}")
st.dataframe(display_df, width='stretch', hide_index=True)
