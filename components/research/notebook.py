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
from macro_engine.research.presentation import (
    evidence_summary,
    stability_rows,
    rolling_diagnostics,
)
from macro_engine.research.notebook import load_investigations, save_investigation


def render_notebook():
    st.subheader("What do you want to investigate?")
    saved = load_investigations()
    by_id = {item["id"]: item for item in saved}
    if "notebook_open_after_save" in st.session_state:
        st.session_state["notebook_selected_id"] = st.session_state.pop(
            "notebook_open_after_save"
        )
        st.success("Investigation and calculation snapshot saved.")
    requested = st.query_params.get("record")
    if requested in by_id and st.session_state.get("opened_record") != requested:
        st.session_state["notebook_selected_id"] = requested
        st.session_state["opened_record"] = requested
    chosen = None
    if by_id:
        with st.expander("Switch investigation"):
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
    if any(
        record.get(side, options[i]) not in options
        for i, side in enumerate(("left", "right"))
    ):
        st.warning(
            "This saved investigation references a series no longer in the registry. Its original file remains unchanged; choose a new investigation to continue."
        )
        return

    title = st.text_input(
        "Investigation title",
        record.get("title", "Do yields and gold move together?"),
        key=f"title_{suffix}",
    )
    left_name = st.selectbox(
        "Left indicator",
        options,
        index=options.index(
            record.get(
                "left",
                st.query_params.get("left")
                if st.query_params.get("left") in options
                else "Commodities · Gold"
                if "Commodities · Gold" in options
                else options[0],
            )
        ),
        key=f"left_{suffix}",
    )
    right_name = st.selectbox(
        "Right indicator",
        options,
        index=options.index(
            record.get(
                "right",
                st.query_params.get("right")
                if st.query_params.get("right") in options
                else "Rates & Bonds · US 10Y"
                if "Rates & Bonds · US 10Y" in options
                else options[1],
            )
        ),
        key=f"right_{suffix}",
    )
    with st.expander("Options: sample, method and hypothesis"):
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
        st.caption(
            "Changes uses percentage returns for eligible prices and basis-point changes for yields. Statistical evidence always compares changes, even when the main chart displays levels."
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
        frequencies = ["Native alignment", "weekly", "monthly", "quarterly", "annual"]
        frequency = st.selectbox(
            "Comparison frequency",
            frequencies,
            index=frequencies.index(record.get("frequency", "Native alignment")),
            key=f"freq_{suffix}",
        )
        st.caption(
            "A coarser frequency uses the last observation in each period. Missing periods remain missing; finer-than-source sampling is not permitted."
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

            with st.spinner("Loading source observations and calculating evidence…"):
                a, am = load(left_name)
                b, bm = load(right_name)
            if frequency != "Native alignment":
                from dataclasses import replace
                from macro_engine.research.analytics import FREQUENCIES

                if any(
                    list(FREQUENCIES).index(frequency)
                    < list(FREQUENCIES).index(m.frequency)
                    for m in (am, bm)
                ):
                    raise ValueError("Choose a frequency no finer than either source.")
                am, bm = (
                    replace(am, frequency=frequency),
                    replace(bm, frequency=frequency),
                )
            values, details = analyze(a, b, am, bm, mode, window=window)
            changed, _ = analyze(a, b, am, bm, "Changes")
            evidence = relationship(changed, window=window)
            st.session_state[f"evidence_{suffix}"] = {
                "settings": [
                    left_name,
                    right_name,
                    str(start),
                    str(end),
                    mode,
                    window,
                    frequency,
                ],
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
                "changed_csv": changed.to_csv(index_label="date"),
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
            "Imported snapshot; values have not been independently verified. Run again to recalculate from providers." if record.get("imported") else "Saved evidence snapshot. Run again to refresh data; the snapshot records the original calculation."
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
                record.get("frequency", "Native alignment"),
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
        frequency,
    ]:
        st.subheader("What the data shows")
        st.info(
            evidence_summary(evidence["stability"], evidence["lead_lag"]).split(
                ". First-half"
            )[0]
        )
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
        with st.expander("Explore stability, rolling windows and lead/lag"):
            st.write(evidence_summary(evidence["stability"], evidence["lead_lag"]))
            st.markdown("##### Historical stability of changes")
            st.dataframe(
                stability_rows(evidence["stability"]),
                hide_index=True,
                use_container_width=True,
            )
            st.caption(
                "Descriptive |r| thresholds: <0.10 very weak; <0.30 weak; <0.50 moderate; <0.70 strong; otherwise very strong. These are not significance tests. Halves split the comparison grid, not the valid observation count."
            )
            with st.expander("Inspect individual lead/lag estimates"):
                rows = [
                    {
                        "Lag (comparison periods)": x["lag"],
                        "Relationship": "Same period"
                        if x["lag"] == 0
                        else f"Left leads right by {x['lag']}"
                        if x["lag"] > 0
                        else f"Right leads left by {-x['lag']}",
                        "Observations": x["observations"],
                        "Correlation": x["correlation"],
                    }
                    for x in evidence["lead_lag"]
                ]
                st.dataframe(rows, hide_index=True, use_container_width=True)
            st.markdown("##### Rolling correlation of changes")
            st.caption(
                f"{window} consecutive comparison periods, each with both changes available; no filling. A missing observation can invalidate several successive windows. Closed-market calendar days are not automatically missing observations."
            )
            valid_rolling = evidence["rolling"].dropna()
            if len(valid_rolling):
                st.caption(
                    f"Latest valid result: {valid_rolling.index[-1].date()} · r={valid_rolling.iloc[-1]:.3f}. {len(valid_rolling)} valid windows out of {len(evidence['rolling'])} comparison periods."
                )
            if len(evidence["rolling"]) and pd.isna(evidence["rolling"].iloc[-1]):
                st.warning(
                    "The latest comparison period has no valid rolling result; the latest valid result shown above is older."
                )
            if evidence.get("changed_csv"):
                changed = pd.read_csv(
                    StringIO(evidence["changed_csv"]),
                    index_col="date",
                    parse_dates=["date"],
                )
                with st.expander("Why are rolling results missing?"):
                    diagnostic = rolling_diagnostics(
                        changed, evidence["rolling"], window
                    )
                    st.dataframe(
                        [
                            {"Reason": label, "Periods": diagnostic[key]}
                            for key, label in [
                                ("warmup_periods", "Initial window warm-up"),
                                ("incomplete_windows", "Incomplete paired changes"),
                                (
                                    "undefined_complete_windows",
                                    "Complete window but undefined variation",
                                ),
                                ("valid_windows", "Valid rolling calculation"),
                            ]
                        ],
                        hide_index=True,
                        use_container_width=True,
                    )
            if not evidence["rolling"].dropna().empty:
                st.line_chart(
                    evidence["rolling"].rename("Rolling correlation of changes")
                )
            else:
                st.info(
                    "No valid rolling correlation is available for this window and sample."
                )
            st.caption(
                "Positive lag: left leads right. Exploratory correlations; no significance, causal or predictive claim. Lag searches entail multiple comparisons."
            )
        st.markdown("#### Your conclusion and next question")
        st.caption(
            "These editable notes are your interpretation, separate from calculated evidence. Consider alternative frequencies, crisis periods or real yields as further tests, not established explanations."
        )
        supporting = st.text_area(
            "Your conclusion", record.get("supporting", ""), key=f"support_{suffix}"
        )
        counterarguments = st.text_area(
            "Counterarguments and alternative explanations",
            record.get("counterarguments", ""),
            key=f"counter_{suffix}",
        )
        st.markdown("#### Keep this research")
        st.caption(
            "Local saves belong to this server and may be lost on a hosting restart. Export a copy for durable storage."
        )
        payload = {
            "title": title,
            "left": left_name,
            "right": right_name,
            "hypothesis": hypothesis,
            "start": str(start),
            "end": str(end),
            "frequency": frequency,
            "calculated_summary": evidence_summary(
                evidence["stability"], evidence["lead_lag"]
            ),
            "mode": mode,
            "window": window,
            "supporting": supporting,
            "counterarguments": counterarguments,
            "evidence": {
                "rolling_csv": evidence["rolling"].to_csv(index_label="date"),
                "changed_csv": evidence.get("changed_csv"),
                **{
                    k: evidence[k]
                    for k in ("details", "lead_lag", "stability", "csv", "source_csv")
                },
            },
        }
        if st.button("Save investigation locally", key=f"save_{suffix}"):
            try:
                saved_record = save_investigation(
                    payload, investigation_id=record.get("id")
                )
            except (OSError, ValueError):
                st.error(
                    "The investigation could not be saved locally. Export a copy below, or reduce the sample size if the record is too large."
                )
            else:
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
            "Export rolling correlations",
            evidence["rolling"].to_csv(index_label="date"),
            "rolling-correlations.csv",
            "text/csv",
        )
        st.download_button(
            "Export research chart", evidence["html"], "investigation.html", "text/html"
        )
