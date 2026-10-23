"""Independent relationship notebook using existing connectors and registry."""

import json
from datetime import date, timedelta
from io import StringIO

import pandas as pd
import streamlit as st

from comparison_registry import COMPARISON_REGISTRY
from components.research.comparison import comparison_figure
from data.yahoo import get_fx_data_yahoo
from macro_engine.research.analytics import analyze, relationship
from macro_engine.research.notebook import load_investigations, save_investigation


def render_notebook():
    st.subheader("Independent relationship investigation")
    saved = load_investigations()
    by_id = {item["id"]: item for item in saved}
    if "notebook_open_after_save" in st.session_state:
        st.session_state["notebook_selected_id"] = st.session_state.pop(
            "notebook_open_after_save"
        )
        st.success("Investigation and calculation snapshot saved.")
    chosen = st.selectbox(
        "Open saved investigation",
        [None] + list(by_id),
        format_func=lambda i: (
            "New investigation" if i is None else by_id[i].get("title", i)
        ),
        key="notebook_selected_id",
    )
    record = {} if chosen is None else by_id[chosen]
    suffix = record.get("id", "new")
    options = sorted(COMPARISON_REGISTRY)
    left_name = st.selectbox(
        "Left indicator",
        options,
        index=options.index(record.get("left", options[0])),
        key=f"left_{suffix}",
    )
    right_name = st.selectbox(
        "Right indicator",
        options,
        index=options.index(record.get("right", options[1])),
        key=f"right_{suffix}",
    )
    title = st.text_input(
        "Investigation title",
        record.get("title", "Relationship investigation"),
        key=f"title_{suffix}",
    )
    hypothesis = st.text_area(
        "Hypothesis", record.get("hypothesis", ""), key=f"hypothesis_{suffix}"
    )
    start = st.date_input(
        "Sample start",
        date.fromisoformat(record.get("start", "2000-01-01")),
        key=f"start_{suffix}",
    )
    end = st.date_input(
        "Sample end",
        date.fromisoformat(record.get("end", date.today().isoformat())),
        key=f"end_{suffix}",
    )
    modes = [
        "Price",
        "Changes",
        "Percentage Change",
        "Relative Performance",
        "Ratio",
        "Rolling Correlation",
        "Drawdown",
        "Rolling Volatility",
        "Yield Spread",
    ]
    mode = st.selectbox(
        "Transformation",
        modes,
        index=modes.index(record.get("mode", "Changes")),
        key=f"mode_{suffix}",
    )
    window = int(
        st.number_input(
            "Window in comparison periods",
            3,
            1000,
            int(record.get("window", 12)),
            key=f"window_{suffix}",
        )
    )
    supporting = st.text_area(
        "Supporting evidence", record.get("supporting", ""), key=f"support_{suffix}"
    )
    counterarguments = st.text_area(
        "Counterarguments and alternative explanations",
        record.get("counterarguments", ""),
        key=f"counter_{suffix}",
    )
    if st.button("Run investigation", key=f"run_{suffix}"):
        if start > end or left_name == right_name:
            st.warning("Choose two different indicators and a valid sample period.")
            return
        try:

            def load(name):
                config = COMPARISON_REGISTRY[name]
                frame = (
                    config["loader"]()
                    if config["kind"] == "function"
                    else get_fx_data_yahoo(
                        config["loader"],
                        start_date=start,
                        end_date=end + timedelta(days=1),
                    )
                )
                if (
                    frame is None
                    or frame.empty
                    or not {"date", "value"}.issubset(frame.columns)
                ):
                    raise RuntimeError(
                        f"No observations are available for {name}. Try another source or series."
                    )
                frame = frame.copy()
                frame["date"] = pd.to_datetime(frame.date)
                return frame[
                    (frame.date >= pd.Timestamp(start))
                    & (frame.date <= pd.Timestamp(end))
                ], config["metadata"]

            a, am = load(left_name)
            b, bm = load(right_name)
            values, details = analyze(a, b, am, bm, mode, window=window)
            changed, _ = analyze(a, b, am, bm, "Changes")
            evidence = relationship(changed, window=window)
            st.session_state[f"evidence_{suffix}"] = {
                "settings": [left_name, right_name, str(start), str(end), mode, window],
                "csv": values.to_csv(index_label="date"),
                "source_csv": {
                    "left": a.to_csv(index=False),
                    "right": b.to_csv(index=False),
                },
                "details": details,
                "html": comparison_figure(
                    values, details, left_name, right_name
                ).to_html(include_plotlyjs=True),
                "lead_lag": evidence["lead_lag"],
                "stability": {
                    k: evidence[k] for k in ("full_sample", "first_half", "second_half")
                },
                "rolling": evidence["rolling"],
                "values": values,
            }
        except (ValueError, RuntimeError, KeyError) as exc:
            st.warning(str(exc))
        except OSError:
            st.warning(
                "The data provider is temporarily unavailable. Try another source or retry later."
            )
    evidence = st.session_state.get(f"evidence_{suffix}")
    if not evidence and record.get("evidence"):
        st.caption(
            "Saved evidence snapshot. Run again to refresh data; the snapshot records the original calculation."
        )
        snapshot = record["evidence"]
        values = pd.read_csv(
            StringIO(snapshot["csv"]), index_col="date", parse_dates=["date"]
        )
        rolling = (
            pd.read_csv(
                StringIO(snapshot["rolling_csv"]), index_col=0, parse_dates=[0]
            ).iloc[:, 0]
            if snapshot.get("rolling_csv")
            else pd.Series(dtype=float)
        )
        evidence = {
            **snapshot,
            "values": values,
            "rolling": rolling,
            "settings": [
                record["left"],
                record["right"],
                record["start"],
                record["end"],
                record["mode"],
                record["window"],
            ],
            "html": comparison_figure(
                values, snapshot["details"], record["left"], record["right"]
            ).to_html(include_plotlyjs=True),
        }
    if evidence and evidence["settings"] == [
        left_name,
        right_name,
        str(start),
        str(end),
        mode,
        window,
    ]:
        st.plotly_chart(
            comparison_figure(
                evidence["values"], evidence["details"], left_name, right_name
            ),
            use_container_width=True,
        )
        details = evidence["details"]
        st.caption(
            f"{details['frequency'].title()} comparison; {details['observations']} paired levels, {details['valid_statistics']} valid transformed observations; {details['missing_periods']} missing periods."
        )
        st.caption(details["limitation"])
        with st.expander("Full methodology and data coverage"):
            st.json(details)
        st.dataframe(evidence["lead_lag"])
        st.dataframe(
            [
                {"Sample": key.replace("_", " ").title(), **value}
                for key, value in evidence["stability"].items()
            ]
        )
        if not evidence["rolling"].dropna().empty:
            st.line_chart(evidence["rolling"].rename("Rolling correlation of changes"))
        else:
            st.info(
                "No valid rolling correlation is available for this window and sample."
            )
        st.caption(
            "Positive lag: left leads right. Exploratory correlations; no significance, causal or predictive claim. Lag searches entail multiple comparisons."
        )
        payload = {
            "title": title,
            "left": left_name,
            "right": right_name,
            "hypothesis": hypothesis,
            "start": str(start),
            "end": str(end),
            "mode": mode,
            "window": window,
            "supporting": supporting,
            "counterarguments": counterarguments,
            "evidence": {
                "rolling_csv": evidence["rolling"].to_csv(index_label="date"),
                **{
                    k: evidence[k]
                    for k in ("details", "lead_lag", "stability", "csv", "source_csv")
                },
            },
        }
        if st.button("Save investigation locally", key=f"save_{suffix}"):
            saved_record = save_investigation(
                payload, investigation_id=record.get("id")
            )
            st.session_state[f"evidence_{saved_record['id']}"] = evidence
            st.session_state["notebook_open_after_save"] = saved_record["id"]
            st.rerun()
        st.download_button(
            "Export investigation",
            json.dumps(payload, indent=2),
            "investigation.json",
            "application/json",
        )
        st.download_button(
            "Export observations", evidence["csv"], "investigation.csv", "text/csv"
        )
        st.download_button(
            "Export research chart", evidence["html"], "investigation.html", "text/html"
        )
