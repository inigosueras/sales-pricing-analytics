from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT))

from app.components.charts import geo_bar_chart, geo_map_chart
from app.components.filters import render_sidebar_filters
from app.components.state import get_conn, has_data
from src.metrics import get_geo_distribution

st.set_page_config(page_title="Geography", page_icon="🌍", layout="wide")
st.title("🌍 Geographic Distribution")

conn = get_conn()

if not has_data():
    st.info("No data loaded yet. Go to the Home page to upload a file or load a sample dataset.")
    st.stop()

filters = render_sidebar_filters(conn)
if not filters.dataset_ids:
    st.stop()

geo_df = get_geo_distribution(conn, filters)

if geo_df.empty:
    st.warning("No data matches the current filters.")
    st.stop()

tab_map, tab_bar = st.tabs(["Map", "Bar Chart"])
with tab_map:
    st.plotly_chart(geo_map_chart(geo_df), width='stretch')
    st.caption(
        "The map matches countries by name — if your Country column uses non-standard "
        "labels, some countries may not render here. The Bar Chart tab always works."
    )
with tab_bar:
    st.plotly_chart(geo_bar_chart(geo_df), width='stretch')

st.markdown("---")
st.subheader("Country Breakdown")
display_df = geo_df.copy()
display_df["revenue"] = display_df["revenue"].map(lambda v: f"${v:,.0f}")
display_df["margin"] = display_df["margin"].map(lambda v: f"${v:,.0f}")
display_df["margin_pct"] = display_df["margin_pct"].map(lambda v: f"{v:.1f}%")
display_df["units"] = display_df["units"].map(lambda v: f"{v:,.0f}")
display_df["avg_price"] = display_df["avg_price"].map(lambda v: f"${v:,.2f}")
st.dataframe(display_df, width='stretch', hide_index=True)
