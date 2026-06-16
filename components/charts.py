import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# -------- Helper Functions --------
def plot_chart(
    df,
    title,
    chart_type,
    height=450,
    date_format="daily",
    yaxis_suffix="",
    reference_lines=None,
    shaded_regions=None,
    tickformat_override=None,
    hover_style="delta",
    delta_type="cumulative",
    show_markers=False,
    decimals=2,
):
    # -------------------- Safety Checks --------------------
    if df is None:
        return None

    if not isinstance(df, pd.DataFrame):
        return None

    if df.empty:
        return None

    if "date" not in df.columns or "value" not in df.columns:
        return None

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["date", "value"])

    if df.empty:
        return None

    chart_color = "#1f77b4"

    # -------------------- Hover Date Formatting --------------------
    if date_format == "daily":
        hover_date_format = "%d %B %Y"
    elif date_format == "monthly":
        hover_date_format = "%B %Y"
    elif date_format == "quarterly":
        hover_date_format = None
    else:
        hover_date_format = "%Y-%m-%d"

    # -------------------- Chart Type --------------------
    mode = "lines+markers" if show_markers else "lines"

    if chart_type == "Line":
        fig = px.line(
            df,
            x="date",
            y="value",
            title=title,
            labels={"date": "", "value": ""},
            height=height,
        )
        fig.update_traces(line=dict(width=2, color=chart_color), mode=mode)

    elif chart_type == "Step":
        fig = px.line(
            df,
            x="date",
            y="value",
            title=title,
            labels={"date": "", "value": ""},
            height=height,
        )
        fig.update_traces(
            line_shape="hv",
            line=dict(width=2, color=chart_color),
            mode=mode,
        )

    elif chart_type == "Area":
        fig = px.area(
            df,
            x="date",
            y="value",
            title=title,
            labels={"date": "", "value": ""},
            height=height,
        )
        fig.update_traces(
            line_color=chart_color,
            fillcolor="rgba(31,119,180,0.3)",
        )

    elif chart_type == "Bar":
        fig = px.bar(
            df,
            x="date",
            y="value",
            title=title,
            labels={"date": "", "value": ""},
            height=height,
        )
        fig.update_traces(
            marker_color=chart_color,
            marker_line_color="black",
            marker_line_width=1,
        )

    else:
        raise ValueError(f"Unsupported chart_type: {chart_type}")

    # -------------------- Base Layout --------------------
    fig.update_layout(
        margin=dict(l=40, r=30, t=70, b=55),
        hovermode="closest",
        dragmode=False,
        title=dict(
            font=dict(size=19, family="Arial Bold"),
            x=0.5,
            xanchor="center",
        ),
        xaxis=dict(
            showgrid=False,
            showline=True,
            linecolor="black",
            linewidth=2,
            ticks="outside",
            ticklen=8,
            tickwidth=1.5,
            tickfont=dict(size=11, family="Arial", color="black"),
            automargin=True,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="LightGrey",
            gridwidth=0.3,
            showline=True,
            linecolor="black",
            linewidth=2,
            ticks="outside",
            tickfont=dict(size=12, family="Arial", color="black"),
            tickformat=f",.{decimals}f{yaxis_suffix}",
            automargin=True,
        ),
        hoverlabel=dict(
            font_size=15,
            bgcolor="#F9F9F9",
            bordercolor="black",
            align="left",
            namelength=0,
        ),
    )

    # -------------------- Reference Lines --------------------
    if reference_lines:
        for ref in reference_lines:
            fig.add_hline(
                y=ref["value"],
                line_dash="dash",
                line_color="red",
                annotation_text=ref.get("label", ""),
                annotation_position="top left",
                annotation_font=dict(size=12, color="red"),
            )

    # -------------------- Shaded Regions --------------------
    if shaded_regions:
        for region in shaded_regions:
            fig.add_vrect(
                x0=region["start"],
                x1=region["end"],
                fillcolor=region.get("color", "LightGrey"),
                opacity=region.get("opacity", 0.3),
                layer="below",
                line_width=0,
            )

    # -------------------- Hover Styles --------------------
    if hover_style == "delta":
        if delta_type == "daily":
            df["delta"] = df["value"].pct_change() * 100
        else:
            df["delta"] = (df["value"] / df["value"].iloc[0] - 1) * 100

        df["delta_str"] = df["delta"].apply(
            lambda x: f"▲ {x:.2f}%"
            if x > 0
            else (f"▼ {abs(x):.2f}%" if pd.notnull(x) and x < 0 else "— 0.00%")
        )

        df["delta_color"] = df["delta"].apply(
            lambda x: "green" if x > 0 else ("red" if x < 0 else "gray")
        )

        if date_format == "quarterly":
            df["hover_label"] = df["date"].dt.to_period("Q").apply(
                lambda x: f"Q{x.quarter} {x.year}"
            )
            fig.update_traces(
                customdata=df[["hover_label", "delta_str", "delta_color"]],
                hovertemplate=(
                    "<span style='color:black'><b>%{customdata[0]}</b></span><br>"
                    f"<span style='color:black'>%{{y:,.{decimals}f}}{yaxis_suffix}</span><br>"
                    "<span style='color:%{customdata[2]}; font-weight:bold'>%{customdata[1]}</span>"
                    "<extra></extra>"
                ),
            )

        else:
            fig.update_traces(
                customdata=df[["delta_str", "delta_color"]],
                hovertemplate=(
                    "<span style='color:black'><b>%{x|"
                    + hover_date_format
                    + "}</b></span><br>"
                    f"<span style='color:black'>%{{y:,.{decimals}f}}{yaxis_suffix}</span><br>"
                    "<span style='color:%{customdata[1]}; font-weight:bold'>%{customdata[0]}</span>"
                    "<extra></extra>"
                ),
            )

    else:
        if date_format == "quarterly":
            df["hover_label"] = df["date"].dt.to_period("Q").apply(
                lambda x: f"Q{x.quarter} {x.year}"
            )
            fig.update_traces(
                customdata=df["hover_label"],
                hovertemplate=(
                    f"<b>%{{customdata}}</b><br>%{{y:,.{decimals}f}}"
                    + yaxis_suffix
                    + "<extra></extra>"
                ),
            )

        else:
            hovertemplate = (
                "<span style='color:black'><b>%{x|"
                + hover_date_format
                + "}</b></span><br>"
                f"<span style='color:black'>%{{y:,.{decimals}f}}{yaxis_suffix}</span>"
                "<extra></extra>"
            )
            fig.update_traces(hovertemplate=hovertemplate)

    # -------------------- X-Axis Tick Formatting --------------------
    if tickformat_override:
        df["tick_label"] = df["date"].dt.strftime(tickformat_override)
        fig.update_xaxes(
            tickmode="array",
            tickvals=df["date"],
            ticktext=df["tick_label"],
        )

    elif date_format in ["daily", "monthly"]:
        fig.update_xaxes(
            tickformat="%b\n%Y",
            nticks=5,
            tickangle=0,
            automargin=True,
            tickfont=dict(size=10, family="Arial", color="black"),
        )

    elif date_format == "quarterly":
        quarter_ticks = df[df["date"].dt.quarter == 4]

        if quarter_ticks.empty:
            fig.update_xaxes(
                tickformat="%Y",
                nticks=5,
                tickangle=0,
                automargin=True,
                tickfont=dict(size=10, family="Arial", color="black"),
            )
        else:
            fig.update_xaxes(
                tickmode="array",
                tickvals=quarter_ticks["date"],
                ticktext=quarter_ticks["date"].dt.strftime("%Y"),
                tickangle=0,
                automargin=True,
                tickfont=dict(size=10, family="Arial", color="black"),
            )

    # -------------------- Final Mobile-Friendly Layout --------------------
    fig.update_layout(
        margin=dict(l=35, r=20, t=85, b=70),
        title=dict(
            font=dict(size=17, family="Arial Bold"),
            x=0.5,
            xanchor="center",
        ),
    )

    # Hide Plotly logo in modebar
    fig.update_layout(modebar=dict(remove=["toImage"]))

    return fig


def plot_scenario_chart(
    df,
    threshold_pct=4.0,
    window=30,
    window_unit="days",
    yaxis_suffix="",
    start_date=None,
    end_date=None,
):
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df.sort_values("date", inplace=True)
    df = df.reset_index(drop=True)

    today = pd.Timestamp.today().normalize()
    df = df[df["date"] <= today]

    if start_date:
        df = df[df["date"] >= pd.to_datetime(start_date)]

    if end_date:
        df = df[df["date"] <= pd.to_datetime(end_date)]

    df["daily_return"] = df["value"].pct_change() * 100
    df["trigger"] = df["daily_return"].abs() >= threshold_pct

    if window_unit == "days":
        delta = pd.Timedelta(days=window)
    elif window_unit == "weeks":
        delta = pd.Timedelta(weeks=window)
    elif window_unit == "months":
        delta = pd.DateOffset(months=window)
    elif window_unit == "years":
        delta = pd.DateOffset(years=window)
    else:
        delta = pd.Timedelta(days=window)

    segments = []
    n = len(df)
    base_color = "#1f77b4"
    trigger_color = "orange"

    i = 0
    trigger_rows = []

    while i < n - 1:
        if df.loc[i, "trigger"]:
            start_idx = i
            end_window_date = df.loc[i, "date"] + delta
            after_idx = (
                df[df["date"] <= end_window_date].index.max()
                if any(df["date"] <= end_window_date)
                else i
            )

            segments.append(
                {
                    "x": df.loc[start_idx : start_idx + 1, "date"],
                    "y": df.loc[start_idx : start_idx + 1, "value"],
                    "color": trigger_color,
                }
            )

            start_price = df.loc[start_idx, "value"]
            end_price = df.loc[after_idx, "value"]
            total_return = (end_price / start_price - 1) * 100

            trigger_rows.append(
                {
                    "Trigger Date": df.loc[start_idx, "date"].strftime("%Y-%m-%d"),
                    "Move %": round(df.loc[start_idx, "daily_return"], 2),
                    f"{window} {window_unit} Return %": round(total_return, 2),
                }
            )

            i = after_idx

        else:
            next_trigger = (
                df.index[(df.index > i) & (df["trigger"])].min()
                if any(df["trigger"][i + 1 :])
                else n - 1
            )

            segments.append(
                {
                    "x": df.loc[i:next_trigger, "date"],
                    "y": df.loc[i:next_trigger, "value"],
                    "color": base_color,
                }
            )

            i = next_trigger

    fig = go.Figure()

    for seg in segments:
        fig.add_trace(
            go.Scatter(
                x=seg["x"],
                y=seg["y"],
                mode="lines",
                line=dict(color=seg["color"], width=3),
                hovertemplate=(
                    "<b>%{x|%d %B %Y}</b><br>"
                    f"%{{y:,.2f}}{yaxis_suffix}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=f"{threshold_pct}% Daily Move (Highlighted in Orange)",
        margin=dict(l=40, r=30, t=60, b=20),
        hovermode="x unified",
        xaxis=dict(
            showgrid=False,
            showline=True,
            linecolor="black",
            linewidth=2,
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="LightGrey",
            gridwidth=0.3,
            showline=True,
            linecolor="black",
            linewidth=2,
            tickformat=f",.2f{yaxis_suffix}",
        ),
    )

    if trigger_rows:
        table_df = pd.DataFrame(trigger_rows)
    else:
        table_df = pd.DataFrame(
            columns=["Trigger Date", "Move %", f"{window} {window_unit} Return %"]
        )

    return fig, table_df