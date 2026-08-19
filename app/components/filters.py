"""
filters.py
----------
Renders the sidebar filter controls shared by every page: which
dataset(s) to analyze, date range, country, category, segment. Returns
a populated Filters object that pages pass straight into src/metrics.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.db import Filters, list_datasets
from src.metrics import get_filter_options


def render_sidebar_filters(conn) -> Filters:
    st.sidebar.header("Filters")

    datasets_df = list_datasets(conn)
    if datasets_df.empty:
        st.sidebar.info("Upload a file on the Home page to get started.")
        return Filters()

    # --- Dataset picker ---
    dataset_labels = {
        row["dataset_id"]: f"{row['dataset_name']} ({row['industry_label'] or 'Unlabeled'}) — {row['row_count']} rows"
        for _, row in datasets_df.iterrows()
    }
    selected_labels = st.sidebar.multiselect(
        "Dataset(s)",
        options=list(dataset_labels.values()),
        default=list(dataset_labels.values()),
        help="Select one dataset to analyze it alone, or several to compare them.",
    )
    label_to_id = {v: k for k, v in dataset_labels.items()}
    selected_ids = [label_to_id[label] for label in selected_labels]

    base_filters = Filters(dataset_ids=selected_ids)

    if not selected_ids:
        st.sidebar.warning("Select at least one dataset.")
        return base_filters

    # --- Options scoped to the selected dataset(s) only ---
    options = get_filter_options(conn, base_filters)

    st.sidebar.markdown("---")

    date_range = None
    if options["min_date"] and options["max_date"]:
        min_d = pd_to_date(options["min_date"])
        max_d = pd_to_date(options["max_date"])
        date_range = st.sidebar.date_input(
            "Date range", value=(min_d, max_d), min_value=min_d, max_value=max_d,
        )

    countries = st.sidebar.multiselect("Country", options=options["countries"])
    categories = st.sidebar.multiselect("Category", options=options["categories"])
    segments = st.sidebar.multiselect("Customer Segment", options=options["segments"])

    date_from = date_to = None
    if date_range and isinstance(date_range, tuple) and len(date_range) == 2:
        date_from, date_to = date_range[0].isoformat(), date_range[1].isoformat()

    return Filters(
        dataset_ids=selected_ids,
        date_from=date_from,
        date_to=date_to,
        countries=countries,
        categories=categories,
        segments=segments,
    )


def pd_to_date(value: str):
    import pandas as pd
    return pd.to_datetime(value).date()
