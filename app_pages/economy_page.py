import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app_pages.common import calculate_summary_stats
from app_pages.market_utils import filter_by_dates
from components.research.research_page import render_research_page


# =========================================================
# DATE HELPERS
# =========================================================

def get_start_date(df, timeframe):
    end = df["date"].max()

    offsets = {
        "1Y": pd.DateOffset(years=1),
        "3Y": pd.DateOffset(years=3),
        "5Y": pd.DateOffset(years=5),
        "10Y": pd.DateOffset(years=10),
    }

    if timeframe in offsets:
        return end - offsets[timeframe]

    return df["date"].min()


def absolute_change_over(df, label):
    end = df["date"].max()

    offsets = {
        "1M": pd.DateOffset(months=1),
        "3M": pd.DateOffset(months=3),
        "6M": pd.DateOffset(months=6),
        "1Y": pd.DateOffset(years=1),
    }

    start_date = end - offsets[label]
    past = df[df["date"] <= start_date]

    if past.empty:
        return None

    return df["value"].iloc[-1] - past["value"].iloc[-1]


# =========================================================
# DATA + FORMATTING HELPERS
# =========================================================

def clean_economy_data(df):
    cleaned = df.copy()
    cleaned["date"] = pd.to_datetime(cleaned["date"])
    cleaned["value"] = pd.to_numeric(cleaned["value"], errors="coerce")

    return (
        cleaned
        .dropna(subset=["date", "value"])
        .sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )


def extend_policy_rate_to_today(df, is_policy_rate):
    if not is_policy_rate or df.empty:
        return df

    today = pd.Timestamp.today().normalize()
    last_date = df["date"].max()

    if last_date >= today:
        return df

    extension = pd.DataFrame(
        {
            "date": [today],
            "value": [df["value"].iloc[-1]],
        }
    )

    return (
        pd.concat([df, extension], ignore_index=True)
        .sort_values("date")
        .reset_index(drop=True)
    )


def format_value(value, meta, include_sign=False):
    decimals = meta.get("decimals", 2)
    unit_label = meta.get("unit_label", "")
    sign = "+" if include_sign and value > 0 else ""

    if meta.get("unit_type") == "thousands":
        return f"{sign}{value:,.{decimals}f}{unit_label}"

    if meta.get("unit_type") == "percent":
        return f"{sign}{value:,.{decimals}f}{unit_label}"

    return f"{sign}{value:,.{decimals}f}{unit_label}"


def format_change(value, meta):
    if value is None:
        return "—"

    if meta.get("change_type") == "percentage_points":
        sign = "+" if value > 0 else ""
        decimals = meta.get("decimals", 1)
        return f"{sign}{value:.{decimals}f} pp"

    return format_value(value, meta, include_sign=True)


def axis_tick_suffix(meta):
    return meta.get("unit_label", "")


def hover_template(name, meta):
    decimals = meta.get("decimals", 2)
    suffix = meta.get("unit_label", "")

    return (
        "<b>%{x|%b %d, %Y}</b><br>"
        f"<b>{name}</b>&nbsp;&nbsp;%{{y:,.{decimals}f}}{suffix}"
        "<extra></extra>"
    )


# =========================================================
# CHART
# =========================================================

def build_economy_level_chart(
    primary_df,
    primary_name,
    primary_meta,
    primary_chart_type,
    compare_df=None,
    compare_name=None,
    compare_meta=None,
    compare_chart_type="Line",
):
    fig = go.Figure()

    has_compare = (
        compare_df is not None
        and compare_name not in [None, "Compare +"]
        and not compare_df.empty
    )

    def add_series(df, name, meta, chart_type, color, yaxis=None):
        common = {
            "x": df["date"],
            "y": df["value"],
            "name": name,
            "hovertemplate": hover_template(name, meta),
        }

        if yaxis:
            common["yaxis"] = yaxis

        if chart_type == "Bar":
            fig.add_trace(
                go.Bar(
                    **common,
                    marker=dict(color=color, line=dict(width=0)),
                    opacity=0.72,
                )
            )
            return

        line_shape = "hv" if chart_type == "Step" else "linear"

        trace_args = {
            **common,
            "mode": "lines",
            "line": dict(
                color=color,
                width=2.5,
                shape=line_shape,
            ),
        }

        if chart_type == "Area":
            trace_args["fill"] = "tozeroy"
            trace_args["fillcolor"] = (
                "rgba(37, 99, 235, 0.07)"
                if color == "#2563EB"
                else "rgba(22, 163, 74, 0.06)"
            )

        fig.add_trace(go.Scatter(**trace_args))

    if has_compare:
        add_series(
            primary_df,
            primary_name,
            primary_meta,
            primary_chart_type,
            "#2563EB",
            yaxis="y2",
        )

        add_series(
            compare_df,
            compare_name,
            compare_meta,
            compare_chart_type,
            "#16A34A",
            yaxis="y",
        )
    else:
        add_series(
            primary_df,
            primary_name,
            primary_meta,
            primary_chart_type,
            "#2563EB",
        )

    fig.update_layout(
        height=430,
        margin=dict(
            l=58,
            r=62 if has_compare else 28,
            t=42 if has_compare else 18,
            b=46,
        ),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        showlegend=has_compare,
        hovermode="x unified" if has_compare else "closest",
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
            hoverformat="%b %d, %Y",
            fixedrange=True,
        ),
        yaxis=dict(
            title=(
                compare_meta.get("title", compare_name)
                if has_compare
                else primary_meta.get("title", primary_name)
            ),
            showgrid=True,
            gridcolor="#E8EDF4",
            zeroline=False,
            showline=True,
            linecolor="#111827",
            linewidth=1.3,
            ticks="outside",
            tickcolor="#111827",
            ticklen=5,
            ticksuffix=(
                axis_tick_suffix(compare_meta)
                if has_compare
                else axis_tick_suffix(primary_meta)
            ),
            tickformat=f",.{(
                compare_meta.get('decimals', 2)
                if has_compare
                else primary_meta.get('decimals', 2)
            )}f",
            fixedrange=True,
        ),
    )

    if has_compare:
        fig.update_layout(
            yaxis2=dict(
                title=primary_meta.get("title", primary_name),
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
                ticksuffix=axis_tick_suffix(primary_meta),
                tickformat=f",.{primary_meta.get('decimals', 2)}f",
                fixedrange=True,
            )
        )

    return fig


# =========================================================
# PAGE
# =========================================================

def render_economy_page(
    economy_map,
    category_map,
    page_key,
    country_name,
    page_description,
):
    def key(name):
        return f"{page_key}_{name}"

    st.markdown(
        """
        <style>
        .ml-economy-select-label {
            margin-bottom: 0.35rem;
            color: #64748B;
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.10em;
        }

        .ml-economy-title-wrap {
            min-height: 66px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .ml-economy-title {
            color: #0F172A;
            font-size: 2.0rem;
            font-weight: 750;
            line-height: 1.1;
            text-align: center;
        }

        .ml-economy-description {
            max-width: 980px;
            margin: 0.25rem auto 1.0rem auto;
            color: #475569;
            font-size: 0.98rem;
            line-height: 1.55;
            text-align: center;
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

    category_col, indicator_col, title_col = st.columns(
        [2.0, 2.5, 5.5],
        gap="medium",
    )

    with category_col:
        st.markdown(
            "<div class='ml-economy-select-label'>SELECT CATEGORY</div>",
            unsafe_allow_html=True,
        )

        category = st.selectbox(
            "Select Category",
            list(category_map.keys()),
            key=key("category"),
            label_visibility="collapsed",
        )

    with indicator_col:
        st.markdown(
            "<div class='ml-economy-select-label'>SELECT INDICATOR</div>",
            unsafe_allow_html=True,
        )

        indicator = st.selectbox(
            "Select Indicator",
            category_map[category],
            key=key("indicator"),
            label_visibility="collapsed",
        )

    meta = economy_map[indicator]

    with title_col:
        st.markdown(
            f"""
            <div class="ml-economy-title-wrap">
                <div class="ml-economy-title">{country_name}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"""
        <div class="ml-economy-description">
            <strong>{indicator}</strong> — {meta["description"]}
        </div>
        """,
        unsafe_allow_html=True,
    )

    df = clean_economy_data(meta["data_func"]())
    df = extend_policy_rate_to_today(
        df,
        meta.get("is_policy_rate", False),
    )

    if df.empty:
        st.error("No data available.")
        st.stop()

    timeframe = st.session_state.get(key("timeframe"), "5Y")
    primary_chart_type = st.session_state.get(
        key("primary_chart_type"),
        "Step" if meta.get("is_policy_rate") else "Line",
    )

    compare_asset = st.session_state.get(
        key("compare_selected"),
        "Compare +",
    )

    compare_chart_type = st.session_state.get(
        key("compare_chart_type"),
        "Line",
    )

    def reset_custom_range_from_timeframe():
        st.session_state[key("use_custom_range")] = False

    def sync_compare_selection():
        st.session_state[key("compare_selected")] = (
            st.session_state[key("compare")]
        )

    def render_chart_controls():
        default_end = df["date"].max().date()
        default_start = max(
            df["date"].min().date(),
            (df["date"].max() - pd.DateOffset(years=5)).date(),
        )

        timeframe_col, date_col, compare_col = st.columns(
            [6.2, 0.9, 2.1],
            gap="small",
        )

        with timeframe_col:
            st.segmented_control(
                "Timeframe",
                ["1Y", "3Y", "5Y", "10Y", "MAX"],
                key=key("timeframe"),
                default="5Y",
                label_visibility="collapsed",
                on_change=reset_custom_range_from_timeframe,
            )

        with date_col:
            earliest = df["date"].min().date()
            latest = df["date"].max().date()

            saved_start = st.session_state.get(
                key("custom_start"),
                default_start,
            )
            saved_end = st.session_state.get(
                key("custom_end"),
                latest,
            )

            saved_start = max(saved_start, earliest)
            saved_end = min(saved_end, latest)
            saved_start = min(saved_start, saved_end)

            with st.popover("Date", use_container_width=True):
                custom_dates = st.date_input(
                    "Custom date range",
                    value=(saved_start, saved_end),
                    min_value=earliest,
                    max_value=latest,
                    key=key("custom_dates"),
                    label_visibility="collapsed",
                )

                if (
                    isinstance(custom_dates, (tuple, list))
                    and len(custom_dates) == 2
                ):
                    custom_start, custom_end = custom_dates

                    if custom_start <= custom_end:
                        if st.button(
                            "Apply range",
                            key=key("apply_custom_range"),
                            use_container_width=True,
                        ):
                            st.session_state[key("custom_start")] = custom_start
                            st.session_state[key("custom_end")] = custom_end
                            st.session_state[key("use_custom_range")] = True
                            st.rerun()

                if st.button(
                    "Reset",
                    key=key("reset_custom_range"),
                    use_container_width=True,
                ):
                    st.session_state[key("use_custom_range")] = False
                    st.session_state[key("custom_start")] = default_start
                    st.session_state[key("custom_end")] = latest
                    st.rerun()

        with compare_col:
            compare_options = [
                "Compare +",
                *[
                    name
                    for name in economy_map.keys()
                    if name != indicator
                ],
            ]

            st.selectbox(
                "Compare",
                compare_options,
                key=key("compare"),
                label_visibility="collapsed",
                on_change=sync_compare_selection,
            )

        active_compare = compare_asset != "Compare +"

        st.markdown(
            "<div class='ml-chart-type-row-label'>Chart display</div>",
            unsafe_allow_html=True,
        )

        if active_compare:
            primary_type_col, compare_type_col, tool_col = st.columns(
                [2.0, 2.0, 2.6],
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
                st.selectbox(
                    f"{compare_asset} chart type",
                    ["Line", "Area", "Bar", "Step"],
                    key=key("compare_chart_type"),
                    format_func=lambda value: f"{compare_asset}: {value}",
                    label_visibility="collapsed",
                )

            with tool_col:
                st.selectbox(
                    "Economic analysis tool",
                    ["Level"],
                    key=key("chart_tool"),
                    format_func=lambda value: f"Tool: {value}",
                    label_visibility="collapsed",
                    disabled=True,
                )
        else:
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
                    "Economic analysis tool",
                    ["Level"],
                    key=key("chart_tool"),
                    format_func=lambda value: f"Tool: {value}",
                    label_visibility="collapsed",
                    disabled=True,
                )

        st.markdown(
            f"""
            <div class="ml-chart-explanation">
                Level view preserves each indicator's original unit. When two
                indicators use different units, MacroLens displays them on
                separate axes rather than applying a misleading conversion.
            </div>
            <div class="ml-chart-insight-label">CURRENT VIEW</div>
            <div class="ml-chart-insight">
                {period_insight}
            </div>
            """,
            unsafe_allow_html=True,
        )

    use_custom_range = st.session_state.get(
        key("use_custom_range"),
        False,
    )

    if use_custom_range:
        start_date = pd.Timestamp(
            st.session_state.get(
                key("custom_start"),
                df["date"].min().date(),
            )
        )
        end_date = pd.Timestamp(
            st.session_state.get(
                key("custom_end"),
                df["date"].max().date(),
            )
        )
    else:
        start_date = get_start_date(df, timeframe)
        end_date = df["date"].max()

    df_filtered = filter_by_dates(
        df,
        start_date,
        end_date,
    )

    compare_df = None
    compare_meta = None

    if compare_asset != "Compare +" and compare_asset in economy_map:
        compare_meta = economy_map[compare_asset]
        compare_df = clean_economy_data(compare_meta["data_func"]())
        compare_df = extend_policy_rate_to_today(
            compare_df,
            compare_meta.get("is_policy_rate", False),
        )
        compare_df = filter_by_dates(
            compare_df,
            start_date,
            end_date,
        )

    has_compare = (
        compare_df is not None
        and compare_meta is not None
        and not compare_df.empty
    )

    primary_values = df_filtered["value"].dropna()

    if primary_values.empty:
        st.error("No data available in the selected range.")
        st.stop()

    start_value = primary_values.iloc[0]
    latest_value = primary_values.iloc[-1]
    primary_change = latest_value - start_value
    direction = "rose" if primary_change > 0 else "fell" if primary_change < 0 else "was unchanged"

    period_insight = (
        f"{indicator} {direction} from "
        f"{format_value(start_value, meta)} to "
        f"{format_value(latest_value, meta)} over the selected period."
    )

    if has_compare:
        compare_values = compare_df["value"].dropna()

        if not compare_values.empty:
            compare_start = compare_values.iloc[0]
            compare_latest = compare_values.iloc[-1]
            compare_change = compare_latest - compare_start
            compare_direction = (
                "rose"
                if compare_change > 0
                else "fell"
                if compare_change < 0
                else "was unchanged"
            )

            period_insight = (
                f"{indicator} {direction} from "
                f"{format_value(start_value, meta)} to "
                f"{format_value(latest_value, meta)}, while "
                f"{compare_asset} {compare_direction} from "
                f"{format_value(compare_start, compare_meta)} to "
                f"{format_value(compare_latest, compare_meta)}. "
                "The dual axes preserve each indicator's original unit."
            )

    stats = calculate_summary_stats(df_filtered)

    if stats["slope"] > 0:
        trend = "Upward"
    elif stats["slope"] < 0:
        trend = "Downward"
    else:
        trend = "Flat"

    if stats["position_pct"] > 70:
        position_label = "High"
    elif stats["position_pct"] < 30:
        position_label = "Low"
    else:
        position_label = "Mid"

    context_label = (
        "Custom view"
        if use_custom_range
        else f"{timeframe} view"
    )

    page_stats = {
        "Latest": format_value(stats["latest_val"], meta),
        "Trend": trend,
        "Position": (
            f"{stats['position_pct']:.0f}% "
            f"({position_label})"
        ),
        "Period Change": format_change(
            stats["change_since_start"],
            meta,
        ),
        "Frequency": meta.get("frequency", "—").title(),
        "Context": context_label,
    }

    fig = build_economy_level_chart(
        primary_df=df_filtered,
        primary_name=indicator,
        primary_meta=meta,
        primary_chart_type=primary_chart_type,
        compare_df=compare_df,
        compare_name=compare_asset if has_compare else None,
        compare_meta=compare_meta,
        compare_chart_type=compare_chart_type,
    )

    related_indicators = [
        item
        for item in category_map.get(category, [])
        if item != indicator
    ][:5]

    if not related_indicators:
        related_indicators = ["No related indicators configured"]

    changes = {
        "1M": format_change(
            absolute_change_over(df, "1M"),
            meta,
        ),
        "3M": format_change(
            absolute_change_over(df, "3M"),
            meta,
        ),
        "6M": format_change(
            absolute_change_over(df, "6M"),
            meta,
        ),
        "1Y": format_change(
            absolute_change_over(df, "1Y"),
            meta,
        ),
    }

    indicator_details = [
        f"Category: {category}",
        f"Frequency: {meta.get('frequency', '—').title()}",
        f"Unit: {meta.get('unit_type', '—').replace('_', ' ').title()}",
        (
            "Raw difference comparison supported"
            if meta.get("compatible_group")
            else "Standardized comparison recommended"
        ),
    ]

    cards = [
        {
            "title": "Related Indicators",
            "type": "list",
            "items": related_indicators,
        },
        {
            "title": "Recent Changes",
            "type": "changes",
            "items": changes,
        },
        {
            "title": "Indicator Details",
            "type": "list",
            "items": indicator_details,
        },
    ]

    render_research_page(
        title=indicator,
        description=meta["description"],
        stats=page_stats,
        figure=fig,
        source=meta.get("source", "Source: MacroLens Research"),
        cards=cards,
        chart_controls=render_chart_controls,
        show_header=False,
    )
