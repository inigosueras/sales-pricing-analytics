"""
charts.py
---------
Plotly figure builders, one function per chart type, reused across
pages. Keeps chart styling consistent and pages free of chart-building
boilerplate.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

PALETTE = ["#2C5F9E", "#4C8FD1", "#7BB3E0", "#1B2A4A", "#8FA8C4", "#B5CBE0"]
TEMPLATE = "plotly_white"


def trend_chart(yoy_df: pd.DataFrame) -> go.Figure:
    """Line chart: revenue this period vs. same period last year."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=yoy_df["Period"], y=yoy_df["Revenue"], mode="lines+markers",
        name="Revenue", line=dict(color=PALETTE[0], width=3),
    ))
    fig.add_trace(go.Scatter(
        x=yoy_df["Period"], y=yoy_df["Revenue_PriorYear"], mode="lines+markers",
        name="Revenue (Prior Year)", line=dict(color=PALETTE[2], width=2, dash="dot"),
    ))
    fig.update_layout(
        template=TEMPLATE, title="Revenue Trend — Current vs. Prior Year",
        xaxis_title="Period", yaxis_title="Revenue", hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def yoy_bar_chart(yoy_df: pd.DataFrame) -> go.Figure:
    """Bar chart of YoY % growth by period, colored by positive/negative."""
    colors = [PALETTE[0] if v >= 0 else "#C24B4B" for v in yoy_df["YoY_Pct"].fillna(0)]
    fig = go.Figure(go.Bar(x=yoy_df["Period"], y=yoy_df["YoY_Pct"], marker_color=colors))
    fig.update_layout(
        template=TEMPLATE, title="YoY Growth % by Period",
        xaxis_title="Period", yaxis_title="YoY %",
    )
    return fig


def top_n_bar_chart(df: pd.DataFrame, value_col: str = "revenue", title: str = "Top 10") -> go.Figure:
    df = df.sort_values(value_col, ascending=True)
    fig = px.bar(
        df, x=value_col, y="name", orientation="h",
        color_discrete_sequence=[PALETTE[0]], template=TEMPLATE, title=title,
    )
    fig.update_layout(xaxis_title=value_col.replace("_", " ").title(), yaxis_title="")
    return fig


def geo_bar_chart(geo_df: pd.DataFrame) -> go.Figure:
    df = geo_df.sort_values("revenue", ascending=True)
    fig = px.bar(
        df, x="revenue", y="Country", orientation="h",
        color="margin_pct", color_continuous_scale="Blues",
        template=TEMPLATE, title="Revenue by Country (colored by Margin %)",
    )
    fig.update_layout(xaxis_title="Revenue", yaxis_title="")
    return fig


def geo_map_chart(geo_df: pd.DataFrame) -> go.Figure | None:
    """
    Choropleth map by country name. Plotly resolves common country names
    automatically; returns None if the dataset's country values can't be
    matched (e.g. custom/non-standard labels), so the caller can fall back
    to the bar chart instead of showing a broken empty map.
    """
    fig = px.choropleth(
        geo_df, locations="Country", locationmode="country names",
        color="revenue", color_continuous_scale="Blues",
        template=TEMPLATE, title="Geographic Revenue Distribution",
    )
    fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
    return fig


def price_volume_waterfall(decomp_df: pd.DataFrame, top_n: int = 8) -> go.Figure:
    """
    Waterfall-style grouped bar: for the top N dimension values by absolute
    revenue change, show how much of the change is Price effect vs Volume
    effect.
    """
    df = decomp_df.reindex(
        decomp_df["Revenue_Change"].abs().sort_values(ascending=False).index
    ).head(top_n)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Price Effect", x=df.iloc[:, 0], y=df["Price_Effect"], marker_color=PALETTE[0],
    ))
    fig.add_trace(go.Bar(
        name="Volume Effect", x=df.iloc[:, 0], y=df["Volume_Effect"], marker_color=PALETTE[2],
    ))
    fig.update_layout(
        template=TEMPLATE, barmode="relative", title="Price vs. Volume Effect on Revenue Change",
        xaxis_title="", yaxis_title="Revenue Impact",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def segment_donut_chart(segment_df: pd.DataFrame) -> go.Figure:
    fig = px.pie(
        segment_df, names="segment", values="revenue", hole=0.5,
        color_discrete_sequence=PALETTE, template=TEMPLATE, title="Revenue Share by Segment",
    )
    fig.update_traces(textinfo="percent+label")
    return fig


def segment_margin_bar_chart(segment_df: pd.DataFrame) -> go.Figure:
    df = segment_df.sort_values("margin_pct", ascending=True)
    fig = px.bar(
        df, x="margin_pct", y="segment", orientation="h",
        color_discrete_sequence=[PALETTE[0]], template=TEMPLATE, title="Margin % by Segment",
    )
    fig.update_layout(xaxis_title="Margin %", yaxis_title="")
    return fig


def dataset_comparison_chart(compare_df: pd.DataFrame) -> go.Figure:
    """Grouped bar comparing revenue and margin % across multiple loaded datasets."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Revenue", x=compare_df["dataset_name"], y=compare_df["revenue"],
        marker_color=PALETTE[0], yaxis="y",
    ))
    fig.add_trace(go.Scatter(
        name="Margin %", x=compare_df["dataset_name"], y=compare_df["margin_pct"],
        mode="lines+markers", marker_color="#C24B4B", yaxis="y2",
    ))
    fig.update_layout(
        template=TEMPLATE, title="Dataset Comparison — Revenue & Margin %",
        yaxis=dict(title="Revenue"),
        yaxis2=dict(title="Margin %", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig
