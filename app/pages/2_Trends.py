from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT))

from app.components.charts import trend_chart, yoy_bar_chart
from app.components.filters import render_sidebar_filters
from app.components.state import get_conn, has_data
from src.metrics import get_trend_with_yoy

st.set_page_config(page_title="Trends", page_icon="📈", layout="wide")
st.title("📈 Trends & Year-over-Year Growth")

conn = get_conn()

if not has_data():
    st.info("No data loaded yet. Go to the Home page to upload a file or load a sample dataset.")
    st.stop()

filters = render_sidebar_filters(conn)
if not filters.dataset_ids:
    st.stop()

freq_label = st.radio("Granularity", options=["Monthly", "Quarterly"], horizontal=True)
freq = "M" if freq_label == "Monthly" else "Q"

trend_df = get_trend_with_yoy(conn, filters, freq=freq)

if trend_df.empty:
    st.warning("No data matches the current filters.")
    st.stop()

st.plotly_chart(trend_chart(trend_df), width='stretch')
st.plotly_chart(yoy_bar_chart(trend_df), width='stretch')

st.markdown("---")
st.subheader("Trend Data")
display_df = trend_df.copy()
display_df["Revenue"] = display_df["Revenue"].map(lambda v: f"${v:,.0f}")
display_df["Revenue_PriorYear"] = display_df["Revenue_PriorYear"].map(
    lambda v: f"${v:,.0f}" if pd.notna(v) else "—"
)
display_df["YoY_Pct"] = display_df["YoY_Pct"].map(lambda v: f"{v:+.1f}%" if pd.notna(v) else "—")
st.dataframe(display_df, width='stretch', hide_index=True)
