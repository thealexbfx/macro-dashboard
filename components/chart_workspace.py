"""Chart-first screens: no text, number or date entry."""

from datetime import date, timedelta
from io import StringIO
import json
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from comparison_registry import COMPARISON_REGISTRY
from data.yahoo import get_fx_data_yahoo
from macro_engine.research.analytics import analyze, relationship, clean, SeriesMetadata
from macro_engine.research.notebook import load_investigations, save_investigation

PERIODS = {"1 year": 365, "5 years": 1826, "All": None}
CORE = [
    "Commodities · Gold",
    "Rates & Bonds · US 10Y",
    "Equities · S&P 500",
    "FX · EUR/USD",
    "Commodities · Crude Oil",
    "Crypto · Bitcoin",
    "United States · CPI YoY",
    "United States · Unemployment Rate",
]


def short(name):
    return {"CPI YoY": "Inflation", "Unemployment Rate": "Unemployment"}.get(
        name.split(" · ")[-1], name.split(" · ")[-1]
    )


def line_chart(frame, name, height=300):
    fig = go.Figure(
        go.Scatter(
            x=frame.date,
            y=frame.value,
            mode="lines",
            name=short(name),
            line=dict(color="#3166cd", width=2),
            connectgaps=False,
        )
    )
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=12, r=12, t=12, b=25),
        showlegend=False,
        font=dict(color="#526076", size=11),
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, title=None)
    fig.update_yaxes(
        gridcolor="#edf0f5",
        title=COMPARISON_REGISTRY[name]["metadata"].units,
        zeroline=False,
    )
    return fig


@st.cache_data(ttl=900, show_spinner=False)
def load_series(name, start, end):
    spec = COMPARISON_REGISTRY[name]
    fred_ids = {
        "Rates & Bonds · US 10Y": "DGS10",
        "United States · CPI YoY": "CPIAUCSL",
        "United States · Unemployment Rate": "UNRATE",
    }
    if name in fred_ids:
        from data.http import read_csv

        series = fred_ids[name]
        source_start = start - timedelta(days=400) if series == "CPIAUCSL" else start
        frame = read_csv(
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id="
            + series
            + "&cosd="
            + source_start.isoformat()
            + "&coed="
            + end.isoformat()
        )
        frame = frame.rename(columns={frame.columns[0]: "date", series: "value"})
        if series == "CPIAUCSL":
            from data.transforms import calculate_yoy_from_index

            frame = calculate_yoy_from_index(clean(frame))
    else:
        frame = (
            spec["loader"]()
            if spec["kind"] == "function"
            else get_fx_data_yahoo(
                spec["loader"], start_date=start, end_date=end + timedelta(days=1)
            )
        )
    if frame is None or frame.empty:
        raise ValueError("No data")
    frame = clean(frame)
    return frame[
        (frame.date >= pd.Timestamp(start)) & (frame.date <= pd.Timestamp(end))
    ]


def pair_chart(values, details, left, right):
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.12,
        subplot_titles=[short(left), short(right)],
    )
    for i, (column, name, color) in enumerate(
        [("left", left, "#3166cd"), ("right", right, "#d4a344")]
    ):
        fig.add_trace(
            go.Scatter(
                x=values.index,
                y=values[column],
                name=short(name),
                mode="lines",
                connectgaps=False,
                line=dict(color=color, width=2),
            ),
            row=i + 1,
            col=1,
        )
        fig.update_yaxes(
            title_text=details["left_units" if i == 0 else "right_units"],
            row=i + 1,
            col=1,
            gridcolor="#edf0f5",
            zeroline=False,
        )
    fig.update_layout(
        template="plotly_white",
        height=570,
        margin=dict(l=15, r=15, t=35, b=25),
        showlegend=False,
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False)
    return fig


def plain_finding(r):
    if r is None:
        return "There is not enough shared data to compare these moves."
    if abs(r) < 0.1:
        return "Their changes showed little connection."
    strength = (
        "weakly" if abs(r) < 0.3 else "moderately" if abs(r) < 0.5 else "strongly"
    )
    direction = "opposite directions" if r < 0 else "the same direction"
    return f"Their changes tended to move in {direction}, {strength}."


def show_snapshot(record):
    evidence = record.get("evidence") or {}
    if not evidence.get("source_csv"):
        st.info("Open this pair to refresh its chart.")
        return
    try:
        left, right = record["left"], record["right"]
        a, b = [
            pd.read_csv(StringIO(evidence["source_csv"][side]))
            for side in ["left", "right"]
        ]
        saved_details = evidence.get("details", {})
        lm = (
            SeriesMetadata(**saved_details["left_metadata"])
            if saved_details.get("left_metadata")
            else COMPARISON_REGISTRY[left]["metadata"]
        )
        rm = (
            SeriesMetadata(**saved_details["right_metadata"])
            if saved_details.get("right_metadata")
            else COMPARISON_REGISTRY[right]["metadata"]
        )
        values, details = analyze(a, b, lm, rm, "Price")
        st.plotly_chart(
            pair_chart(values, details, left, right), use_container_width=True
        )
        st.caption(
            f"Saved prices and readings · {record['start']} to {record['end']}. Refresh to get newer data."
        )
        if record.get("imported"):
            st.caption("Imported data has not been checked against its source.")
    except (ValueError, KeyError, TypeError):
        st.info("This older chart needs a refresh. The saved record is unchanged.")


def render_investigate():
    st.title("Investigate")
    st.caption("Pick two things. See how they moved.")
    options = [n for n in CORE if n in COMPARISON_REGISTRY]
    context = None
    if st.query_params.get('discovery'):
        try:
            start_link=date.fromisoformat(st.query_params['start'])
            end_link=date.fromisoformat(st.query_params['end'])
            observation=date.fromisoformat(st.query_params['observation'])
            target=st.query_params['left']
            if target not in COMPARISON_REGISTRY or not start_link <= observation <= end_link < date.today():
                raise ValueError('Invalid discovery context')
            context={'signal_id':st.query_params['discovery'],'name':target,'start':start_link,'end':end_link,'observation':observation}
        except (ValueError, KeyError):
            st.warning('Discovery link is invalid. Using the standard comparison workspace.')
    active_related=None
    if context:
        from discovery.radar import SPECS, RELATED
        identity=next((key for key,spec in SPECS.items() if spec[0]==context['name']),None)
        suggestions=[(name,why) for name,why in RELATED.get(identity,[]) if name in COMPARISON_REGISTRY]
        st.caption(f"Discovery observation: {context['observation']} · requested history {context['start']} to {context['end']}")
        for name,why in suggestions:
            st.caption(f'{short(name)} — {why}')
        queue=st.multiselect('Related comparison queue',[n for n,_ in suggestions],default=[suggestions[0][0]] if suggestions else [],
                             format_func=short,key='discovery_queue_'+context['signal_id'])
        if queue:
            active_related=st.radio('Queued comparison',queue,format_func=short,horizontal=True)
        for name in queue:
            if name not in options: options.append(name)
    for side in ("left", "right"):
        linked = st.query_params.get(side)
        if linked in COMPARISON_REGISTRY and linked not in options:
            options.append(linked)
    # A saved investigation can use any existing catalogue series.
    records = {x["id"]: x for x in load_investigations()}
    record = records.get(st.query_params.get("record"))
    if record:
        for side in ["left", "right"]:
            if record.get(side) in COMPARISON_REGISTRY and record[side] not in options:
                options.append(record[side])
        st.subheader(record.get("title", "Saved research"))
        show_snapshot(record)
        if record.get("supporting"):
            st.write(record["supporting"])
        if st.button("Refresh this pair"):
            st.query_params.clear()
            st.query_params["page"] = "Investigate"
            st.query_params["left"] = record["left"]
            st.query_params["right"] = record["right"]
            st.rerun()
        return
    a, b, c = st.columns([2, 2, 1])

    def default(side, fallback):
        requested = active_related if side=='right' and active_related else st.query_params.get(side, fallback)
        return (
            options.index(requested)
            if requested in options
            else options.index(fallback)
        )

    with a:
        left = st.selectbox(
            "Compare",
            options,
            index=default("left", "Commodities · Gold"),
            format_func=short,
        )
    with b:
        right = st.selectbox(
            "With",
            options,
            index=default("right", "Rates & Bonds · US 10Y"),
            format_func=short,
            **({'key':'discovery_pair_'+context['signal_id']+'_'+str(active_related)} if context else {}),
        )
    with c:
        period = st.selectbox("Time", ['Discovery window'] if context else list(PERIODS), index=0 if context else 1)
    if left == right:
        st.info("Choose two different things.")
        return
    end = date.today()
    start = context['start'] if context else (
        date(2000, 1, 1)
        if PERIODS[period] is None
        else end - timedelta(days=PERIODS[period])
    )
    if context:
        start,end=context['start'],context['end']
    try:
        with st.spinner("Loading charts…"):
            x, y = load_series(left, start, end), load_series(right, start, end)
            lm, rm = (
                COMPARISON_REGISTRY[left]["metadata"],
                COMPARISON_REGISTRY[right]["metadata"],
            )
            levels, details = analyze(x, y, lm, rm, "Price")
            changed, change_details = analyze(x, y, lm, rm, "Changes")
            evidence = relationship(changed, window=60)
        chart=pair_chart(levels, details, left, right)
        if context:
            chart.add_vline(x=str(context['observation']),line_dash='dot',line_color='#d4a344')
        st.plotly_chart(chart, use_container_width=True)
        st.write(plain_finding(evidence["full_sample"]["correlation"]))
        st.caption(
            f"{details['start']} to {details['end']} · Past patterns do not predict the next move."
        )
        if st.button("Save this comparison", type="primary"):
            payload = dict(
                title=f"{short(left)} and {short(right)}",
                left=left,
                right=right,
                start=str(start),
                end=str(end),
                mode="Price",
                frequency="Native alignment",
                window=60,
                hypothesis="",
                supporting="",
                counterarguments="",
                evidence={
                    "csv": levels.to_csv(index_label="date"),
                    "changed_csv": changed.to_csv(index_label="date"),
                    "rolling_csv": evidence["rolling"].to_csv(index_label="date"),
                    "source_csv": {
                        "left": x.to_csv(index=False),
                        "right": y.to_csv(index=False),
                    },
                    "details": details,
                    "lead_lag": evidence["lead_lag"],
                    "stability": {
                        k: evidence[k]
                        for k in ["full_sample", "first_half", "second_half"]
                    },
                },
            )
            if context:
                payload['discovery']={'signal_id':context['signal_id'],'observation_date':str(context['observation']),
                                      'target':context['name'],'queue':queue}
            save_key = f"chart_saved_{left}_{right}_{period}" + (f"_{context['start']}_{context['end']}" if context else '')
            try:
                saved = save_investigation(
                    payload, investigation_id=st.session_state.get(save_key)
                )
                st.session_state[save_key] = saved["id"]
                st.success("Saved in My Research.")
            except (OSError, ValueError):
                st.warning(
                    "Could not save this comparison. You can still download its data below."
                )
        with st.expander("Data and downloads"):
            st.caption(
                f"The short finding compares changes, not price levels: {change_details['valid_statistics']:,} paired changes. Yield changes use basis points; eligible prices use percent returns."
            )
            st.caption(details["limitation"])
            st.caption(
                f"Sources: {details['left_source']}; {details['right_source']}. Missing values are left blank."
            )
            st.download_button(
                "Download data",
                levels.to_csv(index_label="date"),
                "comparison.csv",
                "text/csv",
            )
    except (ValueError, RuntimeError, OSError, KeyError):
        st.info("This data is unavailable right now. Try another pair.")


def render_chart_research():
    st.title("My Research")
    st.caption("Your saved comparisons, ready to revisit.")
    records = load_investigations()
    if not records:
        st.info("Nothing saved yet. Save a comparison from Investigate.")
        return
    labels = {x["id"]: x.get("title", "Saved comparison") for x in records}
    selected = st.selectbox("Open a comparison", list(labels), format_func=labels.get)
    record = next(x for x in records if x["id"] == selected)
    show_snapshot(record)
    if record.get("supporting"):
        st.write(record["supporting"])
    if record.get("hypothesis"):
        with st.expander("Earlier question"):
            st.write(record["hypothesis"])
    st.caption("Saved on this server. Download a copy to keep it through a restart.")
    st.download_button(
        "Download comparison",
        json.dumps(record, indent=2),
        "investigation.json",
        "application/json",
    )
