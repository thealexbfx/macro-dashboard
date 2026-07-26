from __future__ import annotations

from typing import Any

import streamlit as st


def _format_date(value: Any) -> str:
    if value is None:
        return "Unavailable"

    try:
        return value.strftime("%b %Y")
    except (AttributeError, ValueError):
        return str(value)


def _format_value(value: Any) -> str:
    if value is None:
        return "Unavailable"

    if isinstance(value, float):
        return f"{value:,.2f}"

    return str(value)


def render_model_indicator_inventory(result: Any) -> None:
    """
    Display the indicators actually used in an environment-engine run.

    The hierarchy is derived directly from:

    Environment Result
        -> Pillar Results
        -> Bucket Results
        -> Indicator Results

    No indicator names or model structure are hardcoded into the UI.
    """
    pillar_results = getattr(result, "pillar_results", ())

    if not pillar_results:
        return

    total_buckets = sum(
        len(getattr(pillar, "bucket_results", ()))
        for pillar in pillar_results
    )

    total_indicators = sum(
        len(getattr(bucket, "indicator_results", ()))
        for pillar in pillar_results
        for bucket in getattr(pillar, "bucket_results", ())
    )

    st.markdown("## Model Indicator Inventory")
    st.markdown(
        "Review the indicators included in each macro pillar and "
        "the model buckets they support."
    )

    with st.expander(
        (
            f"View {total_indicators} indicators across "
            f"{total_buckets} model buckets"
        ),
        expanded=False,
    ):
        pillar_tabs = st.tabs(
            [
                getattr(pillar, "name", "Pillar")
                for pillar in pillar_results
            ]
        )

        for tab, pillar in zip(
            pillar_tabs,
            pillar_results,
            strict=True,
        ):
            with tab:
                bucket_results = getattr(
                    pillar,
                    "bucket_results",
                    (),
                )

                if not bucket_results:
                    st.info(
                        "No completed model buckets are available "
                        "for this pillar."
                    )
                    continue

                for bucket in bucket_results:
                    indicator_results = getattr(
                        bucket,
                        "indicator_results",
                        (),
                    )

                    with st.expander(
                        (
                            f"{bucket.name} "
                            f"· {len(indicator_results)} indicators"
                        ),
                        expanded=False,
                    ):
                        if not indicator_results:
                            st.caption(
                                "No completed indicator results "
                                "are available."
                            )
                            continue

                        for indicator in indicator_results:
                            st.markdown(
                                f"**{indicator.name}**"
                            )

                            columns = st.columns(
                                [1.25, 1, 1, 1]
                            )

                            with columns[0]:
                                st.caption("Latest observation")
                                st.write(
                                    _format_date(
                                        indicator.latest_date
                                    )
                                )

                            with columns[1]:
                                st.caption("Latest value")
                                st.write(
                                    _format_value(
                                        indicator.latest_value
                                    )
                                )

                            with columns[2]:
                                st.caption("State")
                                st.write(
                                    indicator.state_label
                                )

                            with columns[3]:
                                st.caption("Trend")
                                st.write(
                                    indicator.trend_label
                                )

                            st.caption(
                                "Confidence "
                                f"{indicator.confidence_score:.0%}"
                            )

                            st.divider()