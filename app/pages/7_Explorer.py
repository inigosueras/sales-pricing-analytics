from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(ROOT))

from app.components.charts import dimension_treemap
from app.components.filters import render_sidebar_filters
from app.components.state import get_conn, has_data
from src.metrics import get_multi_dimension_breakdown

st.set_page_config(page_title="Explorer", page_icon="🔎", layout="wide")
st.title("🔎 Pivot Explorer")
st.caption(
    "Combine any dimensions to explore the data, like dragging fields into an "
    "Excel PivotTable — e.g. Country + Category, or Country + Category + Product."
)

conn = get_conn()

if not has_data():
    st.info("No data loaded yet. Go to the Home page to upload a file or load a sample dataset.")
    st.stop()

filters = render_sidebar_filters(conn)
if not filters.dataset_ids:
    st.stop()

ALL_DIMENSIONS = ["Country", "Category", "Product", "Customer_Segment"]

dimensions = st.multiselect(
    "Combine dimensions (order matters — first field is the outermost grouping)",
    options=ALL_DIMENSIONS,
    default=["Category", "Product"],
    max_selections=3,
    help="Pick 1 to 3 fields to group by simultaneously.",
)

if not dimensions:
    st.warning("Select at least one dimension to build the breakdown.")
    st.stop()

col1, col2 = st.columns(2)
sort_by = col1.selectbox("Sort by", options=["revenue", "margin", "margin_pct", "units"], index=0)
limit = col2.slider("Max rows", min_value=10, max_value=200, value=50, step=10)

breakdown_df = get_multi_dimension_breakdown(conn, filters, dimensions, limit=limit)

if breakdown_df.empty:
    st.warning("No data matches the current filters.")
    st.stop()

breakdown_df = breakdown_df.sort_values(sort_by, ascending=False)

st.plotly_chart(dimension_treemap(breakdown_df, dimensions), width='stretch')

st.markdown("---")
st.subheader("Breakdown Table")
display_df = breakdown_df.copy()
display_df["revenue"] = display_df["revenue"].map(lambda v: f"${v:,.0f}")
display_df["margin"] = display_df["margin"].map(lambda v: f"${v:,.0f}")
display_df["margin_pct"] = display_df["margin_pct"].map(lambda v: f"{v:.1f}%")
display_df["units"] = display_df["units"].map(lambda v: f"{v:,.0f}")
display_df["avg_ticket"] = display_df["avg_ticket"].map(lambda v: f"${v:,.2f}")
st.dataframe(display_df, width='stretch', hide_index=True)

st.caption(
    f"Showing top {min(limit, len(breakdown_df))} combinations of "
    f"{' × '.join(dimensions)}, ranked by {sort_by}."
)
