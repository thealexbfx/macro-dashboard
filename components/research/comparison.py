"""Shared evidence view for existing market comparison controls."""


import plotly.graph_objects as go
from plotly.subplots import make_subplots



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
