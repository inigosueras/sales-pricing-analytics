"""
state.py
--------
Centralizes Streamlit session state so every page shares the same SQLite
connection (with all uploaded datasets) and the same active Filters
object, without each page reinventing initialization logic.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.db import Filters, get_connection


def init_session_state() -> None:
    """Call at the top of every page. Idempotent — safe to call repeatedly."""
    if "conn" not in st.session_state:
        st.session_state.conn = get_connection(":memory:")
    if "filters" not in st.session_state:
        st.session_state.filters = Filters()
    if "active_dataset_ids" not in st.session_state:
        st.session_state.active_dataset_ids = []


def get_conn():
    init_session_state()
    return st.session_state.conn


def get_filters() -> Filters:
    init_session_state()
    return st.session_state.filters


def set_filters(filters: Filters) -> None:
    st.session_state.filters = filters


def has_data() -> bool:
    """True if at least one dataset has been uploaded this session."""
    from src.db import list_datasets
    init_session_state()
    return len(list_datasets(st.session_state.conn)) > 0
