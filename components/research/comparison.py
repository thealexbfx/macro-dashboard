"""Shared evidence view for existing market comparison controls."""

import json

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from macro_engine.research.analytics import analyze, metadata, relationship


def comparison_figure(values, details, left_name, right_name):
    separate = len(values.columns) == 2 and details["mode"] in {
        "Price",
        "Changes",
        "Rolling Volatility",
    }
    fig = make_subplots(
        rows=2 if separate else 1,
        cols=1,
        shared_xaxes=True,
        subplot_titles=(left_name, right_name) if separate else None,
    )
    for i, column in enumerate(values.columns):
        label = (
            (left_name if i == 0 else right_name)
            if column in {"left", "right"}
            else column
        )
        fig.add_trace(
            go.Scatter(x=values.index, y=values[column], name=label, connectgaps=False),
            row=i + 1 if separate else 1,
            col=1,
        )
    fig.update_layout(
        title=f"{left_name} vs {right_name} — {details['mode']}",
        height=600 if separate else 430,
    )
    left_axis = (
        details["left_units"]
        if details["mode"] == "Price"
        else details["left_change_unit"]
        if separate
        else details["output_units"]
    )
    fig.update_yaxes(title_text=left_axis, row=1, col=1)
    if separate:
        fig.update_yaxes(
            title_text=details["right_units"]
            if details["mode"] == "Price"
            else details["right_change_unit"],
            row=2,
            col=1,
        )
    fig.update_layout(
        title=dict(
            text=f"{left_name}<br>{right_name} · {details['mode']}", font=dict(size=13)
        ),
        template="plotly_white",
        colorway=["#1d4ed8", "#b45309"],
        legend=dict(orientation="h", y=-0.12, x=0),
        margin=dict(l=45, r=15, t=90, b=105),
        hovermode="x unified",
        meta=details,
    )
    fig.update_xaxes(title_text="Observation period", row=2 if separate else 1, col=1)
    if details["mode"] != "Price":
        fig.add_hline(y=0, line_color="#64748b", line_width=1)
    fig.add_annotation(
        x=0,
        y=-0.30,
        xref="paper",
        yref="paper",
        xanchor="left",
        showarrow=False,
        text=f"{details['frequency']} · paired n={details['observations']}<br>{details['start']} to {details['end']}<br>Latest-vintage observations; publication timing unverified.<br>Not a point-in-time backtest.",
        font=dict(size=10),
    )
    fig.update_layout(margin=dict(b=175))
    return fig


def render_comparison(
    left, right, left_config, right_config, left_name, right_name, mode, controls
):
    controls()
    lm = metadata(left_config, left_name, left_config.get("group", ""))
    rm = right_config.get("metadata") or metadata(right_config, right_name)
    window = None
    if mode in {"Rolling Correlation", "Rolling Volatility"}:
        window = int(
            st.number_input(
                "Rolling window (comparison periods)",
                min_value=3,
                max_value=1000,
                value=60 if mode == "Rolling Correlation" else 30,
            )
        )
    try:
        values, details = analyze(left, right, lm, rm, mode, window=window)
    except ValueError as exc:
        st.warning(str(exc))
        st.caption(
            "Choose Price for original levels or Changes for economically appropriate changes."
        )
        return
    fig = comparison_figure(values, details, left_name, right_name)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        f"{details['frequency']} • {details['observations']} paired observations • "
        f"{details['start']} to {details['end']} • {details['output_units']} • "
        f"{details['missing_periods']} missing periods • {details['alignment']}"
    )
    st.caption(
        f"Sources: {details['left_source']}; {details['right_source']}. "
        f"{details.get('transformations', '')}"
    )
    st.info(details.get("warning") or details["limitation"])
    if "warning" in details:
        st.caption(details["limitation"])
    if mode == "Price":
        st.caption(
            "Separate panels retain each series' units. Visual co-movement does not establish a relationship."
        )
    valid = values.dropna()
    if not valid.empty:
        st.dataframe(valid.tail(5))
    with st.expander("Lead/lag and historical stability"):
        st.caption(
            "Uses percentage returns for eligible prices, basis-point yield changes, and absolute changes elsewhere."
        )
        try:
            changes_frame, _ = analyze(left, right, lm, rm, "Changes")
        except ValueError as exc:
            st.warning(str(exc))
            return
        stability_window = int(
            st.number_input("Stability window (comparison periods)", 3, 1000, 12)
        )
        report = relationship(changes_frame, window=stability_window)
        st.dataframe(report["lead_lag"])
        st.write({k: report[k] for k in ("full_sample", "first_half", "second_half")})
        st.line_chart(report["rolling"].rename("Rolling correlation of changes"))
        for limitation in report["limitations"]:
            st.caption(limitation)
    st.download_button(
        "Export calculation data (CSV)",
        values.to_csv(index_label="date"),
        "macrolens-analysis.csv",
        "text/csv",
    )
    st.download_button(
        "Export methodology (JSON)",
        json.dumps(details, indent=2),
        "macrolens-methodology.json",
        "application/json",
    )
    st.download_button(
        "Export interactive research chart",
        fig.to_html(include_plotlyjs=True),
        "macrolens-chart.html",
        "text/html",
    )
