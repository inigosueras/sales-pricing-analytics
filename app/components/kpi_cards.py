"""
kpi_cards.py
------------
Renders the main KPI row (revenue, margin %, avg ticket, units) as
Streamlit metric cards. Used at the top of the Overview page and
reused wherever a quick KPI snapshot is needed.
"""

from __future__ import annotations

import streamlit as st


def render_kpi_cards(kpis: dict) -> None:
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Revenue", f"${kpis.get('total_revenue', 0):,.0f}")
    col2.metric("Margin %", f"{kpis.get('margin_pct', 0):.1f}%")
    col3.metric("Avg Ticket", f"${kpis.get('avg_ticket', 0):,.2f}")
    col4.metric("Units Sold", f"{kpis.get('total_units', 0):,.0f}")

    col5, col6, col7 = st.columns(3)
    col5.metric("Total Margin", f"${kpis.get('total_margin', 0):,.0f}")
    col6.metric("Distinct Products", f"{kpis.get('distinct_products', 0):,.0f}")
    col7.metric("Distinct Countries", f"{kpis.get('distinct_countries', 0):,.0f}")
