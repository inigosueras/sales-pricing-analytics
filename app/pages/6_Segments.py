from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT))

from app.components.charts import (
    dataset_comparison_chart,
    segment_donut_chart,
    segment_margin_bar_chart,
)
from app.components.filters import render_sidebar_filters
from app.components.state import get_conn, has_data
from src.metrics import compare_datasets, get_segment_analysis

st.set_page_config(page_title="Segments", page_icon="👥", layout="wide")
st.title("👥 Customer Segment Analysis")

conn = get_conn()

if not has_data():
    st.info("No data loaded yet. Go to the Home page to upload a file or load a sample dataset.")
    st.stop()

filters = render_sidebar_filters(conn)
if not filters.dataset_ids:
    st.stop()

segment_df = get_segment_analysis(conn, filters)

if segment_df.empty:
    st.warning("No data matches the current filters.")
    st.stop()

col1, col2 = st.columns(2)
col1.plotly_chart(segment_donut_chart(segment_df), width='stretch')
col2.plotly_chart(segment_margin_bar_chart(segment_df), width='stretch')

st.markdown("---")
st.subheader("Segment Breakdown")
display_df = segment_df.copy()
display_df["revenue"] = display_df["revenue"].map(lambda v: f"${v:,.0f}")
display_df["margin"] = display_df["margin"].map(lambda v: f"${v:,.0f}")
display_df["margin_pct"] = display_df["margin_pct"].map(lambda v: f"{v:.1f}%")
display_df["units"] = display_df["units"].map(lambda v: f"{v:,.0f}")
display_df["avg_ticket"] = display_df["avg_ticket"].map(lambda v: f"${v:,.2f}")
st.dataframe(display_df, width='stretch', hide_index=True)

# ---------------------------------------------------------------------------
# Dataset comparison — only meaningful with 2+ datasets selected
# ---------------------------------------------------------------------------
if len(filters.dataset_ids) >= 2:
    st.markdown("---")
    st.subheader("📊 Dataset Comparison")
    st.caption("Side-by-side KPIs for the datasets currently selected in the sidebar.")

    compare_df = compare_datasets(conn, filters)
    st.plotly_chart(dataset_comparison_chart(compare_df), width='stretch')

    display_compare = compare_df.copy()
    display_compare["revenue"] = display_compare["revenue"].map(lambda v: f"${v:,.0f}")
    display_compare["margin"] = display_compare["margin"].map(lambda v: f"${v:,.0f}")
    display_compare["margin_pct"] = display_compare["margin_pct"].map(lambda v: f"{v:.1f}%")
    display_compare["units"] = display_compare["units"].map(lambda v: f"{v:,.0f}")
    display_compare["avg_ticket"] = display_compare["avg_ticket"].map(lambda v: f"${v:,.2f}")
    st.dataframe(display_compare, width='stretch', hide_index=True)
else:
    st.info("💡 Select 2 or more datasets in the sidebar to see a side-by-side comparison here.")
