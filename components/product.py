"""Small market overview and a server-local research library."""

from datetime import date, timedelta
from urllib.parse import urlencode
import json
from html import escape
from io import StringIO
import pandas as pd
import streamlit as st
from comparison_registry import COMPARISON_REGISTRY
from data.yahoo import get_fx_data_yahoo
from macro_engine.research.analytics import clean, changes
from macro_engine.research.notebook import load_investigations, save_investigation


def internal_link(label, url):
    st.html(
        '<a target="_self" href="'
        + escape(url, quote=True)
        + '">'
        + escape(label)
        + "</a>"
    )


def investigation_url(left, right):
    return "?" + urlencode({"page": "Investigate", "left": left, "right": right})


@st.cache_data(ttl=600, show_spinner=False)
def recent_series(name, as_of):
    spec = COMPARISON_REGISTRY[name]
    if name == "Rates & Bonds · US 10Y":
        from data.http import read_csv

        frame = read_csv(
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10&cosd="
            + (as_of - timedelta(days=25)).isoformat()
            + "&coed="
            + as_of.isoformat()
        )
        frame = frame.rename(columns={frame.columns[0]: "date", "DGS10": "value"})
    else:
        frame = (
            spec["loader"]()
            if spec["kind"] == "function"
            else get_fx_data_yahoo(
                spec["loader"],
                start_date=as_of - timedelta(days=25),
                end_date=as_of + timedelta(days=1),
            )
        )
    if frame is None or frame.empty:
        raise ValueError("No observations")
    frame = clean(frame)
    return frame[frame.date <= pd.Timestamp(as_of)].tail(20)


def daily_reading(frame, meta, as_of):
    frame = clean(frame).set_index("date").value
    if len(frame) and pd.isna(frame.iloc[-1]):
        raise ValueError("Latest observation is missing")
    if len(frame) < 2:
        raise ValueError("Two observations required")
    # Do not bridge explicit missing values. This is the last recorded move, not a promised calendar-day return.
    delta = changes(frame, meta).iloc[-1]
    latest = frame.index[-1].date()
    return {
        "latest": latest,
        "value": frame.iloc[-1],
        "change": None if pd.isna(delta) else float(delta),
        "unit": meta.change_unit,
        "age": (as_of - latest).days,
        "previous": frame.index[-2].date(),
    }


def render_today():
    from components.chart_workspace import load_series, line_chart

    st.title("Today")
    st.caption("Markets at a glance. Choose a chart to look closer.")
    from components.discovery_radar import render_discovery_radar
    render_discovery_radar()
    names = [
        "Commodities · Gold",
        "Rates & Bonds · US 10Y",
        "Equities · S&P 500",
        "FX · EUR/USD",
    ]
    frames = {}
    for name in names:
        try:
            frames[name] = load_series(
                name, date.today() - timedelta(days=365), date.today()
            )
        except (ValueError, RuntimeError, OSError, KeyError):
            frames[name] = None
    for col, name in zip(st.columns(4), names):
        with col:
            st.caption(name.split(" · ")[-1])
            try:
                reading = daily_reading(
                    frames[name], COMPARISON_REGISTRY[name]["metadata"], date.today()
                )
                value = f"{reading['value']:,.2f}" + (
                    "%" if name.startswith("Rates") else ""
                )
                move = (
                    "No change available"
                    if reading["change"] is None
                    else f"{reading['change']:+.2f} { {'basis points': 'bp', 'percentage points': 'pp'}.get(reading['unit'], reading['unit']) }"
                )
                st.metric(
                    name.split(" · ")[-1], value, move, label_visibility="collapsed"
                )
                st.caption(
                    str(reading["latest"])
                    + (" · delayed" if reading["age"] > 3 else "")
                )
            except (ValueError, RuntimeError, KeyError, TypeError, AttributeError):
                st.info("Source unavailable")
    for offset in [0, 2]:
        for col, name in zip(st.columns(2), names[offset : offset + 2]):
            with col:
                st.subheader(name.split(" · ")[-1])
                frame = frames[name]
                if frame is not None and not frame.empty:
                    st.plotly_chart(line_chart(frame, name), use_container_width=True)
                    other = (
                        "Rates & Bonds · US 10Y"
                        if name != "Rates & Bonds · US 10Y"
                        else "Commodities · Gold"
                    )
                    internal_link("Look closer", investigation_url(name, other))
                else:
                    st.info("Chart unavailable right now.")
    st.subheader("The economy")
    for col, name in zip(
        st.columns(2), ["United States · CPI YoY", "United States · Unemployment Rate"]
    ):
        with col:
            st.markdown(
                "**" + ("Inflation" if "CPI" in name else "Unemployment") + "**"
            )
            try:
                frame = load_series(
                    name, date.today() - timedelta(days=1826), date.today()
                )
                if frame.empty:
                    raise ValueError("No data")
                st.plotly_chart(line_chart(frame, name, 250), use_container_width=True)
                st.caption("US · through " + str(frame.date.max().date()))
            except (ValueError, RuntimeError, OSError, KeyError):
                st.info("Chart unavailable right now.")
    st.caption(
        "Daily closes, not live prices. Moves alone do not explain why markets changed."
    )


def render_research():
    st.title("My Research")
    st.write("Return to a question, revise a conclusion, or export a copy.")
    st.caption(
        "Records are stored on this server, not in a personal cloud account. They may be lost on restart. Export a copy to keep it."
    )
    records = load_investigations()
    if not records:
        st.info("No investigations saved on this server yet.")
        internal_link("Start a question", "?page=Investigate")
    for record in records:
        with st.container(border=True):
            st.subheader(record.get("title", "Untitled investigation"))
            st.caption(
                f"{record.get('left', '')} / {record.get('right', '')} · {record.get('start', '')} to {record.get('end', '')}"
            )
            st.write(
                record.get("supporting")
                or record.get("hypothesis")
                or "No conclusion recorded yet."
            )
            internal_link(
                "Continue investigation", "?page=Investigate&record=" + record["id"]
            )
            st.download_button(
                "Export record",
                json.dumps(record, ensure_ascii=False, indent=2),
                file_name="investigation.json",
                mime="application/json",
                key="export_" + record["id"],
            )
    with st.expander("Restore an exported investigation"):
        file = st.file_uploader("Version 1 investigation JSON", type=["json"])
        if file is not None and st.button("Restore copy on this server"):
            try:
                if file.size > 2_000_000:
                    raise ValueError("File exceeds 2 MB limit")
                record = json.loads(file.getvalue())
                if not isinstance(record, dict):
                    raise ValueError("Expected a record")
                if record.get("schema_version", 1) != 1 or not all(
                    k in record
                    for k in [
                        "title",
                        "left",
                        "right",
                        "start",
                        "end",
                        "mode",
                        "window",
                    ]
                ):
                    raise ValueError("Unsupported investigation")
                if any(record[k] not in COMPARISON_REGISTRY for k in ["left", "right"]):
                    raise ValueError("Series not in catalogue")
                validate_restore(record)
                record["imported"] = True
                save_investigation(record)
                st.rerun()
            except (ValueError, TypeError, OSError):
                st.error(
                    "Could not restore this record. Keep the original file and check its format."
                )


def validate_restore(record):
    if not isinstance(record, dict):
        raise ValueError("Expected record")
    if not all(
        isinstance(record.get(k), str)
        for k in ["title", "left", "right", "start", "end", "mode"]
    ):
        raise ValueError("Invalid fields")
    if date.fromisoformat(record["start"]) > date.fromisoformat(record["end"]):
        raise ValueError("Invalid sample")
    if type(record.get("window")) is not int or not 3 <= record["window"] <= 1000:
        raise ValueError("Invalid window")
    if record["mode"] not in [
        "Price",
        "Changes",
        "Percentage Change",
        "Relative Performance",
        "Ratio",
        "Rolling Correlation",
        "Drawdown",
        "Rolling Volatility",
        "Yield Spread",
    ]:
        raise ValueError("Invalid transformation")
    evidence = record.get("evidence")
    if evidence:
        if not isinstance(evidence, dict) or not all(
            k in evidence
            for k in ["csv", "details", "lead_lag", "stability", "source_csv"]
        ):
            raise ValueError("Incomplete evidence")
        details = evidence["details"]
        if not isinstance(details, dict) or not all(
            k in details
            for k in [
                "mode",
                "frequency",
                "observations",
                "valid_statistics",
                "missing_periods",
                "limitation",
                "left_units",
                "right_units",
                "left_change_unit",
                "right_change_unit",
                "output_units",
                "start",
                "end",
            ]
        ):
            raise ValueError("Invalid methodology")
        stability = evidence["stability"]
        if not isinstance(stability, dict) or not all(
            k in stability for k in ["full_sample", "first_half", "second_half"]
        ):
            raise ValueError("Invalid stability")
        if any(
            not isinstance(v, dict)
            or not all(k in v for k in ["correlation", "observations"])
            for v in stability.values()
        ):
            raise ValueError("Invalid statistics")
        if not isinstance(evidence["lead_lag"], list):
            raise ValueError("Invalid lag estimates")
        if any(
            not isinstance(v, dict)
            or not all(k in v for k in ["lag", "correlation", "observations"])
            for v in evidence["lead_lag"]
        ):
            raise ValueError("Invalid lag fields")
        frame = pd.read_csv(
            StringIO(evidence["csv"]), index_col="date", parse_dates=["date"]
        )
        if frame.empty:
            raise ValueError("Empty evidence")
    return record
