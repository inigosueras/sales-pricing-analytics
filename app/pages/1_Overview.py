from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT))

from app.components.charts import trend_chart
from app.components.filters import render_sidebar_filters
from app.components.kpi_cards import render_kpi_cards
from app.components.state import get_conn, has_data
from src.metrics import get_kpis, get_trend_with_yoy

st.set_page_config(page_title="Overview", page_icon="📊", layout="wide")
st.title("📊 Overview")

conn = get_conn()

if not has_data():
    st.info("No data loaded yet. Go to the Home page to upload a file or load a sample dataset.")
    st.stop()

filters = render_sidebar_filters(conn)
if not filters.dataset_ids:
    st.stop()

kpis = get_kpis(conn, filters)
render_kpi_cards(kpis)

st.markdown("---")
st.subheader("Revenue Trend Snapshot")

trend_df = get_trend_with_yoy(conn, filters, freq="M")
if trend_df.empty:
    st.warning("No data matches the current filters.")
else:
    st.plotly_chart(trend_chart(trend_df), width='stretch')
    st.caption("For quarterly view, YoY growth %, and full trend breakdown, see the **Trends** page.")
