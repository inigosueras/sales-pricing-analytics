"""
filters.py
----------
Renders the sidebar filter controls shared by every page: which
dataset(s) to analyze, date range, country, category, segment. Returns
a populated Filters object that pages pass straight into src/metrics.py.

PERSISTENCE: every widget here uses an explicit `key=`, which Streamlit
keeps in st.session_state for the whole browser session — not just the
current page. This means selecting "Retail only" on the Overview page
and then navigating to Trends keeps that same selection, instead of each
page resetting to "all datasets" independently. This mirrors how a
synced slicer behaves in Power BI: choosing a subset filters the view,
it never deletes anything from the underlying model (that only happens
via the trash icon on the Home page).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.db import Filters, list_datasets
from src.metrics import get_filter_options


def _persisted_multiselect(label: str, options: list[str], key: str, help: str | None = None) -> list[str]:
    """
    A multiselect whose selection persists across pages via session_state,
    pruning any previously-selected values that are no longer valid
    options (e.g. a country that doesn't exist in the newly-selected
    dataset(s)).
    """
    if key not in st.session_state:
        st.session_state[key] = []
    st.session_state[key] = [v for v in st.session_state[key] if v in options]
    return st.sidebar.multiselect(label, options=options, key=key, help=help)


def render_sidebar_filters(conn) -> Filters:
    st.sidebar.header("Filters")

    datasets_df = list_datasets(conn)
    if datasets_df.empty:
        st.sidebar.info("Upload a file on the Home page to get started.")
        return Filters()

    # --- Dataset picker (persisted — see module docstring) ---
    def _short_label(row) -> str:
        base = row["industry_label"] or Path(row["dataset_name"]).stem
        return f"{base} ({row['row_count']:,} rows)"

    dataset_labels = {row["dataset_id"]: _short_label(row) for _, row in datasets_df.iterrows()}

    # Disambiguate identical labels (e.g. two uploads both tagged "Retail"
    # with the same row count) — a multiselect can't tell apart two
    # options with the same display string.
    seen: dict[str, list] = {}
    for did, label in dataset_labels.items():
        seen.setdefault(label, []).append(did)
    for label, ids in seen.items():
        if len(ids) > 1:
            for did in ids:
                dataset_labels[did] = f"{label} #{did}"

    label_to_id = {v: k for k, v in dataset_labels.items()}
    all_labels = list(dataset_labels.values())

    if "dataset_filter_selection" not in st.session_state:
        st.session_state.dataset_filter_selection = all_labels  # first visit: all selected
    else:
        # Keep previously selected labels that still exist; drop ones for
        # datasets that were removed since the last selection.
        st.session_state.dataset_filter_selection = [
            l for l in st.session_state.dataset_filter_selection if l in all_labels
        ]
        if not st.session_state.dataset_filter_selection:
            st.session_state.dataset_filter_selection = all_labels

    selected_labels = st.sidebar.multiselect(
        "Dataset(s)",
        options=all_labels,
        key="dataset_filter_selection",
        help=(
            "Filters which dataset(s) are analyzed — like a Power BI slicer. "
            "Deselecting a dataset here does NOT delete it; your selection is "
            "remembered as you move between pages. Use the 🗑️ button on the "
            "Home page to actually remove a dataset."
        ),
    )
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
        min_d = pd.to_datetime(options["min_date"]).date()
        max_d = pd.to_datetime(options["max_date"]).date()
        date_key = "date_range_filter"

        # Seed / clamp the session-state value directly (rather than also
        # passing `value=` to the widget) — passing both raises a Streamlit
        # warning about conflicting default vs. session-state assignment.
        if date_key not in st.session_state:
            st.session_state[date_key] = (min_d, max_d)
        else:
            prev = st.session_state[date_key]
            if isinstance(prev, tuple) and len(prev) == 2:
                st.session_state[date_key] = (max(prev[0], min_d), min(prev[1], max_d))
            else:
                st.session_state[date_key] = (min_d, max_d)

        date_range = st.sidebar.date_input(
            "Date range", min_value=min_d, max_value=max_d, key=date_key,
        )

    countries = _persisted_multiselect("Country", options["countries"], key="country_filter_selection")
    categories = _persisted_multiselect("Category", options["categories"], key="category_filter_selection")
    segments = _persisted_multiselect("Customer Segment", options["segments"], key="segment_filter_selection")

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
