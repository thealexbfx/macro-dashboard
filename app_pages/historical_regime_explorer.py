from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pandas as pd
import streamlit as st

from macro_engine.historical.cross_asset import format_outcome
from macro_engine.historical.report import (
    HistoricalRegimeReport,
    build_historical_regime_report,
)

from macro_engine.utils.timing import log_runtime


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SP500_HISTORY_FILE = (
    PROJECT_ROOT
    / "research_outputs"
    / "cross_asset"
    / "sp500"
    / "sp500_environment_history.csv"
)


ASSET_UNITS = {
    "S&P 500": "percent",
    "US 10Y": "basis_points",
    "Gold": "percent",
    "WTI": "percent",
    "DXY": "percent",
}


def _html(content: str) -> None:
    st.html(
        dedent(content).strip()
    )

def inject_historical_explorer_css() -> None:
    st.markdown(
        """
        <style>
        .hre-header {
            margin-bottom: 24px;
        }

        .hre-title {
            color: #102033;
            font-size: 30px;
            font-weight: 700;
            letter-spacing: -0.7px;
            margin-bottom: 4px;
        }

        .hre-subtitle {
            color: #6b7788;
            font-size: 13px;
            margin-bottom: 18px;
        }

        .hre-section-title {
            color: #102033;
            font-size: 21px;
            font-weight: 700;
            letter-spacing: -0.3px;
            margin-top: 12px;
            margin-bottom: 14px;
        }

        .hre-metric-card {
            background: #ffffff;
            border: 1px solid #dfe4ea;
            border-radius: 8px;
            padding: 17px 18px;
            min-height: 96px;
        }

        .hre-metric-label {
            color: #687588;
            font-size: 12px;
            margin-bottom: 8px;
        }

        .hre-metric-value {
            color: #102033;
            font-size: 22px;
            font-weight: 700;
        }

        .hre-warning {
            background: #fff9e8;
            border: 1px solid #f1df9d;
            border-radius: 8px;
            padding: 15px 18px;
            color: #4c4530;
            font-size: 13px;
            margin-top: 15px;
        }

        .hre-info {
            background: #eef6ff;
            border: 1px solid #cfe2f7;
            border-radius: 8px;
            padding: 14px 17px;
            color: #31587d;
            font-size: 13px;
            margin-top: 14px;
        }

        .hre-detail-card {
            background: #ffffff;
            border: 1px solid #dfe4ea;
            border-radius: 8px;
            padding: 18px;
            height: 100%;
        }

        .hre-detail-heading {
            color: #102033;
            font-size: 15px;
            font-weight: 700;
            margin-bottom: 13px;
        }

        .hre-detail-row {
            display: flex;
            justify-content: space-between;
            gap: 18px;
            padding: 5px 0;
            border-bottom: 1px solid #eef1f4;
            font-size: 13px;
        }

        .hre-detail-row:last-child {
            border-bottom: none;
        }

        .hre-detail-label {
            color: #667386;
        }

        .hre-detail-value {
            color: #102033;
            font-weight: 600;
            text-align: right;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid #dfe4ea;
            border-radius: 8px;
            overflow: hidden;
        }

        div[data-testid="stSelectbox"] label,
        div[data-testid="stRadio"] label {
            color: #607086;
            font-size: 12px;
        }

        div[data-testid="stHorizontalBlock"] {
            gap: 12px;
        }

        hr {
            border-color: #e1e5ea !important;
            margin-top: 28px !important;
            margin-bottom: 25px !important;
        }
        /* =========================================================
           HISTORICAL REGIME EXPLORER — PAGE HIERARCHY
           ========================================================= */

        .hre-page-header {
            max-width: 920px;
            margin: 18px auto 24px;
            text-align: center;
        }

        .hre-title {
            margin: 0;
            color: #10233f;
            font-size: 2.35rem;
            font-weight: 900;
            letter-spacing: -0.045em;
            line-height: 1.08;
        }

        .hre-subtitle {
            max-width: 730px;
            margin: 9px auto 0;
            color: #33465e;
            font-size: 0.98rem;
            font-weight: 550;
            line-height: 1.6;
        }

        .hre-reading-path {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex-wrap: wrap;
            gap: 0.55rem;

            margin-top: 13px;
            padding: 7px 12px;

            border: 1px solid #d8e1ea;
            border-radius: 999px;
            background: #f7f9fc;

            color: #40536b;
            font-size: 0.75rem;
            font-weight: 750;
        }

        .hre-reading-path span {
            color: #8a99aa;
        }


        /* ---------- Selector ---------- */

        div[data-testid="stSelectbox"] label p {
            color: #40536b !important;
            font-size: 0.74rem !important;
            font-weight: 800 !important;
        }


        /* ---------- Numbered section heading ---------- */

        .hre-section-header {
            display: flex;
            align-items: flex-start;
            gap: 1rem;

            margin: 2rem 0 1.1rem;
            padding-top: 1.6rem;

            border-top: 1px solid #d8e1ea;
        }

        .hre-section-number {
            display: flex;
            width: 34px;
            height: 34px;
            flex: 0 0 34px;

            align-items: center;
            justify-content: center;

            border-radius: 50%;
            background: #10233f;
            color: #ffffff;

            font-size: 0.72rem;
            font-weight: 850;
        }

        .hre-section-title {
            margin: 0;
            color: #10233f;
            font-size: 1.55rem;
            font-weight: 900;
            letter-spacing: -0.03em;
        }

        .hre-section-description {
            max-width: 760px;
            margin-top: 4px;

            color: #33465e;
            font-size: 0.9rem;
            font-weight: 550;
            line-height: 1.55;
        }


        /* ---------- Regime summary ---------- */

        .hre-regime-summary {
            overflow: hidden;
            margin-bottom: 0.9rem;

            border: 1px solid #d3dde7;
            border-left: 5px solid #2d5f9a;
            border-radius: 13px;
            background: #ffffff;

            box-shadow: 0 4px 14px rgba(15, 35, 63, 0.035);
        }

        .hre-regime-summary-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1.2rem;

            padding: 1.25rem 1.35rem;
        }

        .hre-regime-eyebrow {
            color: #52647b;
            font-size: 0.68rem;
            font-weight: 850;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .hre-regime-name {
            margin-top: 5px;
            color: #10233f;
            font-size: 1.55rem;
            font-weight: 900;
            letter-spacing: -0.025em;
        }

        .hre-regime-count {
            min-width: 155px;
            padding: 0.75rem 0.9rem;

            border-radius: 9px;
            background: #10233f;
        }

        .hre-regime-count span {
            display: block;
            color: #c2cede;
            font-size: 0.65rem;
            font-weight: 800;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }

        .hre-regime-count strong {
            display: block;
            margin-top: 4px;

            color: #ffffff;
            font-size: 1.35rem;
            font-weight: 900;
        }

        .hre-regime-description {
            padding: 0.9rem 1.35rem;

            border-top: 1px solid #dfe6ed;
            background: #f8fafc;

            color: #33465e;
            font-size: 0.9rem;
            font-weight: 550;
            line-height: 1.55;
        }


        /* ---------- Compact metric cards ---------- */

        .hre-metric-card {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;

            min-height: 68px;
            padding: 0.8rem 1rem;

            border: 1px solid #d8e1ea;
            border-radius: 10px;
            background: #ffffff;

            box-shadow: 0 3px 10px rgba(15, 35, 63, 0.03);
        }

        .hre-metric-label {
            margin: 0;

            color: #52647b;
            font-size: 0.68rem;
            font-weight: 850;
            letter-spacing: 0.055em;
            text-transform: uppercase;
        }

        .hre-metric-value {
            color: #10233f;
            font-size: 1.35rem;
            font-weight: 900;
            text-align: right;
        }


        /* ---------- Sample panel ---------- */

        .hre-sample-panel {
            display: flex;
            align-items: flex-start;
            gap: 0.9rem;

            margin-top: 1rem;
            padding: 1rem 1.1rem;

            border-radius: 11px;
        }

        .hre-sample-limited {
            border: 1px solid #ead4aa;
            border-left: 5px solid #c58b2b;
            background: #fffaf1;
        }

        .hre-sample-moderate {
            border: 1px solid #cfdde9;
            border-left: 5px solid #527ea8;
            background: #f5f9fd;
        }

        .hre-sample-established {
            border: 1px solid #c8e2d5;
            border-left: 5px solid #278063;
            background: #f4fbf7;
        }

        .hre-sample-icon {
            display: flex;
            width: 28px;
            height: 28px;
            flex: 0 0 28px;

            align-items: center;
            justify-content: center;

            border-radius: 50%;
            background: rgba(255, 255, 255, 0.7);

            color: #80571a;
            font-size: 0.78rem;
            font-weight: 900;
        }

        .hre-sample-eyebrow {
            color: #52647b;
            font-size: 0.66rem;
            font-weight: 850;
            letter-spacing: 0.055em;
            text-transform: uppercase;
        }

        .hre-sample-title {
            margin-top: 3px;

            color: #10233f;
            font-size: 1rem;
            font-weight: 900;
        }

        .hre-sample-text {
            max-width: 850px;
            margin-top: 4px;

            color: #33465e;
            font-size: 0.87rem;
            font-weight: 550;
            line-height: 1.55;
        }


        /* ---------- Responsive ---------- */

        @media (max-width: 800px) {
            .hre-title {
                font-size: 1.95rem;
            }

            .hre-regime-summary-top {
                align-items: stretch;
                flex-direction: column;
            }

            .hre-regime-count {
                width: 100%;
            }

            .hre-metric-card {
                align-items: flex-start;
                flex-direction: column;
            }

            .hre-metric-value {
                text-align: left;
            }
        }
        /* =========================================================
           HISTORICAL EXPLORER — TABLES AND EPISODE DETAIL
           ========================================================= */

        .hre-table-heading {
            margin: 1.15rem 0 0.65rem;
        }

        .hre-table-title {
            color: #10233f;
            font-size: 1rem;
            font-weight: 900;
        }

        .hre-table-description,
        .hre-detail-description {
            margin-top: 3px;
            color: #40536b;
            font-size: 0.82rem;
            font-weight: 550;
        }


        /* ---------- Dataframes ---------- */

        div[data-testid="stDataFrame"] {
            border: 1px solid #ccd8e3;
            border-radius: 10px;
            overflow: hidden;
            background: #ffffff;
            box-shadow: 0 3px 12px rgba(15, 35, 63, 0.035);
        }

        div[data-testid="stDataFrame"] * {
            font-size: 0.8rem;
        }


        /* ---------- Selected asset summary ---------- */

        .hre-asset-summary {
            overflow: hidden;
            margin: 0.9rem 0 1rem;
            border: 1px solid #d4dee8;
            border-radius: 12px;
            background: #ffffff;
        }

        .hre-asset-summary-heading {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            padding: 1rem 1.2rem;
            border-bottom: 1px solid #dfe6ed;
            background: #f8fafc;
        }

        .hre-asset-summary-eyebrow {
            color: #52647b;
            font-size: 0.67rem;
            font-weight: 850;
            letter-spacing: 0.055em;
            text-transform: uppercase;
        }

        .hre-asset-summary-name {
            margin-top: 4px;
            color: #10233f;
            font-size: 1.3rem;
            font-weight: 900;
        }

        .hre-asset-summary-horizon {
            padding: 6px 10px;
            border-radius: 999px;
            background: #eaf0f7;
            color: #365b88;
            font-size: 0.7rem;
            font-weight: 800;
        }

        .hre-asset-summary-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }

        .hre-asset-summary-metric {
            padding: 1rem 1.15rem;
            border-left: 1px solid #e1e7ee;
        }

        .hre-asset-summary-metric:first-child {
            border-left: none;
        }

        .hre-asset-summary-metric span {
            display: block;
            color: #52647b;
            font-size: 0.66rem;
            font-weight: 850;
            letter-spacing: 0.045em;
            text-transform: uppercase;
        }

        .hre-asset-summary-metric strong {
            display: block;
            margin-top: 6px;
            color: #10233f;
            font-size: 1.05rem;
            font-weight: 900;
        }


        /* ---------- Methodology notes ---------- */

        .hre-methodology-note {
            display: flex;
            gap: 0.6rem;
            margin-top: 0.8rem;
            padding: 0.85rem 1rem;
            border-left: 4px solid #6d94b8;
            border-radius: 5px;
            background: #f4f8fc;
            color: #33465e;
            font-size: 0.82rem;
            line-height: 1.5;
        }

        .hre-methodology-note strong {
            flex: 0 0 auto;
            color: #10233f;
        }


        /* ---------- Episode history ---------- */

        .hre-episode-count-panel {
            min-height: 64px;
            padding: 0.8rem 1rem;
            border: 1px solid #d8e1ea;
            border-radius: 9px;
            background: #f8fafc;
        }

        .hre-episode-count-panel span {
            display: block;
            color: #52647b;
            font-size: 0.66rem;
            font-weight: 850;
            text-transform: uppercase;
        }

        .hre-episode-count-panel strong {
            display: block;
            margin-top: 5px;
            color: #10233f;
            font-size: 0.88rem;
            font-weight: 800;
        }


        /* ---------- Selected episode ---------- */

        .hre-selected-episode {
            display: grid;
            grid-template-columns:
                minmax(0, 1.4fr)
                minmax(0, 1fr)
                minmax(0, 1fr);
            margin: 0.9rem 0 1rem;
            border: 1px solid #d5dee7;
            border-radius: 11px;
            background: #f8fafc;
        }

        .hre-selected-episode > div {
            padding: 0.9rem 1rem;
            border-left: 1px solid #dfe6ed;
        }

        .hre-selected-episode > div:first-child {
            border-left: none;
        }

        .hre-selected-episode span {
            display: block;
            color: #52647b;
            font-size: 0.65rem;
            font-weight: 850;
            letter-spacing: 0.045em;
            text-transform: uppercase;
        }

        .hre-selected-episode strong {
            display: block;
            margin-top: 5px;
            color: #10233f;
            font-size: 0.88rem;
            font-weight: 850;
        }


        /* ---------- Entry conditions ---------- */

        .hre-entry-card {
            height: 100%;
            overflow: hidden;
            border: 1px solid #d5dee7;
            border-radius: 11px;
            background: #ffffff;
        }

        .hre-entry-card-header {
            padding: 1rem 1.15rem;
            border-bottom: 1px solid #dfe6ed;
            background: #10233f;
        }

        .hre-entry-eyebrow {
            color: #bdcad9;
            font-size: 0.66rem;
            font-weight: 850;
            letter-spacing: 0.055em;
            text-transform: uppercase;
        }

        .hre-entry-date {
            margin-top: 4px;
            color: #ffffff;
            font-size: 1.2rem;
            font-weight: 900;
        }

        .hre-entry-card-body {
            padding: 0.35rem 1.1rem;
        }

        .hre-entry-row {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            padding: 0.72rem 0;
            border-top: 1px solid #e8edf2;
        }

        .hre-entry-row:first-child {
            border-top: none;
        }

        .hre-entry-row span {
            color: #40536b;
            font-size: 0.82rem;
            font-weight: 600;
        }

        .hre-entry-row strong {
            color: #10233f;
            font-size: 0.84rem;
            font-weight: 850;
            text-align: right;
        }

        .hre-outcomes-heading {
            margin-bottom: 0.65rem;
        }

        .hre-detail-heading {
            color: #10233f;
            font-size: 1.05rem;
            font-weight: 900;
        }


        /* ---------- Responsive ---------- */

        @media (max-width: 850px) {
            .hre-asset-summary-grid,
            .hre-selected-episode {
                grid-template-columns: 1fr;
            }

            .hre-asset-summary-metric,
            .hre-selected-episode > div {
                border-left: none;
                border-top: 1px solid #e1e7ee;
            }

            .hre-asset-summary-metric:first-child,
            .hre-selected-episode > div:first-child {
                border-top: none;
            }

            .hre-asset-summary-heading {
                align-items: flex-start;
                flex-direction: column;
            }

            .hre-methodology-note {
                flex-direction: column;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_available_environments() -> list[str]:
    with log_runtime(
        "Load available historical environments"
    ):
        history = pd.read_csv(
            SP500_HISTORY_FILE
        )

        return (
            history["us_environment"]
            .dropna()
            .astype(str)
            .drop_duplicates()
            .sort_values()
            .tolist()
        )


@st.cache_data(show_spinner=False)
def load_regime_report(
    environment: str,
) -> HistoricalRegimeReport:
    with log_runtime(
        f"Historical regime report: {environment}"
    ):
        return build_historical_regime_report(
            environment=environment,
            horizons=(1, 3, 6),
        )


def format_score(value: object) -> str:
    if value is None or pd.isna(value):
        return "N/A"

    return f"{float(value):+.2f}"


def format_ratio(value: object) -> str:
    if value is None or pd.isna(value):
        return "N/A"

    return f"{float(value):.0%}"


def render_header() -> None:
    _html(
        """
        <div class="hre-page-header">
            <div class="hre-title">
                Historical Regime Explorer
            </div>

            <div class="hre-subtitle">
                Explore how major assets performed after comparable
                macro environments appeared historically.
            </div>

            <div class="hre-reading-path">
                Regime Summary
                <span>→</span>
                Cross-Asset Outcomes
                <span>→</span>
                Historical Episodes
                <span>→</span>
                Episode Detail
            </div>
        </div>
        """
    )


def render_metric_card(
    label: str,
    value: str,
) -> None:
    st.markdown(
        f"""
        <div class="hre-metric-card">
            <div class="hre-metric-label">{label}</div>
            <div class="hre-metric-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_episode_metrics(
    report: HistoricalRegimeReport,
) -> None:
    completed = int(
        report.raw_episodes["next_environment"]
        .notna()
        .sum()
    )

    columns = st.columns(4)

    with columns[0]:
        render_metric_card(
            "Historical Episodes",
            str(report.episode_count),
        )

    with columns[1]:
        render_metric_card(
            "Average Duration",
            f"{report.average_duration_months:.1f} months",
        )

    with columns[2]:
        render_metric_card(
            "Median Duration",
            f"{report.median_duration_months:.1f} months",
        )

    with columns[3]:
        render_metric_card(
            "Completed Episodes",
            str(completed),
        )

def render_regime_summary(
    report: HistoricalRegimeReport,
) -> None:
    _html(
        f"""
        <section class="hre-regime-summary">
            <div class="hre-regime-summary-top">
                <div>
                    <div class="hre-regime-eyebrow">
                        Selected Environment
                    </div>

                    <div class="hre-regime-name">
                        {report.environment}
                    </div>
                </div>

                <div class="hre-regime-count">
                    <span>Historical Episodes</span>
                    <strong>{report.episode_count}</strong>
                </div>
            </div>

            <div class="hre-regime-description">
                Historical outcomes are measured from the first month
                in which this macro environment appeared.
            </div>
        </section>
        """
    )

def render_sample_warning(
    report: HistoricalRegimeReport,
) -> None:
    if report.episode_count >= 15:
        quality_label = "Established Sample"
        quality_text = (
            f"{report.episode_count} distinct historical episodes are "
            "available for this environment."
        )
        quality_class = "hre-sample-established"

    elif report.episode_count >= 10:
        quality_label = "Moderate Sample"
        quality_text = (
            f"{report.episode_count} distinct historical episodes are "
            "available. The results provide useful historical context, "
            "but should not be treated as a forecast."
        )
        quality_class = "hre-sample-moderate"

    else:
        quality_label = "Limited Sample"
        quality_text = (
            f"Only {report.episode_count} distinct historical episodes "
            "are available. Treat the results as descriptive historical "
            "evidence rather than a forecast."
        )
        quality_class = "hre-sample-limited"

    _html(
        f"""
        <section class="hre-sample-panel {quality_class}">
            <div class="hre-sample-icon">!</div>

            <div>
                <div class="hre-sample-eyebrow">
                    Sample Quality
                </div>

                <div class="hre-sample-title">
                    {quality_label}
                </div>

                <div class="hre-sample-text">
                    {quality_text}
                </div>
            </div>
        </section>
        """
    )

def render_section_header(
    *,
    number: str,
    title: str,
    description: str,
) -> None:
    _html(
        f"""
        <div class="hre-section-header">
            <div class="hre-section-number">
                {number}
            </div>

            <div>
                <div class="hre-section-title">
                    {title}
                </div>

                <div class="hre-section-description">
                    {description}
                </div>
            </div>
        </div>
        """
    )

def _summary_value(
    row: pd.Series,
    column: str,
) -> str:
    value = row.get(column)

    if value is None or pd.isna(value):
        return "N/A"

    return str(value)


def _best_supported_row(
    asset_summary: pd.DataFrame,
) -> pd.Series:
    if asset_summary.empty:
        raise ValueError(
            "Asset summary cannot be empty."
        )

    frequency_columns = [
        "Positive return frequency",
        "Yield-rise frequency",
        "Positive frequency",
    ]

    frequency_column = next(
        (
            column
            for column in frequency_columns
            if column in asset_summary.columns
        ),
        None,
    )

    if frequency_column is None:
        return asset_summary.iloc[0]

    numeric_frequency = pd.to_numeric(
        asset_summary[frequency_column]
        .astype(str)
        .str.replace("%", "", regex=False),
        errors="coerce",
    )

    if numeric_frequency.notna().any():
        return asset_summary.loc[
            numeric_frequency.idxmax()
        ]

    return asset_summary.iloc[0]


def render_selected_asset_summary(
    *,
    selected_asset: str,
    asset_summary: pd.DataFrame,
    frequency_label: str,
) -> None:
    best_row = _best_supported_row(
        asset_summary
    )

    horizon = _summary_value(
        best_row,
        "Horizon",
    )

    average = _summary_value(
        best_row,
        "Average",
    )

    frequency = _summary_value(
        best_row,
        frequency_label,
    )

    best = _summary_value(
        best_row,
        "Best",
    )

    worst = _summary_value(
        best_row,
        "Worst",
    )

    _html(
        f"""
        <section class="hre-asset-summary">
            <div class="hre-asset-summary-heading">
                <div>
                    <div class="hre-asset-summary-eyebrow">
                        Selected Asset
                    </div>

                    <div class="hre-asset-summary-name">
                        {selected_asset}
                    </div>
                </div>

                <div class="hre-asset-summary-horizon">
                    Best historical consistency: {horizon}
                </div>
            </div>

            <div class="hre-asset-summary-grid">
                <div class="hre-asset-summary-metric">
                    <span>Average Outcome</span>
                    <strong>{average}</strong>
                </div>

                <div class="hre-asset-summary-metric">
                    <span>{frequency_label}</span>
                    <strong>{frequency}</strong>
                </div>

                <div class="hre-asset-summary-metric">
                    <span>Best Outcome</span>
                    <strong>{best}</strong>
                </div>

                <div class="hre-asset-summary-metric">
                    <span>Worst Outcome</span>
                    <strong>{worst}</strong>
                </div>
            </div>
        </section>
        """
    )

def render_asset_summary(
    report: HistoricalRegimeReport,
) -> None:
    render_section_header(
        number="02",
        title="Cross-Asset Outcomes",
        description=(
            "Compare the average, median and range of asset "
            "performance following each historical regime entry."
        ),
    )

    asset_options = (
        report.summary["Asset"]
        .drop_duplicates()
        .tolist()
    )

    selector_left, selector_col, selector_right = st.columns(
        [1.2, 1.6, 1.2]
    )

    with selector_col:
        selected_asset = st.selectbox(
            "Asset",
            options=asset_options,
            index=0,
            key="historical_regime_asset",
        )

    asset_summary = (
        report.summary[
            report.summary["Asset"].eq(
                selected_asset
            )
        ]
        .drop(columns=["Asset"])
        .copy()
    )

    frequency_label = (
        "Yield-rise frequency"
        if selected_asset == "US 10Y"
        else "Positive return frequency"
    )

    asset_summary = asset_summary.rename(
        columns={
            "Positive frequency": frequency_label,
        }
    )

    asset_summary["Horizon"] = (
        asset_summary["Horizon"]
        .astype(str)
        .add("M")
    )

    render_selected_asset_summary(
        selected_asset=selected_asset,
        asset_summary=asset_summary,
        frequency_label=frequency_label,
    )

    _html(
        """
        <div class="hre-table-heading">
            <div class="hre-table-title">
                Horizon Comparison
            </div>

            <div class="hre-table-description">
                Outcomes across all distinct regime-entry episodes.
            </div>
        </div>
        """
    )

    st.dataframe(
        asset_summary,
        hide_index=True,
        use_container_width=True,
        height=178,
    )

    if selected_asset == "US 10Y":
        frequency_explanation = (
            "Yield-rise frequency measures how often the "
            "10-year Treasury yield increased after regime entry."
        )
    else:
        frequency_explanation = (
            "Positive return frequency measures how often the "
            "asset produced a positive forward return."
        )

    _html(
        f"""
        <div class="hre-methodology-note">
            <strong>How to read this table</strong>

            <span>
                Each observation represents one distinct regime-entry
                episode rather than one monthly data point.
                {frequency_explanation}
            </span>
        </div>
        """
    )


def render_episode_history(
    report: HistoricalRegimeReport,
) -> None:
    render_section_header(
        number="03",
        title="Historical Episodes",
        description=(
            "Inspect each distinct period in which the selected "
            "macro environment appeared and compare subsequent outcomes."
        ),
    )

    control_col, summary_col = st.columns(
        [1, 2]
    )

    with control_col:
        selected_horizon = st.radio(
            "Forward Horizon",
            options=[1, 3, 6],
            index=2,
            horizontal=True,
            format_func=lambda horizon: (
                f"{horizon} Month"
                if horizon == 1
                else f"{horizon} Months"
            ),
            key="historical_regime_horizon",
        )

    with summary_col:
        _html(
            f"""
            <div class="hre-episode-count-panel">
                <span>Table View</span>

                <strong>
                    Showing {selected_horizon}-month outcomes across
                    {report.episode_count} distinct episodes
                </strong>
            </div>
            """
        )

    display = report.episode_display.copy()

    outcome_columns = [
        column
        for column in display.columns
        if column.endswith(
            f" {selected_horizon}M"
        )
    ]

    identity_columns = [
        "Entry",
        "End",
        "Duration",
        "Previous",
        "Next",
    ]

    columns = [
        column
        for column in (
            identity_columns + outcome_columns
        )
        if column in display.columns
    ]

    st.dataframe(
        display[columns],
        hide_index=True,
        use_container_width=True,
        height=min(
            420,
            38 + len(display) * 35,
        ),
    )

    _html(
        """
        <div class="hre-methodology-note">
            <strong>Episode methodology</strong>

            <span>
                Forward outcomes are measured from the first month
                in which the regime appeared. Each row represents
                one distinct episode.
            </span>
        </div>
        """
    )
    
def get_episode_outcome(
    episode: pd.Series,
    asset_name: str,
    horizon: int,
) -> object:
    prefixes = {
        "S&P 500": "sandp_500",
        "US 10Y": "us_10y",
        "Gold": "gold",
        "WTI": "wti",
        "DXY": "dxy",
    }

    column = f"{prefixes[asset_name]}_{horizon}m"

    if column in episode.index:
        return episode[column]

    return None

def render_entry_conditions(
    episode: pd.Series,
) -> None:
    rows = [
        (
            "Activity Score",
            format_score(
                episode["entry_activity_score"]
            ),
        ),
        (
            "Inflation Score",
            format_score(
                episode["entry_inflation_score"]
            ),
        ),
        (
            "Financial Score",
            format_score(
                episode["entry_financial_score"]
            ),
        ),
        (
            "Confidence",
            format_ratio(
                episode["entry_confidence"]
            ),
        ),
        (
            "Conviction",
            format_ratio(
                episode["entry_conviction"]
            ),
        ),
        (
            "Previous Environment",
            episode["previous_environment"],
        ),
        (
            "Next Environment",
            episode["next_environment"],
        ),
    ]

    rows_html = "".join(
        f"""
        <div class="hre-entry-row">
            <span>{label}</span>
            <strong>{value}</strong>
        </div>
        """
        for label, value in rows
    )

    _html(
        f"""
        <section class="hre-entry-card">
            <div class="hre-entry-card-header">
                <div>
                    <div class="hre-entry-eyebrow">
                        Regime Entry
                    </div>

                    <div class="hre-entry-date">
                        {episode["start_month"]}
                    </div>
                </div>
            </div>

            <div class="hre-entry-card-body">
                {rows_html}
            </div>
        </section>
        """
    )

def render_episode_details(
    report: HistoricalRegimeReport,
) -> None:
    render_section_header(
        number="04",
        title="Episode Detail",
        description=(
            "Review the model conditions recorded at regime entry "
            "and the forward asset outcomes from that point."
        ),
    )

    raw = report.raw_episodes.copy()

    raw["episode_label"] = raw.apply(
        lambda row: (
            f"{row['start_month']} → "
            f"{row['end_month']} "
            f"({int(row['duration_months'])} months)"
        ),
        axis=1,
    )

    selector_left, selector_col, selector_right = st.columns(
        [0.6, 2.8, 0.6]
    )

    with selector_col:
        selected_episode = st.selectbox(
            "Historical Episode",
            options=raw["episode_label"].tolist(),
            index=len(raw) - 1,
            key="historical_episode_detail",
        )

    episode = raw.loc[
        raw["episode_label"].eq(
            selected_episode
        )
    ].iloc[0]

    _html(
        f"""
        <section class="hre-selected-episode">
            <div>
                <span>Selected Episode</span>
                <strong>{selected_episode}</strong>
            </div>

            <div>
                <span>Previous Environment</span>
                <strong>
                    {episode["previous_environment"]}
                </strong>
            </div>

            <div>
                <span>Next Environment</span>
                <strong>
                    {episode["next_environment"]}
                </strong>
            </div>
        </section>
        """
    )

    left, right = st.columns(
        [1, 1.45]
    )

    with left:
        render_entry_conditions(
            episode
        )

    with right:
        outcome_records: list[
            dict[str, str]
        ] = []

        for asset_name, unit in (
            ASSET_UNITS.items()
        ):
            outcome_records.append(
                {
                    "Asset": asset_name,
                    "1M": format_outcome(
                        get_episode_outcome(
                            episode,
                            asset_name,
                            1,
                        ),
                        unit,
                    ),
                    "3M": format_outcome(
                        get_episode_outcome(
                            episode,
                            asset_name,
                            3,
                        ),
                        unit,
                    ),
                    "6M": format_outcome(
                        get_episode_outcome(
                            episode,
                            asset_name,
                            6,
                        ),
                        unit,
                    ),
                }
            )

        outcomes = pd.DataFrame(
            outcome_records
        )

        _html(
            """
            <div class="hre-outcomes-heading">
                <div class="hre-detail-heading">
                    Forward Outcomes
                </div>

                <div class="hre-detail-description">
                    Asset performance measured from the selected
                    regime-entry month.
                </div>
            </div>
            """
        )

        st.dataframe(
            outcomes,
            hide_index=True,
            use_container_width=True,
            height=215,
        )

    _html(
        """
        <div class="hre-methodology-note">
            <strong>Entry conditions</strong>

            <span>
                Scores and model confidence reflect the readings
                recorded when the historical environment first appeared.
            </span>
        </div>
        """
    )

def render_historical_regime_explorer_page() -> None:
    inject_historical_explorer_css()
    render_header()

    environments = load_available_environments()

    if not environments:
        st.warning(
            "No historical macro environments are currently available."
        )
        return

    requested_environment = st.query_params.get("environment")

    if requested_environment in environments:
        default_environment = requested_environment
    elif "Restrictive Reflation" in environments:
        default_environment = "Restrictive Reflation"
    else:
        default_environment = environments[0]

    left_space, selector_col, right_space = st.columns(
        [1.2, 2.4, 1.2]
    )

    with selector_col:
        selected_environment = st.selectbox(
            "Macro Environment",
            options=environments,
            index=environments.index(default_environment),
            key="historical_regime_environment",
        )

    report = load_regime_report(selected_environment)

    _html(
        """
        <div class="hre-section-header">
            <div class="hre-section-number">01</div>

            <div>
                <div class="hre-section-title">
                    Regime Summary
                </div>

                <div class="hre-section-description">
                    Review the frequency, duration and historical sample
                    quality of the selected macro environment.
                </div>
            </div>
        </div>
        """
    )

    render_regime_summary(report)
    render_episode_metrics(report)
    render_sample_warning(report)

    render_asset_summary(report)
    render_episode_history(report)
    render_episode_details(report)