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
    st.title("What changed?")
    st.write("A quick market check. Follow a question that interests you.")
    st.caption(
        "Latest recorded moves, not live quotes. Price movements alone do not identify their causes."
    )
    watch = [
        ("Commodities · Gold", "Rates & Bonds · US 10Y"),
        ("Rates & Bonds · US 10Y", "Commodities · Gold"),
        ("Equities · S&P 500", "Commodities · Gold"),
        ("FX · EUR/USD", "Rates & Bonds · US 10Y"),
    ]
    for name, other in watch:
        with st.container(border=True):
            st.markdown("**" + name.split(" · ")[-1] + "**")
            try:
                with st.spinner("Checking observations…"):
                    result = daily_reading(
                        recent_series(name, date.today()),
                        COMPARISON_REGISTRY[name]["metadata"],
                        date.today(),
                    )
                move = (
                    "Unavailable"
                    if result["change"] is None
                    else f"{result['change']:+.2f} {result['unit']}"
                )
                st.write(move + " since previous observation")
                st.caption(
                    f"{result['previous']} → {result['latest']} · latest value {result['value']:,.2f} · {COMPARISON_REGISTRY[name]['metadata'].source}"
                )
                if result["age"] > 3:
                    st.warning(
                        f"Data is {result['age']} calendar days old. The move is not today's return."
                    )
            except (ValueError, RuntimeError, OSError, KeyError):
                st.info("Source unavailable. No move has been estimated.")
            internal_link("Investigate a relationship", investigation_url(name, other))
    st.caption(
        "Market responses to releases require verified event and surprise data. This overview does not supply a news feed or infer catalysts."
    )
    recent = load_investigations()[:3]
    if recent:
        st.subheader("Continue a question")
        for record in recent:
            internal_link(
                record.get("title", "Untitled investigation"),
                "?page=Investigate&record=" + record["id"],
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
        details=evidence['details']
        if not isinstance(details,dict) or not all(k in details for k in ['mode','frequency','observations','valid_statistics','missing_periods','limitation','left_units','right_units','left_change_unit','right_change_unit','output_units','start','end']): raise ValueError('Invalid methodology')
        stability=evidence['stability']
        if not isinstance(stability,dict) or not all(k in stability for k in ['full_sample','first_half','second_half']): raise ValueError('Invalid stability')
        if any(not isinstance(v,dict) or not all(k in v for k in ['correlation','observations']) for v in stability.values()): raise ValueError('Invalid statistics')
        if not isinstance(evidence['lead_lag'],list): raise ValueError('Invalid lag estimates')
        if any(not isinstance(v,dict) or not all(k in v for k in ['lag','correlation','observations']) for v in evidence['lead_lag']): raise ValueError('Invalid lag fields')
        frame = pd.read_csv(
            StringIO(evidence["csv"]), index_col="date", parse_dates=["date"]
        )
        if frame.empty:
            raise ValueError("Empty evidence")
    return record
