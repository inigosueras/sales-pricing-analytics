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
POSITIVE_COLOR = "#2C5F9E"
NEGATIVE_COLOR = "#C24B4B"
TEMPLATE = "plotly_white"


def _segment_color_map(segment_names: list[str]) -> dict[str, str]:
    """
    Assigns each segment a fixed color from PALETTE based on alphabetical
    order, so the same segment always gets the same color across every
    chart on the page (donut, bar, etc.) — comparing them visually only
    works if "Wholesale" is the same color everywhere.
    """
    ordered = sorted(segment_names)
    return {name: PALETTE[i % len(PALETTE)] for i, name in enumerate(ordered)}


def trend_chart(yoy_df: pd.DataFrame) -> go.Figure:
    """Line chart: revenue this period vs. same period last year."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=yoy_df["Period"], y=yoy_df["Revenue"], mode="lines+markers",
        name="Revenue", line=dict(color=PALETTE[0], width=3),
        hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=yoy_df["Period"], y=yoy_df["Revenue_PriorYear"], mode="lines+markers",
        name="Revenue (Prior Year)", line=dict(color=PALETTE[2], width=2, dash="dot"),
        hovertemplate="%{x}<br>$%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        template=TEMPLATE, title="Revenue Trend — Current vs. Prior Year",
        xaxis_title="Period", yaxis_title="Revenue", hovermode="x unified",
        yaxis_tickprefix="$", yaxis_tickformat=",.0f",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def yoy_bar_chart(yoy_df: pd.DataFrame) -> go.Figure:
    """Bar chart of YoY % growth by period, colored by positive/negative."""
    colors = [POSITIVE_COLOR if v >= 0 else NEGATIVE_COLOR for v in yoy_df["YoY_Pct"].fillna(0)]
    fig = go.Figure(go.Bar(
        x=yoy_df["Period"], y=yoy_df["YoY_Pct"], marker_color=colors,
        text=yoy_df["YoY_Pct"].map(lambda v: f"{v:+.1f}%" if pd.notna(v) else ""),
        textposition="outside",
        hovertemplate="%{x}<br>%{y:+.1f}%<extra></extra>",
    ))
    fig.update_layout(
        template=TEMPLATE, title="YoY Growth % by Period",
        xaxis_title="Period", yaxis_title="YoY %", yaxis_ticksuffix="%",
    )
    return fig


def top_n_bar_chart(df: pd.DataFrame, value_col: str = "revenue", title: str = "Top 10") -> go.Figure:
    df = df.sort_values(value_col, ascending=True)
    is_currency = value_col in ("revenue", "margin")
    text = df[value_col].map(lambda v: f"${v:,.0f}" if is_currency else f"{v:,.0f}")

    fig = go.Figure(go.Bar(
        x=df[value_col], y=df["name"], orientation="h",
        marker_color=PALETTE[0], text=text, textposition="outside",
        hovertemplate="%{y}<br>" + ("$%{x:,.0f}" if is_currency else "%{x:,.0f}") + "<extra></extra>",
    ))
    fig.update_layout(
        template=TEMPLATE, title=title,
        xaxis_title=value_col.replace("_", " ").title(), yaxis_title="",
        xaxis_tickprefix="$" if is_currency else "", xaxis_tickformat=",.0f",
        margin=dict(r=60),  # room for outside labels on the longest bar
    )
    return fig


def geo_bar_chart(geo_df: pd.DataFrame) -> go.Figure:
    df = geo_df.sort_values("revenue", ascending=True)
    fig = px.bar(
        df, x="revenue", y="Country", orientation="h",
        color="margin_pct", color_continuous_scale="Blues",
        template=TEMPLATE, title="Revenue by Country (colored by Margin %)",
    )
    fig.update_traces(hovertemplate="%{y}<br>Revenue: $%{x:,.0f}<extra></extra>")
    fig.update_layout(
        xaxis_title="Revenue", yaxis_title="",
        xaxis_tickprefix="$", xaxis_tickformat=",.0f",
        coloraxis_colorbar_title="Margin %",
    )
    return fig


def geo_map_chart(geo_df: pd.DataFrame) -> go.Figure:
    """
    Choropleth map by country name, automatically zoomed (fitbounds) to
    the region containing data — avoids a handful of tiny, hard-to-see
    markers on an otherwise empty world map when the dataset covers a
    small region (e.g. just Europe).
    """
    fig = px.choropleth(
        geo_df, locations="Country", locationmode="country names",
        color="revenue", color_continuous_scale="Blues",
        template=TEMPLATE, title="Geographic Revenue Distribution",
    )
    fig.update_traces(hovertemplate="%{location}<br>Revenue: $%{z:,.0f}<extra></extra>")
    fig.update_geos(fitbounds="locations", visible=True)
    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        coloraxis_colorbar_title="Revenue",
    )
    return fig


def price_volume_waterfall(decomp_df: pd.DataFrame, top_n: int = 8) -> go.Figure:
    """
    Grouped bar: for the top N dimension values by absolute revenue
    change, show how much of the change is Price effect vs Volume effect.
    """
    df = decomp_df.reindex(
        decomp_df["Revenue_Change"].abs().sort_values(ascending=False).index
    ).head(top_n)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Price Effect", x=df.iloc[:, 0], y=df["Price_Effect"], marker_color=PALETTE[0],
        hovertemplate="%{x}<br>Price Effect: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Volume Effect", x=df.iloc[:, 0], y=df["Volume_Effect"], marker_color=PALETTE[2],
        hovertemplate="%{x}<br>Volume Effect: $%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        template=TEMPLATE, barmode="relative", title="Price vs. Volume Effect on Revenue Change",
        xaxis_title="", yaxis_title="Revenue Impact",
        yaxis_tickprefix="$", yaxis_tickformat=",.0f",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def segment_donut_chart(segment_df: pd.DataFrame) -> go.Figure:
    color_map = _segment_color_map(segment_df["segment"].tolist())
    fig = px.pie(
        segment_df, names="segment", values="revenue", hole=0.5,
        color="segment", color_discrete_map=color_map,
        template=TEMPLATE, title="Revenue Share by Segment",
    )
    fig.update_traces(
        textinfo="percent+label",
        hovertemplate="%{label}<br>$%{value:,.0f} (%{percent})<extra></extra>",
    )
    return fig


def segment_margin_bar_chart(segment_df: pd.DataFrame) -> go.Figure:
    """
    Bar chart of margin % by segment. The x-axis is scaled to the actual
    spread of the data (not forced to start at 0) so that small but real
    differences between segments (e.g. 50.4% vs 50.7%) are visible instead
    of all bars looking identical.
    """
    df = segment_df.sort_values("margin_pct", ascending=True)
    color_map = _segment_color_map(df["segment"].tolist())
    colors = [color_map[s] for s in df["segment"]]

    values = df["margin_pct"]
    spread = values.max() - values.min()
    # Pad by 15% of the spread (or a fixed 2pp if segments are all ~equal)
    pad = max(spread * 0.4, 1.0)
    x_min = max(0, values.min() - pad)
    x_max = values.max() + pad

    fig = go.Figure(go.Bar(
        x=values, y=df["segment"], orientation="h", marker_color=colors,
        text=values.map(lambda v: f"{v:.1f}%"), textposition="outside",
        hovertemplate="%{y}<br>Margin: %{x:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        template=TEMPLATE, title="Margin % by Segment",
        xaxis_title="Margin %", yaxis_title="",
        xaxis=dict(range=[x_min, x_max], ticksuffix="%"),
    )
    return fig


def dimension_treemap(df: pd.DataFrame, dimensions: list[str]) -> go.Figure:
    """
    Treemap showing nested dimension combinations (e.g. Country > Category >
    Product), sized by revenue and colored by margin % — the visual
    equivalent of drilling down through an Excel PivotTable's row fields.
    """
    fig = px.treemap(
        df, path=[px.Constant("All")] + dimensions, values="revenue",
        color="margin_pct", color_continuous_scale="Blues",
        template=TEMPLATE, title=" / ".join(dimensions) + " — Revenue Breakdown",
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>Revenue: $%{value:,.0f}<br>Margin: %{color:.1f}%<extra></extra>",
    )
    fig.update_layout(margin=dict(t=40, l=10, r=10, b=10), coloraxis_colorbar_title="Margin %")
    return fig


def dataset_comparison_chart(compare_df: pd.DataFrame) -> go.Figure:
    """Grouped bar comparing revenue and margin % across multiple loaded datasets."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Revenue", x=compare_df["dataset_name"], y=compare_df["revenue"],
        marker_color=PALETTE[0], yaxis="y",
        hovertemplate="%{x}<br>Revenue: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        name="Margin %", x=compare_df["dataset_name"], y=compare_df["margin_pct"],
        mode="lines+markers", marker_color=NEGATIVE_COLOR, yaxis="y2",
        hovertemplate="%{x}<br>Margin: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        template=TEMPLATE, title="Dataset Comparison — Revenue & Margin %",
        yaxis=dict(title="Revenue", tickprefix="$", tickformat=",.0f"),
        yaxis2=dict(title="Margin %", overlaying="y", side="right", ticksuffix="%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig
