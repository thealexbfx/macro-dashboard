import datetime as dt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app_pages.common import calculate_summary_stats
from app_pages.market_utils import filter_by_dates
from components.research.research_page import render_research_page
from data.yahoo import get_fx_data_yahoo


# =========================================================
# DATE HELPERS
# =========================================================

def get_start_date(df, timeframe):
    end = df["date"].max()

    offsets = {
        "1D": pd.DateOffset(days=1),
        "1W": pd.DateOffset(weeks=1),
        "1M": pd.DateOffset(months=1),
        "3M": pd.DateOffset(months=3),
        "6M": pd.DateOffset(months=6),
        "1Y": pd.DateOffset(years=1),
        "3Y": pd.DateOffset(years=3),
        "5Y": pd.DateOffset(years=5),
        "10Y": pd.DateOffset(years=10),
    }

    if timeframe in offsets:
        return end - offsets[timeframe]

    return df["date"].min()


def pct_change_over(df, label):
    end = df["date"].max()

    offsets = {
        "1D": pd.DateOffset(days=1),
        "1W": pd.DateOffset(weeks=1),
        "1M": pd.DateOffset(months=1),
        "6M": pd.DateOffset(months=6),
        "1Y": pd.DateOffset(years=1),
    }

    start_date = end - offsets[label]
    past = df[df["date"] <= start_date]

    if past.empty:
        return "—"

    start_val = past["value"].iloc[-1]
    latest_val = df["value"].iloc[-1]

    if start_val == 0:
        return "—"

    change = (latest_val / start_val - 1) * 100
    sign = "+" if change > 0 else ""

    return f"{sign}{change:.2f}%"


def add_latest_label(
    fig,
    plot_df,
    value_column,
    name,
    color,
    yref="y",
    value_format=",.2f",
    suffix="",
):
    values = plot_df[["date", value_column]].dropna()
    if values.empty:
        return

    latest = values.iloc[-1]
    formatted_value = format(latest[value_column], value_format)
    fig.add_annotation(
        x=latest["date"],
        y=latest[value_column],
        yref=yref,
        text=f"{name} {formatted_value}{suffix}",
        showarrow=False,
        xanchor="left",
        xshift=8,
        font=dict(color=color, size=12),
        bgcolor="rgba(255,255,255,0.84)",
        borderpad=2,
    )


def add_average_reference(
    fig,
    plot_df,
    value_column,
    name,
    color,
    yref="y",
    value_format=",.2f",
    suffix="",
):
    values = plot_df[value_column].dropna()
    if values.empty:
        return

    average = values.mean()
    formatted_average = format(average, value_format)
    fig.add_shape(
        type="line",
        xref="paper",
        x0=0,
        x1=1,
        yref=yref,
        y0=average,
        y1=average,
        line=dict(color=color, width=1.1, dash="dash"),
        opacity=0.48,
        layer="below",
    )
    fig.add_annotation(
        xref="paper",
        x=0.01,
        yref=yref,
        y=average,
        text=f"Avg {name}: {formatted_average}{suffix}",
        showarrow=False,
        xanchor="left",
        yanchor="bottom",
        yshift=3,
        font=dict(color=color, size=10),
        bgcolor="rgba(255,255,255,0.76)",
        borderpad=1,
    )
    
    

def build_clean_market_chart(
    df,
    primary_chart_type,
    compare_df=None,
    compare_name=None,
    compare_chart_type="Line",
    primary_name="Primary",
):
    chart_df = df.copy()

    chart_df["date"] = pd.to_datetime(chart_df["date"])
    chart_df["value"] = pd.to_numeric(
        chart_df["value"],
        errors="coerce",
    )

    chart_df = (
        chart_df
        .dropna(subset=["date", "value"])
        .sort_values("date")
    )

    fig = go.Figure()

    has_compare = (
        compare_df is not None
        and compare_name not in [None, "None", "Compare +"]
    )

    y1_min = None
    y1_max = None
    y2_min = None
    y2_max = None

    def add_visible_series(
        plot_df,
        value_column,
        name,
        chart_type,
        color,
        yaxis=None,
        line_width=2.4,
        fill_opacity=0.07,
    ):
        common_args = {
            "x": plot_df["date"],
            "y": plot_df[value_column],
            "name": name,
            "hovertemplate": "%{y:,.2f}<extra></extra>",
        }

        if yaxis:
            common_args["yaxis"] = yaxis

        if chart_type == "Bar":
            fig.add_trace(
                go.Bar(
                    **common_args,
                    marker=dict(
                        color=color,
                        line=dict(width=0),
                    ),
                    opacity=0.72,
                )
            )
            return

        line_shape = "hv" if chart_type == "Step" else "linear"

        trace_args = {
            **common_args,
            "mode": "lines",
            "line": dict(
                color=color,
                width=line_width,
                shape=line_shape,
            ),
        }

        if chart_type == "Area":
            trace_args["fill"] = "tozeroy"
            trace_args["fillcolor"] = (
                f"rgba({37 if color == '#2563EB' else 22}, "
                f"{99 if color == '#2563EB' else 163}, "
                f"{235 if color == '#2563EB' else 74}, "
                f"{fill_opacity})"
            )

        fig.add_trace(go.Scatter(**trace_args))

    # -----------------------------------------------------
    # DUAL-AXIS COMPARISON
    # -----------------------------------------------------

    if has_compare:
        compare_df = compare_df.copy()

        compare_df["date"] = pd.to_datetime(compare_df["date"])
        compare_df["value"] = pd.to_numeric(
            compare_df["value"],
            errors="coerce",
        )

        compare_df = (
            compare_df
            .dropna(subset=["date", "value"])
            .sort_values("date")
        )

        merged = pd.merge(
            chart_df[["date", "value"]],
            compare_df[["date", "value"]],
            on="date",
            how="inner",
            suffixes=("_main", "_compare"),
        )

        if merged.empty:
            has_compare = False

        else:
            # Blue primary asset — right axis
            add_visible_series(
                plot_df=merged,
                value_column="value_main",
                name=primary_name,
                chart_type=primary_chart_type,
                color="#2563EB",
                yaxis="y2",
                line_width=2.5,
                fill_opacity=0.06,
            )

            # Green comparison asset — left axis
            add_visible_series(
                plot_df=merged,
                value_column="value_compare",
                name=compare_name,
                chart_type=compare_chart_type,
                color="#16A34A",
                yaxis="y",
                line_width=2.1,
                fill_opacity=0.05,
            )

            y1_min = merged["value_compare"].min()
            y1_max = merged["value_compare"].max()
            y2_min = merged["value_main"].min()
            y2_max = merged["value_main"].max()

    # -----------------------------------------------------
    # SINGLE-SERIES CHART
    # -----------------------------------------------------

    if not has_compare:
        chart_df["plot_value"] = chart_df["value"]

        if primary_chart_type == "Bar":
            fig.add_trace(
                go.Bar(
                    x=chart_df["date"],
                    y=chart_df["plot_value"],
                    name=primary_name,
                    marker=dict(
                        color="#2563EB",
                        line=dict(width=0),
                    ),
                    hovertemplate=(
                        "<b>%{x|%b %d, %Y}</b>"
                        "<br>"
                        "<span style='color:#2563EB'>●</span> "
                        f"<b>{primary_name}</b>"
                        "&nbsp;&nbsp;%{y:,.2f}"
                        "<extra></extra>"
                    ),
                )
            )

        else:
            line_shape = (
                "hv"
                if primary_chart_type == "Step"
                else "linear"
            )

            trace_args = {
                "x": chart_df["date"],
                "y": chart_df["plot_value"],
                "mode": "lines",
                "name": primary_name,
                "line": dict(
                    color="#2563EB",
                    width=2.5,
                    shape=line_shape,
                ),
                "hovertemplate": (
                    "<b>%{x|%b %d, %Y}</b>"
                    "<br>"
                    "<span style='color:#2563EB'>●</span> "
                    f"<b>{primary_name}</b>"
                    "&nbsp;&nbsp;%{y:,.2f}"
                    "<extra></extra>"
                ),
            }

            if primary_chart_type == "Area":
                trace_args["fill"] = "tozeroy"
                trace_args["fillcolor"] = "rgba(37, 99, 235, 0.07)"

            fig.add_trace(go.Scatter(**trace_args))

        y1_min = chart_df["plot_value"].min()
        y1_max = chart_df["plot_value"].max()

    def padded_range(ymin, ymax):
        if ymin is None or ymax is None:
            return None

        span = ymax - ymin if ymax != ymin else 1

        return [
            ymin - span * 0.04,
            ymax + span * 0.10,
        ]

    layout = dict(
        height=430,
        margin=dict(
            l=52,
            r=60 if has_compare else 28,
            t=42 if has_compare else 18,
            b=46,
        ),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        showlegend=has_compare,
        hovermode="x unified" if has_compare else "closest",
        hoverdistance=60,
        barmode="overlay",
        font=dict(
            family="Inter",
            size=14,
            color="#111827",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="left",
            x=0,
            font=dict(
                family="Inter",
                size=14,
                color="#111827",
            ),
            bgcolor="rgba(255,255,255,0)",
        ),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#94A3B8",
            font=dict(
                family="Inter",
                color="#111827",
                size=14,
            ),
            align="left",
            namelength=-1,
        ),
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor="#E8EDF4",
            gridwidth=1,
            showline=True,
            linecolor="#111827",
            linewidth=1.3,
            ticks="outside",
            tickcolor="#111827",
            ticklen=5,
            tickfont=dict(
                family="Inter",
                size=14,
                color="#111827",
            ),
            hoverformat="%b %d, %Y",
            showspikes=False,
            fixedrange=True,
        ),
        yaxis=dict(
            title="",
            range=padded_range(y1_min, y1_max),
            showgrid=True,
            gridcolor="#E8EDF4",
            gridwidth=1,
            zeroline=False,
            showline=True,
            linecolor="#111827",
            linewidth=1.3,
            ticks="outside",
            tickcolor="#111827",
            ticklen=5,
            tickfont=dict(
                family="Inter",
                size=14,
                color="#111827",
            ),
            tickformat=",.0f",
            fixedrange=True,
        ),
    )

    if has_compare:
        layout["yaxis2"] = dict(
            title="",
            range=padded_range(y2_min, y2_max),
            overlaying="y",
            side="right",
            showgrid=False,
            zeroline=False,
            showline=True,
            linecolor="#111827",
            linewidth=1.3,
            ticks="outside",
            tickcolor="#111827",
            ticklen=5,
            tickfont=dict(
                family="Inter",
                size=14,
                color="#111827",
            ),
            tickformat=",.0f",
            fixedrange=True,
        )

    fig.update_layout(**layout)

    if has_compare:
        add_average_reference(
            fig, merged, "value_main", primary_name, "#2563EB", yref="y2"
        )
        add_average_reference(
            fig, merged, "value_compare", compare_name, "#16A34A", yref="y"
        )
        add_latest_label(
            fig, merged, "value_main", primary_name, "#2563EB", yref="y2"
        )
        add_latest_label(
            fig, merged, "value_compare", compare_name, "#16A34A", yref="y"
        )
    else:
        add_average_reference(
            fig, chart_df, "plot_value", primary_name, "#2563EB"
        )
        add_latest_label(
            fig, chart_df, "plot_value", primary_name, "#2563EB"
        )

    return fig


def build_percentage_change_chart(
    df,
    primary_chart_type,
    compare_df,
    compare_name,
    compare_chart_type="Line",
    primary_name="Primary",
):
    """
    Compare two assets by cumulative percentage change from the first
    common observation in the selected date range.
    """
    primary_df = df[["date", "value"]].copy()
    secondary_df = compare_df[["date", "value"]].copy()

    primary_df["date"] = pd.to_datetime(primary_df["date"])
    secondary_df["date"] = pd.to_datetime(secondary_df["date"])

    primary_df["value"] = pd.to_numeric(
        primary_df["value"],
        errors="coerce",
    )
    secondary_df["value"] = pd.to_numeric(
        secondary_df["value"],
        errors="coerce",
    )

    primary_df = (
        primary_df
        .dropna(subset=["date", "value"])
        .sort_values("date")
    )
    secondary_df = (
        secondary_df
        .dropna(subset=["date", "value"])
        .sort_values("date")
    )

    merged = pd.merge(
        primary_df,
        secondary_df,
        on="date",
        how="inner",
        suffixes=("_main", "_compare"),
    )

    merged = merged[
        (merged["value_main"] != 0)
        & (merged["value_compare"] != 0)
    ].copy()

    if merged.empty:
        return go.Figure()

    primary_start = merged["value_main"].iloc[0]
    compare_start = merged["value_compare"].iloc[0]

    merged["primary_pct"] = (
        (
            merged["value_main"] / primary_start
            - 1
        )
        * 100
    ).round(2)

    merged["compare_pct"] = (
        (
            merged["value_compare"] / compare_start
            - 1
        )
        * 100
    ).round(2)

    fig = go.Figure()

    def add_series(
        value_column,
        name,
        chart_type,
        color,
        fillcolor,
        line_width,
    ):
        if chart_type == "Bar":
            fig.add_trace(
                go.Bar(
                    x=merged["date"],
                    y=merged[value_column],
                    name=name,
                    marker=dict(
                        color=color,
                        line=dict(width=0),
                    ),
                    opacity=0.72,
                    hovertemplate="%{y:+.2f}%<extra></extra>",
                )
            )
            return

        line_shape = "hv" if chart_type == "Step" else "linear"

        trace_args = {
            "x": merged["date"],
            "y": merged[value_column],
            "mode": "lines",
            "name": name,
            "line": dict(
                color=color,
                width=line_width,
                shape=line_shape,
            ),
            "hovertemplate": "%{y:+.2f}%<extra></extra>",
        }

        if chart_type == "Area":
            trace_args["fill"] = "tozeroy"
            trace_args["fillcolor"] = fillcolor

        fig.add_trace(go.Scatter(**trace_args))

    add_series(
        value_column="primary_pct",
        name=primary_name,
        chart_type=primary_chart_type,
        color="#2563EB",
        fillcolor="rgba(37, 99, 235, 0.07)",
        line_width=2.5,
    )

    add_series(
        value_column="compare_pct",
        name=compare_name,
        chart_type=compare_chart_type,
        color="#16A34A",
        fillcolor="rgba(22, 163, 74, 0.06)",
        line_width=2.1,
    )

    combined_values = pd.concat(
        [
            merged["primary_pct"],
            merged["compare_pct"],
        ],
        ignore_index=True,
    )

    ymin = combined_values.min()
    ymax = combined_values.max()
    span = ymax - ymin if ymax != ymin else 1

    fig.update_layout(
        height=430,
        margin=dict(
            l=58,
            r=28,
            t=42,
            b=46,
        ),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        showlegend=True,
        hovermode="x unified",
        hoverdistance=60,
        barmode="overlay",
        font=dict(
            family="Inter",
            size=14,
            color="#111827",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="left",
            x=0,
            font=dict(
                family="Inter",
                size=14,
                color="#111827",
            ),
            bgcolor="rgba(255,255,255,0)",
        ),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#94A3B8",
            font=dict(
                family="Inter",
                color="#111827",
                size=14,
            ),
            align="left",
            namelength=-1,
        ),
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor="#E8EDF4",
            gridwidth=1,
            showline=True,
            linecolor="#111827",
            linewidth=1.3,
            ticks="outside",
            tickcolor="#111827",
            ticklen=5,
            tickfont=dict(
                family="Inter",
                size=14,
                color="#111827",
            ),
            hoverformat="%b %d, %Y",
            showspikes=False,
            fixedrange=True,
        ),
        yaxis=dict(
            title="Percentage change",
            range=[
                ymin - span * 0.08,
                ymax + span * 0.12,
            ],
            showgrid=True,
            gridcolor="#E8EDF4",
            gridwidth=1,
            zeroline=True,
            zerolinecolor="#94A3B8",
            zerolinewidth=1.2,
            showline=True,
            linecolor="#111827",
            linewidth=1.3,
            ticks="outside",
            tickcolor="#111827",
            ticklen=5,
            tickfont=dict(
                family="Inter",
                size=14,
                color="#111827",
            ),
            ticksuffix="%",
            tickformat="+.2f",
            fixedrange=True,
        ),
    )

    fig.add_annotation(
        xref="paper",
        yref="y",
        x=0.01,
        y=0,
        text="Above 0% = gain · Below 0% = loss",
        showarrow=False,
        yshift=12,
        font=dict(color="#64748B", size=11),
        bgcolor="rgba(255,255,255,0.80)",
    )

    add_average_reference(
        fig,
        merged,
        "primary_pct",
        primary_name,
        "#2563EB",
        value_format="+.2f",
        suffix="%",
    )
    add_average_reference(
        fig,
        merged,
        "compare_pct",
        compare_name,
        "#16A34A",
        value_format="+.2f",
        suffix="%",
    )
    add_latest_label(
        fig,
        merged,
        "primary_pct",
        primary_name,
        "#2563EB",
        value_format="+.2f",
        suffix="%",
    )
    add_latest_label(
        fig,
        merged,
        "compare_pct",
        compare_name,
        "#16A34A",
        value_format="+.2f",
        suffix="%",
    )

    return fig


def prepare_comparison_data(df, compare_df):
    primary = df[["date", "value"]].copy()
    secondary = compare_df[["date", "value"]].copy()

    for frame in (primary, secondary):
        frame["date"] = pd.to_datetime(frame["date"])
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        frame.dropna(subset=["date", "value"], inplace=True)
        frame.sort_values("date", inplace=True)

    return pd.merge(
        primary,
        secondary,
        on="date",
        how="inner",
        suffixes=("_main", "_compare"),
    )


def build_analysis_chart(series, y_title, percent_axis=False, zero_line=False):
    fig = go.Figure()
    colors = ["#2563EB", "#16A34A"]
    fills = ["rgba(37, 99, 235, 0.07)", "rgba(22, 163, 74, 0.06)"]

    for index, item in enumerate(series):
        plot_df = item["df"].dropna(subset=[item["column"]])
        chart_type = item.get("chart_type", "Line")
        color = colors[index % len(colors)]
        hover_template = (
            "%{y:+.2f}%<extra></extra>"
            if percent_axis
            else "%{y:,.2f}<extra></extra>"
        )

        if chart_type == "Bar":
            fig.add_trace(
                go.Bar(
                    x=plot_df["date"],
                    y=plot_df[item["column"]],
                    name=item["name"],
                    marker=dict(color=color, line=dict(width=0)),
                    opacity=0.72,
                    hovertemplate=hover_template,
                )
            )
            continue

        trace_args = {
            "x": plot_df["date"],
            "y": plot_df[item["column"]],
            "mode": "lines",
            "name": item["name"],
            "line": dict(
                color=color,
                width=2.5 if index == 0 else 2.1,
                shape="hv" if chart_type == "Step" else "linear",
            ),
            "hovertemplate": hover_template,
        }

        if chart_type == "Area":
            trace_args["fill"] = "tozeroy"
            trace_args["fillcolor"] = fills[index % len(fills)]

        fig.add_trace(go.Scatter(**trace_args))

    values = pd.concat(
        [item["df"][item["column"]].dropna() for item in series],
        ignore_index=True,
    )
    ymin = values.min() if not values.empty else 0
    ymax = values.max() if not values.empty else 1
    span = ymax - ymin if ymax != ymin else max(abs(ymax), 1)

    fig.update_layout(
        height=430,
        margin=dict(l=58, r=28, t=42 if len(series) > 1 else 18, b=46),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        showlegend=len(series) > 1,
        hovermode="x unified" if len(series) > 1 else "closest",
        hoverdistance=60,
        barmode="overlay",
        font=dict(family="Inter", size=14, color="#111827"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.03,
            xanchor="left",
            x=0,
            font=dict(family="Inter", size=14, color="#111827"),
            bgcolor="rgba(255,255,255,0)",
        ),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            bordercolor="#94A3B8",
            font=dict(family="Inter", color="#111827", size=14),
            align="left",
            namelength=-1,
        ),
        xaxis=dict(
            title="",
            showgrid=True,
            gridcolor="#E8EDF4",
            showline=True,
            linecolor="#111827",
            linewidth=1.3,
            ticks="outside",
            tickcolor="#111827",
            ticklen=5,
            tickfont=dict(family="Inter", size=14, color="#111827"),
            hoverformat="%b %d, %Y",
            fixedrange=True,
        ),
        yaxis=dict(
            title=y_title,
            range=[ymin - span * 0.08, ymax + span * 0.12],
            showgrid=True,
            gridcolor="#E8EDF4",
            zeroline=zero_line,
            zerolinecolor="#94A3B8",
            zerolinewidth=1.2,
            showline=True,
            linecolor="#111827",
            linewidth=1.3,
            ticks="outside",
            tickcolor="#111827",
            ticklen=5,
            tickfont=dict(family="Inter", size=14, color="#111827"),
            ticksuffix="%" if percent_axis else "",
            tickformat="+.2f" if percent_axis else ",.2f",
            fixedrange=True,
        ),
    )

    for index, item in enumerate(series):
        color = colors[index % len(colors)]
        value_format = item.get(
            "value_format",
            "+.2f" if percent_axis else ",.2f",
        )
        suffix = "%" if percent_axis else ""
        add_average_reference(
            fig,
            item["df"],
            item["column"],
            item["name"],
            color,
            value_format=value_format,
            suffix=suffix,
        )
        add_latest_label(
            fig,
            item["df"],
            item["column"],
            item["name"],
            color,
            value_format=value_format,
            suffix=suffix,
        )
    return fig


def build_ratio_chart(df, compare_df, primary_name, compare_name, chart_type):
    merged = prepare_comparison_data(df, compare_df)
    merged = merged[merged["value_compare"] != 0].copy()
    merged["ratio"] = merged["value_main"] / merged["value_compare"]
    fig = build_analysis_chart(
        [{
            "df": merged,
            "column": "ratio",
            "name": f"{primary_name} / {compare_name}",
            "chart_type": chart_type,
            "value_format": ",.4f",
        }],
        y_title=f"{primary_name} / {compare_name}",
    )
    return fig


def build_rolling_correlation_chart(df, compare_df, primary_name, compare_name):
    merged = prepare_comparison_data(df, compare_df)
    merged["main_return"] = merged["value_main"].pct_change()
    merged["compare_return"] = merged["value_compare"].pct_change()
    merged["correlation"] = merged["main_return"].rolling(60).corr(
        merged["compare_return"]
    )
    fig = build_analysis_chart(
        [{
            "df": merged,
            "column": "correlation",
            "name": f"{primary_name} vs {compare_name} (60D)",
            "chart_type": "Line",
        }],
        y_title="60-day rolling correlation",
        zero_line=True,
    )
    fig.update_yaxes(range=[-1.05, 1.05], tickformat="+.2f")
    for value, label in ((0.5, "Positive"), (0.0, "Neutral"), (-0.5, "Inverse")):
        fig.add_hline(
            y=value,
            line_dash="dot" if value else "solid",
            line_color="#CBD5E1" if value else "#94A3B8",
            line_width=1,
            annotation_text=label,
            annotation_position="top left",
            annotation_font=dict(color="#64748B", size=11),
        )
    return fig


def build_drawdown_chart(
    df,
    compare_df,
    primary_name,
    compare_name,
    primary_chart_type,
    compare_chart_type,
):
    merged = prepare_comparison_data(df, compare_df)
    merged["primary_drawdown"] = (
        merged["value_main"] / merged["value_main"].cummax() - 1
    ) * 100
    merged["compare_drawdown"] = (
        merged["value_compare"] / merged["value_compare"].cummax() - 1
    ) * 100
    fig = build_analysis_chart(
        [
            {
                "df": merged,
                "column": "primary_drawdown",
                "name": primary_name,
                "chart_type": primary_chart_type,
            },
            {
                "df": merged,
                "column": "compare_drawdown",
                "name": compare_name,
                "chart_type": compare_chart_type,
            },
        ],
        y_title="Drawdown",
        percent_axis=True,
        zero_line=True,
    )
    fig.add_annotation(
        xref="paper",
        yref="y",
        x=0.01,
        y=0,
        text="0% = selected-period high",
        showarrow=False,
        yshift=12,
        font=dict(color="#64748B", size=11),
        bgcolor="rgba(255,255,255,0.80)",
    )
    return fig


def build_rolling_volatility_chart(
    df,
    compare_df,
    primary_name,
    compare_name,
    primary_chart_type,
    compare_chart_type,
):
    merged = prepare_comparison_data(df, compare_df)
    merged["primary_volatility"] = (
        merged["value_main"]
        .pct_change()
        .rolling(30)
        .std()
        * (252 ** 0.5)
        * 100
    ).round(2)

    merged["compare_volatility"] = (
        merged["value_compare"]
        .pct_change()
        .rolling(30)
        .std()
        * (252 ** 0.5)
        * 100
    ).round(2)
    fig = build_analysis_chart(
        [
            {
                "df": merged,
                "column": "primary_volatility",
                "name": primary_name,
                "chart_type": primary_chart_type,
            },
            {
                "df": merged,
                "column": "compare_volatility",
                "name": compare_name,
                "chart_type": compare_chart_type,
            },
        ],
        y_title="30-day annualized volatility",
        percent_axis=True,
    )
    return fig

# =========================================================
# PAGE
# =========================================================

def render_market_page(
    market_map,
    category_map,
    compare_map,
    page_key,
    asset_label,
):
    def key(name):
        return f"{page_key}_{name}"

    st.markdown(
        """
        <style>
        /* Keep the complete tool label visible. */
        .st-key-commodity_chart_tool {
            min-width: 230px !important;
        }

        .st-key-commodity_chart_tool div[data-testid="stSelectbox"],
        .st-key-commodity_chart_tool div[data-baseweb="select"] {
            width: 100% !important;
        }

        .ml-chart-explanation {
            margin-top: 0.7rem;
            color: #64748B;
            font-size: 0.88rem;
            line-height: 1.5;
            max-width: 980px;
        }

        .ml-chart-insight-label {
            margin-top: 0.8rem;
            color: #94A3B8;
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.11em;
        }

        .ml-chart-insight {
            margin-top: 0.18rem;
            margin-bottom: 0.35rem;
            padding: 0.62rem 0.78rem;
            border-left: 3px solid #2563EB;
            border-radius: 0 7px 7px 0;
            background: #F8FAFC;
            color: #334155;
            font-size: 0.9rem;
            line-height: 1.5;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # =========================================================
    # COMMODITY HEADER
    # =========================================================

    header_select_col, header_title_col, header_spacer_col = st.columns(
        [2.2, 5.6, 2.2],
        gap="medium",
    )

    with header_select_col:
        st.markdown(
            f"<div class='ml-commodity-select-label'>SELECT {asset_label.upper()}</div>",
            unsafe_allow_html=True,
        )

        indicator = st.selectbox(
            f"Select {asset_label}",
            list(market_map.keys()),
            key=key("indicator"),
            label_visibility="collapsed",
        )

    meta = market_map[indicator]

    with header_title_col:
        st.markdown(
            f"""
            <div class="ml-commodity-title-wrap">
                <div class="ml-commodity-title">{indicator}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with header_spacer_col:
        st.empty()

    st.markdown(
        f"""
        <div class="ml-commodity-description">
            {meta["description"]}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "data_func" in meta:
        df = meta["data_func"]().dropna()
    elif "ticker" in meta:
        df = get_fx_data_yahoo(
            meta["ticker"],
            start_date=dt.date(1990, 1, 1),
            end_date=dt.date.today(),
        ).dropna()
    else:
        st.error("No data source configured for this market.")
        st.stop()

    if df.empty:
        st.error("No data available.")
        st.stop()

    df["date"] = pd.to_datetime(df["date"])

    df["value"] = pd.to_numeric(
        df["value"],
        errors="coerce",
    )

    df = (
        df
        .dropna(subset=["date", "value"])
        .sort_values("date")
    )

    timeframe = st.session_state.get(
        key("timeframe"),
        "1Y",
    )

    primary_chart_type = st.session_state.get(
        key("primary_chart_type"),
        "Line",
    )

    compare_chart_type = st.session_state.get(
        key("compare_chart_type"),
        "Line",
    )

    if key("compare_selected") not in st.session_state:
        st.session_state[key("compare_selected")] = (
            st.session_state.get(key("compare"), "Compare +")
        )

    if key("tool_selected") not in st.session_state:
        st.session_state[key("tool_selected")] = (
            st.session_state.get(key("chart_tool"), "Price")
        )

    compare_asset = st.session_state[key("compare_selected")]
    chart_tool = st.session_state[key("tool_selected")]

    # -----------------------------------------------------
    # TIMEFRAME CALLBACK
    # -----------------------------------------------------

    def reset_custom_range_from_timeframe():
        st.session_state[key("use_custom_range")] = False

    def sync_compare_selection():
        selected_compare = st.session_state[key("compare")]
        st.session_state[key("compare_selected")] = selected_compare

        compare_type_key = (
            key(f"compare_chart_type_{selected_compare}")
        )
        if compare_type_key in st.session_state:
            st.session_state[key("compare_chart_type")] = (
                st.session_state[compare_type_key]
            )

    def sync_tool_selection():
        st.session_state[key("tool_selected")] = (
            st.session_state[key("chart_tool")]
        )

    def sync_compare_chart_type(widget_key):
        st.session_state[key("compare_chart_type")] = (
            st.session_state[widget_key]
        )

    # -----------------------------------------------------
    # TOOLBAR
    # -----------------------------------------------------

    def render_chart_controls():
        default_end = df["date"].max().date()

        default_start = max(
            df["date"].min().date(),
            (
                df["date"].max()
                - pd.DateOffset(years=1)
            ).date(),
        )

        has_active_compare = compare_asset != "Compare +"

        # =====================================================
        # TOP ROW: TIMEFRAME, DATE, COMPARE
        # =====================================================

        timeframe_col, date_col, compare_col = st.columns(
            [6.2, 0.9, 2.1],
            gap="small",
        )

        with timeframe_col:
            st.segmented_control(
                "Timeframe",
                [
                    "1D",
                    "1W",
                    "1M",
                    "3M",
                    "6M",
                    "1Y",
                    "3Y",
                    "5Y",
                    "10Y",
                    "MAX",
                ],
                key=key("timeframe"),
                default="1Y",
                label_visibility="collapsed",
                on_change=reset_custom_range_from_timeframe,
            )

        with date_col:
            latest_available_date = df["date"].max().date()
            earliest_available_date = df["date"].min().date()

            saved_start = st.session_state.get(
                key("custom_start"),
                default_start,
            )

            saved_end = st.session_state.get(
                key("custom_end"),
                latest_available_date,
            )

            saved_start = max(
                saved_start,
                earliest_available_date,
            )

            saved_end = min(
                saved_end,
                latest_available_date,
            )

            saved_start = min(
                saved_start,
                saved_end,
            )

            with st.popover(
                "Date",
                use_container_width=True,
            ):
                custom_dates = st.date_input(
                    "",
                    value=(
                        saved_start,
                        saved_end,
                    ),
                    min_value=earliest_available_date,
                    max_value=latest_available_date,
                    key=key("custom_dates"),
                    label_visibility="collapsed",
                )

                if (
                    isinstance(custom_dates, (tuple, list))
                    and len(custom_dates) == 2
                ):
                    custom_start, custom_end = custom_dates

                    custom_start = max(
                        custom_start,
                        earliest_available_date,
                    )

                    custom_end = min(
                        custom_end,
                        latest_available_date,
                    )

                    if custom_start <= custom_end:
                        if st.button(
                            "Apply range",
                            key=key("apply_custom_range"),
                            use_container_width=True,
                        ):
                            st.session_state[
                                key("custom_start")
                            ] = custom_start

                            st.session_state[
                                key("custom_end")
                            ] = custom_end

                            st.session_state[
                                key("use_custom_range")
                            ] = True

                            st.rerun()

                if st.button(
                    "Reset",
                    key=key("reset_custom_range"),
                    use_container_width=True,
                ):
                    st.session_state[
                        key("use_custom_range")
                    ] = False

                    st.session_state[
                        key("custom_start")
                    ] = default_start

                    st.session_state[
                        key("custom_end")
                    ] = latest_available_date

                    st.rerun()

        with compare_col:
            st.selectbox(
                "Compare",
                list(compare_map.keys()),
                key=key("compare"),
                label_visibility="collapsed",
                on_change=sync_compare_selection,
            )

        # =====================================================
        # SECOND ROW: CHART TYPES AND TOOLS
        # =====================================================

        st.markdown(
            "<div class='ml-chart-type-row-label'>Chart display</div>",
            unsafe_allow_html=True,
        )

        if has_active_compare:
            (
                primary_type_col,
                compare_type_col,
                tool_col,
                spacer_col,
            ) = st.columns(
                [2.0, 2.0, 2.6, 2.0],
                gap="small",
            )

            with primary_type_col:
                st.selectbox(
                    f"{indicator} chart type",
                    ["Line", "Area", "Bar", "Step"],
                    key=key("primary_chart_type"),
                    format_func=lambda value: f"{indicator}: {value}",
                    label_visibility="collapsed",
                )

            with compare_type_col:
                selected_compare = compare_asset

                compare_type_key = (
                    key(f"compare_chart_type_{selected_compare}")
                )

                if compare_type_key not in st.session_state:
                    st.session_state[compare_type_key] = compare_chart_type

                st.selectbox(
                    f"{selected_compare} chart type",
                    ["Line", "Area", "Bar", "Step"],
                    key=compare_type_key,
                    format_func=lambda value: (
                        f"{selected_compare}: {value}"
                    ),
                    label_visibility="collapsed",
                    on_change=sync_compare_chart_type,
                    args=(compare_type_key,),
                )

            with tool_col:
                st.selectbox(
                    "Comparison tool",
                    [
                        "Price",
                        "Percentage Change",
                        "Ratio",
                        "Rolling Correlation",
                        "Drawdown",
                        "Rolling Volatility",
                    ],
                    key=key("chart_tool"),
                    format_func=lambda value: f"Tool: {value}",
                    label_visibility="collapsed",
                    on_change=sync_tool_selection,
                )

        else:
            # Analytical tools currently require a comparison asset.
            if st.session_state.get(
                key("chart_tool"),
                "Price",
            ) != "Price":
                st.session_state[key("chart_tool")] = "Price"

            st.session_state[key("tool_selected")] = "Price"

            primary_type_col, tool_col, spacer_col = st.columns(
                [2.0, 2.6, 4.0],
                gap="small",
            )

            with primary_type_col:
                st.selectbox(
                    f"{indicator} chart type",
                    ["Line", "Area", "Bar", "Step"],
                    key=key("primary_chart_type"),
                    format_func=lambda value: f"{indicator}: {value}",
                    label_visibility="collapsed",
                )

            with tool_col:
                st.selectbox(
                    "Comparison tool",
                    ["Price"],
                    key=key("chart_tool"),
                    format_func=lambda value: f"Tool: {value}",
                    label_visibility="collapsed",
                    disabled=True,
                )

        st.markdown(
            f"""
            <div class="ml-chart-explanation">
                {tool_description}
            </div>
            <div class="ml-chart-insight-label">CURRENT VIEW</div>
            <div class="ml-chart-insight">
                {period_insight}
            </div>
            """,
            unsafe_allow_html=True,
        )

    # -----------------------------------------------------
    # DATE FILTER
    # -----------------------------------------------------

    use_custom_range = st.session_state.get(
        key("use_custom_range"),
        False,
    )

    latest_data_timestamp = df["date"].max()

    if use_custom_range:
        start_date = pd.Timestamp(
            st.session_state.get(
                key("custom_start"),
                df["date"].min().date(),
            )
        )

        requested_end = pd.Timestamp(
            st.session_state.get(
                key("custom_end"),
                latest_data_timestamp.date(),
            )
        )

        end_date = min(
            requested_end,
            latest_data_timestamp,
        )
    else:
        start_date = get_start_date(
            df,
            timeframe,
        )

        end_date = latest_data_timestamp

    df_filtered = filter_by_dates(
        df,
        start_date,
        end_date,
    )

    # -----------------------------------------------------
    # COMPARISON DATA
    # -----------------------------------------------------

    compare_df = None

    if compare_asset != "Compare +":
        compare_source = compare_map.get(compare_asset)

        if callable(compare_source):
            compare_df = compare_source().dropna()
        elif compare_source:
            compare_df = get_fx_data_yahoo(
                compare_source,
                start_date=dt.date(1990, 1, 1),
                end_date=dt.date.today(),
            ).dropna()

            compare_df["date"] = pd.to_datetime(
                compare_df["date"]
            )

            compare_df["value"] = pd.to_numeric(
                compare_df["value"],
                errors="coerce",
            )

            compare_df = (
                compare_df
                .dropna(subset=["date", "value"])
                .sort_values("date")
            )

            compare_df = filter_by_dates(
                compare_df,
                start_date,
                end_date,
            )

    has_comparison_data = (
        compare_df is not None
        and compare_asset != "Compare +"
        and not compare_df.empty
    )

    tool_descriptions = {
        "Price": (
            "Compares both assets in their original units using separate axes. "
            "Focus on whether they move together or diverge."
            if has_comparison_data
            else "Shows the asset's closing value over the selected period. "
            "Use the range and trend to place the latest reading in context."
        ),
        "Percentage Change": (
            "Shows cumulative performance from the beginning of the selected "
            "period. Both series start at 0%."
        ),
        "Ratio": (
            f"Shows how many units of {compare_asset} equal one unit of "
            f"{indicator}. A rising line means {indicator} is outperforming "
            f"{compare_asset}."
        ),
        "Rolling Correlation": (
            "Measures how similarly the assets' daily returns moved over the "
            "previous 60 observations. +1 means together, 0 means no consistent "
            "relationship, and -1 means opposite."
        ),
        "Drawdown": (
            "Shows how far each asset is below its highest value reached during "
            "the selected period."
        ),
        "Rolling Volatility": (
            "Estimates each asset's recent annualized price variability over 30 "
            "observations. A rising line indicates larger recent price swings."
        ),
    }
    tool_description = tool_descriptions.get(chart_tool, tool_descriptions["Price"])

    period_insight = "Select a comparison asset to unlock relative analysis."
    primary_values = df_filtered["value"].dropna()

    if chart_tool == "Price" and not primary_values.empty:
        start_value = primary_values.iloc[0]
        end_value = primary_values.iloc[-1]
        period_return = (end_value / start_value - 1) * 100 if start_value else 0
        direction = "rose" if period_return >= 0 else "fell"
        period_insight = (
            f"Period move: {indicator} {direction} from {start_value:,.2f} to "
            f"{end_value:,.2f}, a {abs(period_return):.2f}% move. Its highest "
            f"close was {primary_values.max():,.2f} and its lowest was "
            f"{primary_values.min():,.2f}."
        )

    if has_comparison_data and chart_tool != "Price":
        insight_df = prepare_comparison_data(df_filtered, compare_df)
        period_insight = (
            "There is not enough common history in the selected window to "
            "calculate a reliable current reading."
        )

        if chart_tool == "Percentage Change" and not insight_df.empty:
            primary_return = (
                insight_df["value_main"].iloc[-1]
                / insight_df["value_main"].iloc[0]
                - 1
            ) * 100
            compare_return = (
                insight_df["value_compare"].iloc[-1]
                / insight_df["value_compare"].iloc[0]
                - 1
            ) * 100
            leader = indicator if primary_return >= compare_return else compare_asset
            difference = abs(primary_return - compare_return)
            period_insight = (
                f"Period summary: {indicator} returned {primary_return:+.2f}%, "
                f"while {compare_asset} returned {compare_return:+.2f}%. "
                f"{leader} outperformed by {difference:.2f} percentage points."
            )

        elif chart_tool == "Ratio":
            valid = insight_df[insight_df["value_compare"] != 0].copy()
            valid["ratio"] = valid["value_main"] / valid["value_compare"]
            if not valid.empty:
                current_ratio = valid["ratio"].iloc[-1]
                average_ratio = valid["ratio"].mean()
                relative_word = "above" if current_ratio >= average_ratio else "below"
                performer = indicator if current_ratio >= average_ratio else compare_asset
                period_insight = (
                    f"Relative performance: The {indicator}/{compare_asset} ratio "
                    f"is {current_ratio:,.4f}, {relative_word} its selected-period "
                    f"average of {average_ratio:,.4f}, indicating {performer} has "
                    "recently outperformed on this relative measure."
                )

        elif chart_tool == "Rolling Correlation":
            correlation = (
                insight_df["value_main"].pct_change().rolling(60).corr(
                    insight_df["value_compare"].pct_change()
                ).dropna()
            )
            if not correlation.empty:
                current = correlation.iloc[-1]
                previous = correlation.iloc[-22] if len(correlation) >= 22 else correlation.iloc[0]
                magnitude = abs(current)
                strength = (
                    "strongly" if magnitude >= 0.70
                    else "moderately" if magnitude >= 0.40
                    else "weakly" if magnitude >= 0.20
                    else "minimally"
                )
                direction = "inverse" if current < 0 else "positive"
                change_word = "strengthened" if abs(current) > abs(previous) else "weakened"
                period_insight = (
                    f"Current relationship: The 60-observation correlation is "
                    f"{current:+.2f}, indicating a {strength} {direction} relationship. "
                    f"It has {change_word} from {previous:+.2f} about one month ago."
                )

        elif chart_tool == "Drawdown" and not insight_df.empty:
            primary_dd = (
                insight_df["value_main"] / insight_df["value_main"].cummax() - 1
            ) * 100
            compare_dd = (
                insight_df["value_compare"]
                / insight_df["value_compare"].cummax()
                - 1
            ) * 100
            period_insight = (
                f"Current position: {indicator} is {abs(primary_dd.iloc[-1]):.2f}% "
                f"below its period high, versus {abs(compare_dd.iloc[-1]):.2f}% for "
                f"{compare_asset}. Their largest declines were "
                f"{abs(primary_dd.min()):.2f}% and {abs(compare_dd.min()):.2f}%, "
                "respectively."
            )

        elif chart_tool == "Rolling Volatility":
            primary_vol = (
                insight_df["value_main"].pct_change().rolling(30).std()
                * (252 ** 0.5) * 100
            ).dropna()
            compare_vol = (
                insight_df["value_compare"].pct_change().rolling(30).std()
                * (252 ** 0.5) * 100
            ).dropna()
            if not primary_vol.empty and not compare_vol.empty:
                riskier = indicator if primary_vol.iloc[-1] >= compare_vol.iloc[-1] else compare_asset
                period_insight = (
                    f"Risk comparison: {indicator} volatility is currently "
                    f"{primary_vol.iloc[-1]:.2f}%, compared with "
                    f"{compare_vol.iloc[-1]:.2f}% for {compare_asset}. {riskier} "
                    "has experienced larger recent price swings."
                )

    # -----------------------------------------------------
    # SUMMARY STATISTICS
    # -----------------------------------------------------

    stats = calculate_summary_stats(df_filtered)

    latest_val = stats["latest_val"]
    position_pct = stats["position_pct"]
    slope = stats["slope"]
    volatility = stats["volatility"]

    if slope > 0:
        trend = "Upward"
    elif slope < 0:
        trend = "Downward"
    else:
        trend = "Flat"

    if position_pct > 70:
        position_label = "High"
    elif position_pct < 30:
        position_label = "Low"
    else:
        position_label = "Mid"

    if volatility > 25:
        significance = "High"
    elif volatility > 12:
        significance = "Moderate"
    else:
        significance = "Low"

    context_label = (
        "Custom view"
        if use_custom_range
        else f"{timeframe} view"
    )

    page_stats = {
        "Latest": f"{latest_val:,.2f}",
        "Trend": trend,
        "Position": (
            f"{position_pct:.2f}% "
            f"({position_label})"
        ),
        "Volatility": f"{volatility:.2f}%",
        "Significance": significance,
        "Context": context_label,
    }

    price_changes = {
        "1D": pct_change_over(df, "1D"),
        "1W": pct_change_over(df, "1W"),
        "1M": pct_change_over(df, "1M"),
        "6M": pct_change_over(df, "6M"),
        "1Y": pct_change_over(df, "1Y"),
    }

    # -----------------------------------------------------
    # FIGURE
    # -----------------------------------------------------

    has_comparison_data = (
        compare_df is not None
        and compare_asset != "Compare +"
        and not compare_df.empty
    )

    if chart_tool == "Percentage Change" and has_comparison_data:
        fig = build_percentage_change_chart(
            df=df_filtered,
            primary_chart_type=primary_chart_type,
            compare_df=compare_df,
            compare_name=compare_asset,
            compare_chart_type=compare_chart_type,
            primary_name=indicator,
        )
    elif chart_tool == "Ratio" and has_comparison_data:
        fig = build_ratio_chart(
            df=df_filtered,
            compare_df=compare_df,
            primary_name=indicator,
            compare_name=compare_asset,
            chart_type=primary_chart_type,
        )
    elif chart_tool == "Rolling Correlation" and has_comparison_data:
        fig = build_rolling_correlation_chart(
            df=df_filtered,
            compare_df=compare_df,
            primary_name=indicator,
            compare_name=compare_asset,
        )
    elif chart_tool == "Drawdown" and has_comparison_data:
        fig = build_drawdown_chart(
            df=df_filtered,
            compare_df=compare_df,
            primary_name=indicator,
            compare_name=compare_asset,
            primary_chart_type=primary_chart_type,
            compare_chart_type=compare_chart_type,
        )
    elif chart_tool == "Rolling Volatility" and has_comparison_data:
        fig = build_rolling_volatility_chart(
            df=df_filtered,
            compare_df=compare_df,
            primary_name=indicator,
            compare_name=compare_asset,
            primary_chart_type=primary_chart_type,
            compare_chart_type=compare_chart_type,
        )
    else:
        fig = build_clean_market_chart(
            df=df_filtered,
            primary_chart_type=primary_chart_type,
            compare_df=compare_df,
            compare_name=compare_asset,
            compare_chart_type=compare_chart_type,
            primary_name=indicator,
        )

    analysis_card_title = "Price Changes"
    analysis_card_items = price_changes

    if has_comparison_data and chart_tool != "Price":
        analysis_df = prepare_comparison_data(df_filtered, compare_df)

        if chart_tool == "Percentage Change" and not analysis_df.empty:
            primary_return = (
                analysis_df["value_main"].iloc[-1]
                / analysis_df["value_main"].iloc[0]
                - 1
            ) * 100
            compare_return = (
                analysis_df["value_compare"].iloc[-1]
                / analysis_df["value_compare"].iloc[0]
                - 1
            ) * 100
            analysis_card_title = "Period Performance"
            analysis_card_items = {
                indicator: f"{primary_return:+.2f}%",
                compare_asset: f"{compare_return:+.2f}%",
                "Difference": f"{primary_return - compare_return:+.2f}%",
            }

        elif chart_tool == "Ratio":
            ratios = (
                analysis_df.loc[
                    analysis_df["value_compare"] != 0,
                    "value_main",
                ]
                / analysis_df.loc[
                    analysis_df["value_compare"] != 0,
                    "value_compare",
                ]
            )
            if not ratios.empty:
                analysis_card_title = f"{indicator} / {compare_asset}"
                analysis_card_items = {
                    "Current Ratio": f"{ratios.iloc[-1]:,.2f}",
                    "Highest Ratio": f"{ratios.max():,.2f}",
                    "Lowest Ratio": f"{ratios.min():,.2f}",
                    "Average Ratio": f"{ratios.mean():,.2f}",
                }

        elif chart_tool == "Rolling Correlation":
            correlation = (
                analysis_df["value_main"].pct_change().rolling(60).corr(
                    analysis_df["value_compare"].pct_change()
                ).dropna()
            )
            if not correlation.empty:
                analysis_card_title = "60-Day Correlation"
                analysis_card_items = {
                    "Current": f"{correlation.iloc[-1]:+.2f}",
                    "Average": f"{correlation.mean():+.2f}",
                    "Highest": f"{correlation.max():+.2f}",
                    "Lowest": f"{correlation.min():+.2f}",
                }

        elif chart_tool == "Drawdown":
            primary_dd = (
                analysis_df["value_main"]
                / analysis_df["value_main"].cummax()
                - 1
            ) * 100
            compare_dd = (
                analysis_df["value_compare"]
                / analysis_df["value_compare"].cummax()
                - 1
            ) * 100
            analysis_card_title = "Drawdown Summary"
            analysis_card_items = {
                f"{indicator} Current": f"{primary_dd.iloc[-1]:+.2f}%",
                f"{indicator} Maximum": f"{primary_dd.min():+.2f}%",
                f"{compare_asset} Current": f"{compare_dd.iloc[-1]:+.2f}%",
                f"{compare_asset} Maximum": f"{compare_dd.min():+.2f}%",
            }

        elif chart_tool == "Rolling Volatility":
            primary_vol = (
                analysis_df["value_main"].pct_change().rolling(30).std()
                * (252 ** 0.5)
                * 100
            ).dropna()
            compare_vol = (
                analysis_df["value_compare"].pct_change().rolling(30).std()
                * (252 ** 0.5)
                * 100
            ).dropna()
            if not primary_vol.empty and not compare_vol.empty:
                analysis_card_title = "30-Day Annualized Volatility"
                analysis_card_items = {
                    f"{indicator} Current": f"{primary_vol.iloc[-1]:.2f}%",
                    f"{indicator} Average": f"{primary_vol.mean():.2f}%",
                    f"{compare_asset} Current": f"{compare_vol.iloc[-1]:.2f}%",
                    f"{compare_asset} Average": f"{compare_vol.mean():.2f}%",
                }

    cards = [
        {
            "title": "Related Markets",
            "type": "list",
            "items": meta["related"],
        },
        {
            "title": analysis_card_title,
            "type": "changes",
            "items": analysis_card_items,
        },
        {
            "title": "Key Drivers",
            "type": "list",
            "items": meta["drivers"],
        },
    ]

    render_research_page(
        title=indicator,
        description=meta["description"],
        stats=page_stats,
        figure=fig,
        source="Source: Yahoo Finance",
        cards=cards,
        chart_controls=render_chart_controls,
        show_header=False,
    )
