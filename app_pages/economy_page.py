import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app_pages.market_utils import filter_by_dates
from components.research.research_page import render_research_page

from components.page_intro import render_page_intro

ANALYSIS_OPTIONS = [
    "Level",
    "Z-Score",
    "Percentile",
    "Correlation",
    "Spread",
]

FREQUENCY_ORDER = {
    "daily": 0,
    "weekly": 1,
    "monthly": 2,
    "quarterly": 3,
    "annual": 4,
}

FREQUENCY_PERIODS = {
    "daily": "D",
    "weekly": "W-FRI",
    "monthly": "M",
    "quarterly": "Q",
    "annual": "Y",
}


# =========================================================
# DATE + DATA HELPERS
# =========================================================

def get_start_date(df, timeframe):
    end = df["date"].max()
    offsets = {
        "1Y": pd.DateOffset(years=1),
        "3Y": pd.DateOffset(years=3),
        "5Y": pd.DateOffset(years=5),
        "10Y": pd.DateOffset(years=10),
    }
    return end - offsets[timeframe] if timeframe in offsets else df["date"].min()


def clean_economy_data(df):
    if df is None or df.empty or not {"date", "value"}.issubset(df.columns):
        return pd.DataFrame(columns=["date", "value"])

    cleaned = df[["date", "value"]].copy()
    cleaned["date"] = pd.to_datetime(cleaned["date"], errors="coerce")
    cleaned["value"] = pd.to_numeric(cleaned["value"], errors="coerce")
    return (
        cleaned.dropna(subset=["date", "value"])
        .sort_values("date")
        .drop_duplicates(subset=["date"], keep="last")
        .reset_index(drop=True)
    )


def extend_policy_rate_to_today(df, is_policy_rate):
    if not is_policy_rate or df.empty:
        return df

    today = pd.Timestamp.today().normalize()
    if df["date"].max() >= today:
        return df

    return pd.concat(
        [df, pd.DataFrame({"date": [today], "value": [df["value"].iloc[-1]]})],
        ignore_index=True,
    ).sort_values("date").reset_index(drop=True)


def load_indicator(meta):
    return extend_policy_rate_to_today(
        clean_economy_data(meta["data_func"]()),
        meta.get("is_policy_rate", False),
    )


def value_at_or_before(df, target_date):
    eligible = df[df["date"] <= target_date]
    return None if eligible.empty else float(eligible["value"].iloc[-1])


def absolute_change_over(df, label):
    if df.empty:
        return None

    offsets = {
        "1M": pd.DateOffset(months=1),
        "3M": pd.DateOffset(months=3),
        "6M": pd.DateOffset(months=6),
        "1Y": pd.DateOffset(years=1),
    }
    latest = float(df["value"].iloc[-1])
    past = value_at_or_before(df, df["date"].max() - offsets[label])
    return None if past is None else latest - past


def common_frequency(primary_meta, compare_meta):
    primary = primary_meta.get("frequency", "monthly").lower()
    compare = compare_meta.get("frequency", "monthly").lower()
    return max(
        (primary, compare),
        key=lambda item: FREQUENCY_ORDER.get(item, FREQUENCY_ORDER["monthly"]),
    )


def align_series(primary_df, compare_df, primary_meta, compare_meta):
    """Align two macro series without inventing higher-frequency observations."""
    frequency = common_frequency(primary_meta, compare_meta)
    period_alias = FREQUENCY_PERIODS.get(frequency, "M")

    def resample(df, name):
        sampled = df[["date", "value"]].copy()
        sampled["period"] = sampled["date"].dt.to_period(period_alias)
        sampled = sampled.groupby("period", as_index=False)["value"].last()
        sampled["date"] = sampled["period"].dt.to_timestamp(how="end").dt.normalize()
        return sampled.set_index("date")["value"].dropna().rename(name)

    aligned = pd.concat(
        [resample(primary_df, "primary"), resample(compare_df, "compare")],
        axis=1,
        join="inner",
    ).dropna().reset_index()
    return aligned, frequency


def zscore(series):
    std = series.std(ddof=0)
    if pd.isna(std) or math.isclose(float(std), 0.0):
        return pd.Series(0.0, index=series.index)
    return (series - series.mean()) / std


def historical_percentile_series(series):
    return series.rank(method="average", pct=True) * 100


def latest_percentile(df):
    values = df["value"].dropna()
    if values.empty:
        return None
    latest = values.iloc[-1]
    return float((values <= latest).mean() * 100)


def ordinal(value):
    rounded = int(round(value))
    if 10 <= rounded % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(rounded % 10, "th")
    return f"{rounded}{suffix} Percentile"


def recent_trend(df, observations=6):
    values = df["value"].dropna().tail(observations)
    if len(values) < 2:
        return "Stable"

    change = float(values.iloc[-1] - values.iloc[0])
    scale = max(float(values.abs().median()), float(values.std(ddof=0)), 1.0)
    threshold = scale * 0.01
    if change > threshold:
        return "Rising"
    if change < -threshold:
        return "Falling"
    return "Stable"


def spread_is_compatible(primary_meta, compare_meta):
    if not compare_meta:
        return False

    primary_override = primary_meta.get("spread_unit")
    compare_override = compare_meta.get("spread_unit")
    if primary_override or compare_override:
        return bool(primary_override and primary_override == compare_override)

    return (
        primary_meta.get("unit_type") == "percent"
        and compare_meta.get("unit_type") == "percent"
        and primary_meta.get("unit_label", "%")
        == compare_meta.get("unit_label", "%")
    )


# =========================================================
# FORMATTING
# =========================================================

def format_value(value, meta, include_sign=False):
    if value is None or pd.isna(value):
        return "—"
    decimals = meta.get("decimals", 2)
    suffix = meta.get("unit_label", "")
    sign = "+" if include_sign and value > 0 else ""
    return f"{sign}{value:,.{decimals}f}{suffix}"


def format_change(value, meta):
    if value is None or pd.isna(value):
        return "—"
    if meta.get("change_type") == "percentage_points":
        sign = "+" if value > 0 else ""
        return f"{sign}{value:.{meta.get('decimals', 1)}f} pp"
    return format_value(value, meta, include_sign=True)


def hover_template(name, decimals=2, suffix=""):
    return (
        "<b>%{x|%b %d, %Y}</b><br>"
        f"<b>{name}</b>&nbsp;&nbsp;%{{y:,.{decimals}f}}{suffix}"
        "<extra></extra>"
    )


# =========================================================
# ANALYSIS ENGINE
# =========================================================

def transform_analysis(
    analysis,
    primary_df,
    primary_name,
    primary_meta,
    compare_df=None,
    compare_name=None,
    compare_meta=None,
    correlation_window=12,
):
    has_compare = compare_df is not None and compare_meta is not None and not compare_df.empty

    result = {
        "analysis": analysis,
        "primary": primary_df.copy(),
        "compare": compare_df.copy() if has_compare else None,
        "y_title": primary_meta.get("title", primary_name),
        "suffix": primary_meta.get("unit_label", ""),
        "decimals": primary_meta.get("decimals", 2),
        "common_axis": False,
        "frequency": None,
        "valid": True,
        "message": "",
    }

    if analysis == "Level":
        return result

    if analysis == "Z-Score":
        result["primary"]["value"] = zscore(result["primary"]["value"])
        if has_compare:
            result["compare"]["value"] = zscore(result["compare"]["value"])
        result.update(y_title="Z-Score", suffix="σ", decimals=2, common_axis=True)
        return result

    if analysis == "Percentile":
        result["primary"]["value"] = historical_percentile_series(
            result["primary"]["value"]
        )
        if has_compare:
            result["compare"]["value"] = historical_percentile_series(
                result["compare"]["value"]
            )
        result.update(
            y_title="Historical Percentile",
            suffix="%",
            decimals=0,
            common_axis=True,
        )
        return result

    if not has_compare:
        result.update(
            valid=False,
            message=f"{analysis} requires a comparison indicator.",
        )
        return result

    aligned, frequency = align_series(
        primary_df,
        compare_df,
        primary_meta,
        compare_meta,
    )
    result["frequency"] = frequency

    if aligned.empty:
        result.update(
            valid=False,
            message="The selected indicators do not have overlapping observations.",
        )
        return result

    if analysis == "Correlation":
        minimum = max(4, correlation_window // 2)
        corr = aligned["primary"].rolling(
            correlation_window,
            min_periods=minimum,
        ).corr(aligned["compare"])
        result["primary"] = pd.DataFrame(
            {"date": aligned["date"], "value": corr}
        ).dropna()
        result["compare"] = None
        result.update(
            y_title=f"Rolling Correlation ({correlation_window} observations)",
            suffix="",
            decimals=2,
            common_axis=True,
        )
        if result["primary"].empty:
            result.update(
                valid=False,
                message=(
                    f"At least {minimum} overlapping observations are needed "
                    "for this correlation window."
                ),
            )
        return result

    if analysis == "Spread":
        if not spread_is_compatible(primary_meta, compare_meta):
            result.update(
                valid=False,
                message=(
                    "Spread is available only for indicators with compatible units. "
                    "Use Z-Score, Percentile, or Correlation for this pair."
                ),
            )
            return result

        result["primary"] = pd.DataFrame(
            {
                "date": aligned["date"],
                "value": aligned["primary"] - aligned["compare"],
            }
        )
        result["compare"] = None
        result.update(
            y_title=f"{primary_name} minus {compare_name}",
            suffix=primary_meta.get("unit_label", ""),
            decimals=max(
                primary_meta.get("decimals", 2),
                compare_meta.get("decimals", 2),
            ),
            common_axis=True,
        )
        return result

    return result


# =========================================================
# CHART
# =========================================================

def build_economy_chart(
    transformed,
    primary_name,
    primary_meta,
    primary_chart_type,
    compare_name=None,
    compare_meta=None,
    compare_chart_type="Line",
):
    fig = go.Figure()

    if not transformed["valid"]:
        fig.add_annotation(
            text=transformed["message"],
            x=0.5,
            y=0.5,
            xref="paper",
            yref="paper",
            showarrow=False,
            align="center",
            font=dict(size=15, color="#475569"),
        )
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        fig.update_layout(height=430, paper_bgcolor="#FFFFFF", plot_bgcolor="#FFFFFF")
        return fig

    analysis = transformed["analysis"]
    primary_df = transformed["primary"]
    compare_df = transformed["compare"]
    has_compare = compare_df is not None and not compare_df.empty
    dual_axis = has_compare and analysis == "Level"

    if analysis == "Correlation":
        primary_trace_name = f"{primary_name} vs {compare_name}"
    elif analysis == "Spread":
        primary_trace_name = f"{primary_name} − {compare_name}"
    else:
        primary_trace_name = primary_name

    def add_series(df, name, chart_type, color, yaxis=None, meta=None):
        decimals = transformed["decimals"] if analysis != "Level" else meta.get("decimals", 2)
        suffix = transformed["suffix"] if analysis != "Level" else meta.get("unit_label", "")
        common = dict(
            x=df["date"],
            y=df["value"],
            name=name,
            hovertemplate=hover_template(name, decimals, suffix),
        )
        if yaxis:
            common["yaxis"] = yaxis

        if chart_type == "Bar" and analysis not in {"Correlation", "Spread"}:
            fig.add_trace(
                go.Bar(**common, marker=dict(color=color, line=dict(width=0)), opacity=0.72)
            )
            return

        trace = dict(
            **common,
            mode="lines",
            line=dict(
                color=color,
                width=2.5,
                shape="hv" if chart_type == "Step" and analysis == "Level" else "linear",
            ),
        )
        if chart_type == "Area" and analysis not in {"Correlation", "Spread"}:
            trace["fill"] = "tozeroy"
            trace["fillcolor"] = (
                "rgba(37, 99, 235, 0.07)"
                if color == "#2563EB"
                else "rgba(22, 163, 74, 0.06)"
            )
        fig.add_trace(go.Scatter(**trace))

    add_series(
        primary_df,
        primary_trace_name,
        primary_chart_type,
        "#2563EB",
        yaxis="y2" if dual_axis else None,
        meta=primary_meta,
    )
    if has_compare:
        add_series(
            compare_df,
            compare_name,
            compare_chart_type,
            "#16A34A",
            meta=compare_meta,
        )

    if analysis == "Z-Score":
        for level in (-2, 0, 2):
            fig.add_hline(
                y=level,
                line_width=1,
                line_dash="dot" if level else "solid",
                line_color="#CBD5E1",
            )
    elif analysis == "Percentile":
        for level in (20, 50, 80):
            fig.add_hline(y=level, line_width=1, line_dash="dot", line_color="#CBD5E1")
    elif analysis == "Correlation":
        fig.add_hline(y=0, line_width=1, line_color="#94A3B8")
    elif analysis == "Spread":
        fig.add_hline(y=0, line_width=1, line_color="#94A3B8")

    left_title = (
        compare_meta.get("title", compare_name)
        if dual_axis
        else transformed["y_title"]
    )
    left_suffix = (
        compare_meta.get("unit_label", "")
        if dual_axis
        else transformed["suffix"]
    )
    left_decimals = (
        compare_meta.get("decimals", 2)
        if dual_axis
        else transformed["decimals"]
    )

    fig.update_layout(
        height=430,
        margin=dict(l=58, r=62 if dual_axis else 28, t=42 if has_compare else 18, b=46),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        showlegend=has_compare,
        hovermode="x unified" if has_compare else "closest",
        barmode="overlay",
        font=dict(family="Inter", size=14, color="#111827"),
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
            font=dict(family="Inter", color="#111827", size=14),
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
            title=left_title,
            showgrid=True,
            gridcolor="#E8EDF4",
            zeroline=False,
            showline=True,
            linecolor="#111827",
            linewidth=1.3,
            ticks="outside",
            tickcolor="#111827",
            ticklen=5,
            ticksuffix=left_suffix,
            tickformat=f",.{left_decimals}f",
            fixedrange=True,
        ),
    )

    if analysis == "Percentile":
        fig.update_yaxes(range=[0, 100])
    elif analysis == "Correlation":
        fig.update_yaxes(range=[-1, 1])

    if dual_axis:
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
                ticksuffix=primary_meta.get("unit_label", ""),
                tickformat=f",.{primary_meta.get('decimals', 2)}f",
                fixedrange=True,
            )
        )

    return fig


# =========================================================
# MACRO NARRATIVE
# =========================================================

def comparison_intelligence(
    primary_name,
    primary_df,
    primary_meta,
    compare_name,
    compare_df,
    compare_meta,
):
    if compare_df is None or compare_meta is None or compare_df.empty:
        change = absolute_change_over(primary_df, "3M")
        if change is None:
            return f"{primary_name} is currently {format_value(primary_df['value'].iloc[-1], primary_meta)}."
        direction = "rising" if change > 0 else "falling" if change < 0 else "stable"
        return (
            f"{primary_name} is {direction}, with a 3-month change of "
            f"{format_change(change, primary_meta)}."
        )

    names = {primary_name, compare_name}
    latest = {
        primary_name: float(primary_df["value"].iloc[-1]),
        compare_name: float(compare_df["value"].iloc[-1]),
    }
    changes = {
        primary_name: absolute_change_over(primary_df, "3M"),
        compare_name: absolute_change_over(compare_df, "3M"),
    }

    inflation_names = {
        "CPI YoY",
        "Core CPI YoY",
        "PCE YoY",
        "Core PCE YoY",
        "PPI YoY",
        "Core PPI YoY",
    }
    inflation_match = next((name for name in names if name in inflation_names), None)
    if "Federal Funds Rate" in names and inflation_match:
        real_rate = latest["Federal Funds Rate"] - latest[inflation_match]
        inflation_change = changes[inflation_match]
        if real_rate > 0 and (inflation_change is None or inflation_change <= 0):
            return (
                f"The policy rate is {real_rate:.1f} percentage points above "
                f"{inflation_match}, suggesting real policy settings are restrictive."
            )
        if real_rate > 0:
            return (
                f"The policy rate remains {real_rate:.1f} percentage points above "
                f"{inflation_match}, although renewed inflation pressure could reduce restraint."
            )
        return (
            f"The policy rate is {abs(real_rate):.1f} percentage points below "
            f"{inflation_match}, implying a negative simple real policy rate."
        )

    if names == {"Non Farm Payrolls", "Unemployment Rate"}:
        payrolls = latest["Non Farm Payrolls"]
        unemployment_change = changes["Unemployment Rate"]
        if payrolls > 150 and unemployment_change is not None and unemployment_change > 0:
            return (
                "Labor demand remains resilient despite a gradual increase in unemployment."
            )
        if payrolls > 150 and (unemployment_change is None or unemployment_change <= 0):
            return "Payroll growth remains firm while unemployment is stable or improving."
        if payrolls < 100 and unemployment_change is not None and unemployment_change > 0:
            return "Slower hiring and rising unemployment point to a cooling labor market."
        return "Hiring momentum has moderated, but the unemployment signal remains mixed."

    if "Average Hourly Earnings YoY" in names and inflation_match:
        real_wage_growth = latest["Average Hourly Earnings YoY"] - latest[inflation_match]
        if real_wage_growth > 0:
            return (
                f"Wage growth is running {real_wage_growth:.1f} percentage points above "
                f"{inflation_match}, supporting real household purchasing power."
            )
        return (
            f"Wage growth is trailing {inflation_match} by {abs(real_wage_growth):.1f} "
            "percentage points, pressuring real purchasing power."
        )

    aligned, frequency = align_series(
        primary_df,
        compare_df,
        primary_meta,
        compare_meta,
    )
    corr = aligned["primary"].corr(aligned["compare"]) if len(aligned) >= 4 else None
    primary_direction = recent_trend(primary_df).lower()
    compare_direction = recent_trend(compare_df).lower()
    relationship = ""
    if corr is not None and not pd.isna(corr):
        if corr >= 0.6:
            relationship = f" Their {frequency} readings have moved closely together (r = {corr:.2f})."
        elif corr <= -0.6:
            relationship = f" Their {frequency} readings have moved in opposite directions (r = {corr:.2f})."
    return (
        f"{primary_name} is {primary_direction}, while {compare_name} is "
        f"{compare_direction}.{relationship}"
    )


def analysis_explanation(analysis, has_compare, compatible, window):
    if analysis == "Level":
        return (
            "Level preserves each indicator’s original unit. Different units use separate "
            "axes so the comparison is not distorted."
        )
    if analysis == "Z-Score":
        return (
            "Z-Score shows how far each reading sits from its selected-period average, "
            "measured in standard deviations."
        )
    if analysis == "Percentile":
        return (
            "Percentile ranks every reading within the selected history. 80 means the "
            "reading is higher than roughly 80% of observations in view."
        )
    if analysis == "Correlation":
        return (
            f"Rolling correlation measures co-movement over {window} aligned observations. "
            "It describes association, not causation."
            if has_compare
            else "Select a comparison indicator to calculate rolling correlation."
        )
    if analysis == "Spread":
        if not has_compare:
            return "Select a comparison indicator to calculate a spread."
        if not compatible:
            return "These units are not compatible for subtraction; use a standardized analysis instead."
        return "Spread subtracts the comparison indicator from the primary indicator in like-for-like units."
    return ""


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
            margin-bottom: 0.35rem; color: #64748B; font-size: 0.72rem;
            font-weight: 700; letter-spacing: 0.10em;
        }
        .ml-economy-description {
            max-width: 980px; margin: 0.25rem auto 1rem auto; color: #475569;
            font-size: 0.98rem; line-height: 1.55; text-align: center;
        }
        .ml-chart-type-row-label {
            margin-top: 0.55rem; margin-bottom: 0.32rem; color: #94A3B8;
            font-size: 0.68rem; font-weight: 700; letter-spacing: 0.11em;
        }
        .ml-chart-explanation {
            margin-top: 0.7rem; color: #64748B; font-size: 0.88rem;
            line-height: 1.5; max-width: 980px;
        }
        .ml-chart-insight-label {
            margin-top: 0.8rem; color: #94A3B8; font-size: 0.68rem;
            font-weight: 700; letter-spacing: 0.11em;
        }
        .ml-chart-insight {
            margin-top: 0.18rem; margin-bottom: 0.35rem; padding: 0.62rem 0.78rem;
            border-left: 3px solid #2563EB; border-radius: 0 7px 7px 0;
            background: #F8FAFC; color: #334155; font-size: 0.9rem; line-height: 1.5;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    render_page_intro(
        title=f"{country_name} Economy",
        description=page_description,
        guide=(
            "Select an indicator to explore its latest reading, historical trend "
            "and supporting data. These pages explain the economic evidence that "
            "feeds the Macro Engine rather than providing investment signals."
        ),
    )
    
    selector_col, _ = st.columns([3.2, 6.8], gap="medium")
    with selector_col:
        st.markdown("<div class='ml-economy-select-label'>SELECT CATEGORY</div>", unsafe_allow_html=True)
        category = st.selectbox(
            "Select Category",
            list(category_map.keys()),
            key=key("category"),
            label_visibility="collapsed",
        )
        st.markdown(
            "<div class='ml-economy-select-label' style='margin-top:0.65rem;'>SELECT INDICATOR</div>",
            unsafe_allow_html=True,
        )
        indicator = st.selectbox(
            "Select Indicator",
            category_map[category],
            key=key("indicator"),
            label_visibility="collapsed",
        )

    meta = economy_map[indicator]
    st.markdown(
        f"<div class='ml-economy-description'><strong>{indicator}</strong> — {meta['description']}</div>",
        unsafe_allow_html=True,
    )

    df = load_indicator(meta)
    if df.empty:
        st.error("No data available.")
        return

    timeframe = st.session_state.get(key("timeframe"), "5Y")
    analysis = st.session_state.get(key("analysis"), "Level")
    correlation_window = int(st.session_state.get(key("correlation_window"), 12))
    primary_chart_type = st.session_state.get(
        key("primary_chart_type"),
        "Step" if meta.get("is_policy_rate") else "Line",
    )
    compare_asset = st.session_state.get(key("compare"), "Compare +")
    compare_chart_type = st.session_state.get(key("compare_chart_type"), "Line")

    use_custom_range = st.session_state.get(key("use_custom_range"), False)
    if use_custom_range:
        start_date = pd.Timestamp(st.session_state.get(key("custom_start"), df["date"].min().date()))
        end_date = pd.Timestamp(st.session_state.get(key("custom_end"), df["date"].max().date()))
    else:
        start_date = get_start_date(df, timeframe)
        end_date = df["date"].max()

    df_filtered = filter_by_dates(df, start_date, end_date)
    if df_filtered.empty:
        st.error("No data available in the selected range.")
        return

    compare_df = None
    compare_meta = None
    if compare_asset != "Compare +" and compare_asset in economy_map:
        compare_meta = economy_map[compare_asset]
        compare_df = filter_by_dates(load_indicator(compare_meta), start_date, end_date)

    has_compare = compare_df is not None and compare_meta is not None and not compare_df.empty
    compatible_spread = spread_is_compatible(meta, compare_meta)

    transformed = transform_analysis(
        analysis=analysis,
        primary_df=df_filtered,
        primary_name=indicator,
        primary_meta=meta,
        compare_df=compare_df,
        compare_name=compare_asset if has_compare else None,
        compare_meta=compare_meta,
        correlation_window=correlation_window,
    )

    macro_insight = comparison_intelligence(
        indicator,
        df_filtered,
        meta,
        compare_asset if has_compare else None,
        compare_df,
        compare_meta,
    )

    def reset_custom_range_from_timeframe():
        st.session_state[key("use_custom_range")] = False

    def render_chart_controls():
        default_start = max(
            df["date"].min().date(),
            (df["date"].max() - pd.DateOffset(years=5)).date(),
        )
        earliest = df["date"].min().date()
        latest = df["date"].max().date()

        timeframe_col, date_col, compare_col = st.columns([6.2, 0.9, 2.1], gap="small")
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
            saved_start = max(st.session_state.get(key("custom_start"), default_start), earliest)
            saved_end = min(st.session_state.get(key("custom_end"), latest), latest)
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
                if isinstance(custom_dates, (tuple, list)) and len(custom_dates) == 2:
                    custom_start, custom_end = custom_dates
                    if custom_start <= custom_end and st.button(
                        "Apply range",
                        key=key("apply_custom_range"),
                        use_container_width=True,
                    ):
                        st.session_state[key("custom_start")] = custom_start
                        st.session_state[key("custom_end")] = custom_end
                        st.session_state[key("use_custom_range")] = True
                        st.rerun()
                if st.button("Reset", key=key("reset_custom_range"), use_container_width=True):
                    st.session_state[key("use_custom_range")] = False
                    st.session_state[key("custom_start")] = default_start
                    st.session_state[key("custom_end")] = latest
                    st.rerun()
        with compare_col:
            st.selectbox(
                "Compare",
                ["Compare +", *[name for name in economy_map if name != indicator]],
                key=key("compare"),
                label_visibility="collapsed",
            )

        st.markdown("<div class='ml-chart-type-row-label'>CHART DISPLAY</div>", unsafe_allow_html=True)
        if has_compare:
            primary_col, compare_type_col, analysis_col = st.columns([2.0, 2.0, 2.6], gap="small")
            with primary_col:
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
            with analysis_col:
                st.selectbox(
                    "Economic analysis",
                    ANALYSIS_OPTIONS,
                    key=key("analysis"),
                    format_func=lambda value: f"Analysis: {value}",
                    label_visibility="collapsed",
                )
        else:
            primary_col, analysis_col, _ = st.columns([2.0, 2.6, 4.0], gap="small")
            with primary_col:
                st.selectbox(
                    f"{indicator} chart type",
                    ["Line", "Area", "Bar", "Step"],
                    key=key("primary_chart_type"),
                    format_func=lambda value: f"{indicator}: {value}",
                    label_visibility="collapsed",
                )
            with analysis_col:
                st.selectbox(
                    "Economic analysis",
                    ANALYSIS_OPTIONS,
                    key=key("analysis"),
                    format_func=lambda value: f"Analysis: {value}",
                    label_visibility="collapsed",
                )

        if analysis == "Correlation":
            st.select_slider(
                "Rolling window (aligned observations)",
                options=[6, 12, 24, 36, 60],
                value=correlation_window,
                key=key("correlation_window"),
            )

        explanation = analysis_explanation(
            analysis,
            has_compare,
            compatible_spread,
            correlation_window,
        )
        st.markdown(
            f"""
            <div class='ml-chart-explanation'>{explanation}</div>
            <div class='ml-chart-insight-label'>MACRO READ</div>
            <div class='ml-chart-insight'>{macro_insight}</div>
            """,
            unsafe_allow_html=True,
        )

    context_percentile = latest_percentile(df_filtered)
    context_label = "Custom View" if use_custom_range else f"{timeframe} View"
    page_stats = {
        "Latest": format_value(float(df_filtered["value"].iloc[-1]), meta),
        "Trend": recent_trend(df_filtered),
        "Historical Position": (
            ordinal(context_percentile) if context_percentile is not None else "—"
        ),
        "3M Change": format_change(absolute_change_over(df_filtered, "3M"), meta),
        "Frequency": meta.get("frequency", "—").title(),
        "Context": context_label,
    }

    fig = build_economy_chart(
        transformed=transformed,
        primary_name=indicator,
        primary_meta=meta,
        primary_chart_type=primary_chart_type,
        compare_name=compare_asset if has_compare else None,
        compare_meta=compare_meta,
        compare_chart_type=compare_chart_type,
    )

    related_indicators = [item for item in category_map.get(category, []) if item != indicator][:5]
    if not related_indicators:
        related_indicators = ["No related indicators configured"]

    changes = {
        label: format_change(absolute_change_over(df, label), meta)
        for label in ["1M", "3M", "6M", "1Y"]
    }

    available_analyses = ["Level", "Z-Score", "Percentile"]
    if has_compare:
        available_analyses.append("Correlation")
    if has_compare and compatible_spread:
        available_analyses.append("Spread")

    indicator_details = [
        f"Category: {category}",
        f"Frequency: {meta.get('frequency', '—').title()}",
        f"Unit: {meta.get('unit_type', '—').replace('_', ' ').title()}",
        f"Analyses ready: {', '.join(available_analyses)}",
    ]

    cards = [
        {"title": "Related Indicators", "type": "list", "items": related_indicators},
        {"title": "Recent Changes", "type": "changes", "items": changes},
        {"title": "Indicator Details", "type": "list", "items": indicator_details},
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
