from __future__ import annotations

import streamlit as st
from textwrap import dedent

from macro_engine.utils.timing import log_runtime
from macro_engine.decision.assets import (
    build_workspace,
    get_available_assets,
)
from macro_engine.decision.workspace import DecisionWorkspaceResult

from macro_engine.decision.historical_context import (
    HistoricalContext,
)

from macro_engine.decision.snapshots import (
    DecisionSnapshot,
    SnapshotComparison,
    build_snapshot,
    compare_snapshots,
    find_last_material_change_date,
    load_latest_snapshot,
    save_snapshot,
)

@st.cache_data(
    ttl=1800,
    show_spinner=False,
)
def load_decision_workspace(
    asset_key: str,
    horizon_months: int,
) -> DecisionWorkspaceResult:
    with log_runtime(
        (
            "Decision workspace "
            f"{asset_key} "
            f"{horizon_months}M"
        )
    ):
        return build_workspace(
            asset_key=asset_key,
            horizon_months=horizon_months,
        )
def _format_score(value: float) -> str:
    return f"{value:+.2f}"

def _score_interpretation(value: float) -> str:
    if value >= 0.50:
        return "Strongly Bullish"

    if value >= 0.20:
        return "Moderately Bullish"

    if value > -0.20:
        return "Neutral"

    if value > -0.50:
        return "Moderately Bearish"

    return "Strongly Bearish"

def _format_percentage(value: float) -> str:
    return f"{value:.0%}"


def _direction_class(direction: str) -> str:
    direction_key = direction.lower()

    if direction_key == "bullish":
        return "ml-research-bullish"

    if direction_key == "bearish":
        return "ml-research-bearish"

    return "ml-research-neutral"


def _render_evidence_section(
    title: str,
    evidence: tuple,
    empty_message: str,
) -> None:
    _html(
        f"""
        <div class="ml-research-section-title">{title}</div>
        """
    )

    if not evidence:
        _html(
            f"""
            <div class="ml-research-empty">
                {empty_message}
            </div>
            """
        )
        return

    for item in evidence:
        _html(
            f"""
            <div class="ml-research-evidence">
                <div class="ml-research-evidence-category">
                    {item.category}
                </div>
                <div class="ml-research-evidence-message">
                    {item.message}
                </div>
                <div class="ml-research-evidence-source">
                    Source: {item.source}
                </div>
            </div>
            """
        )

def _format_return(value: float | None) -> str:
    if value is None:
        return "N/A"

    return f"{value:+.2%}"


def _format_price(value: float | None) -> str:
    if value is None:
        return "N/A"

    return f"{value:.4f}"

def _html(content: str) -> None:
    st.html(dedent(content).strip())

def _inject_research_workspace_css() -> None:
    st.markdown(
        """
        <style>
        .ml-research-page {
            max-width: 1180px;
            margin: 0 auto;
            padding: 0.5rem 0 3rem 0;
        }

        .ml-research-eyebrow {
            color: #64748b;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.45rem;
        }

        .ml-research-title {
            color: #0f172a;
            font-size: 2rem;
            font-weight: 700;
            letter-spacing: -0.03em;
            margin-bottom: 0.35rem;
        }

        .ml-research-subtitle {
            color: #64748b;
            font-size: 0.98rem;
            line-height: 1.55;
            margin-bottom: 1.6rem;
        }

        .ml-research-hero {
            background: #ffffff;
            border: 1px solid #dfe4ea;
            border-radius: 12px;
            padding: 1.6rem;
            margin-bottom: 1.25rem;
        }

        .ml-research-asset {
            color: #475569;
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }

        .ml-research-direction {
            font-size: 2.15rem;
            font-weight: 750;
            letter-spacing: -0.04em;
            margin-bottom: 0.45rem;
        }

        .ml-research-bullish {
            color: #237a57;
        }

        .ml-research-bearish {
            color: #a84545;
        }

        .ml-research-neutral {
            color: #8a6d1d;
        }

        .ml-research-score {
            color: #475569;
            font-size: 0.9rem;
        }

        .ml-research-metric {
            background: #ffffff;
            border: 1px solid #dfe4ea;
            border-radius: 10px;
            padding: 1.05rem 1.1rem;
            min-height: 108px;
        }

        .ml-research-metric-label {
            color: #64748b;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            margin-bottom: 0.45rem;
        }

        .ml-research-metric-value {
            color: #0f172a;
            font-size: 1.45rem;
            font-weight: 700;
        }

        .ml-research-card {
            background: #ffffff;
            border: 1px solid #dfe4ea;
            border-radius: 12px;
            padding: 1.45rem;
            margin-top: 1.25rem;
        }

        .ml-research-section-title {
            color: #0f172a;
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 0.9rem;
        }

        .ml-research-thesis {
            color: #263244;
            font-size: 0.98rem;
            line-height: 1.7;
        }

        .ml-research-evidence {
            border-top: 1px solid #edf0f3;
            padding: 0.95rem 0;
        }

        .ml-research-evidence:first-of-type {
            border-top: none;
            padding-top: 0;
        }

        .ml-research-evidence-category {
            color: #64748b;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.3rem;
        }

        .ml-research-evidence-message {
            color: #263244;
            font-size: 0.93rem;
            line-height: 1.55;
        }

        .ml-research-evidence-source {
            color: #94a3b8;
            font-size: 0.75rem;
            margin-top: 0.35rem;
        }

        .ml-research-empty {
            color: #64748b;
            font-size: 0.9rem;
        }

        .ml-research-limitation {
            color: #475569;
            font-size: 0.92rem;
            line-height: 1.55;
            padding: 0.55rem 0;
            border-top: 1px solid #edf0f3;
        }

        .ml-research-limitation:first-of-type {
            border-top: none;
            padding-top: 0;
        }

        .ml-research-date {
            color: #94a3b8;
            font-size: 0.78rem;
            margin-top: 1.25rem;
        }
        
        .ml-research-hero-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.6fr);
            gap: 1rem;
            margin-bottom: 1.1rem;
        }

        .ml-research-hero-main {
            background: #ffffff;
            border: 1px solid #d9e0e8;
            border-radius: 14px;
            padding: 1.75rem;
        }

        .ml-research-hero-side {
            background: #10233f;
            border: 1px solid #10233f;
            border-radius: 14px;
            padding: 1.55rem;
            color: #ffffff;
        }

        .ml-research-hero-side-label {
            color: #b7c4d6;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.07em;
            text-transform: uppercase;
            margin-bottom: 0.6rem;
        }

        .ml-research-hero-side-value {
            color: #ffffff;
            font-size: 1.85rem;
            font-weight: 750;
            letter-spacing: -0.03em;
            margin-bottom: 0.55rem;
        }

        .ml-research-hero-side-text {
            color: #d7e0eb;
            font-size: 0.91rem;
            line-height: 1.55;
        }

        .ml-section-heading {
            color: #102033;
            font-size: 1.35rem;
            font-weight: 750;
            letter-spacing: -0.02em;
            margin-top: 2rem;
            margin-bottom: 0.25rem;
        }

        .ml-section-description {
            color: #58687c;
            font-size: 0.93rem;
            line-height: 1.5;
            margin-bottom: 1rem;
        }

        .ml-context-card {
            background: #ffffff;
            border: 1px solid #d9e0e8;
            border-radius: 12px;
            padding: 1.35rem;
            height: 100%;
        }

        .ml-context-title {
            color: #102033;
            font-size: 1.05rem;
            font-weight: 750;
            margin-bottom: 1rem;
        }

        .ml-context-row {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            padding: 0.68rem 0;
            border-top: 1px solid #edf1f5;
        }

        .ml-context-row:first-of-type {
            border-top: none;
            padding-top: 0;
        }

        .ml-context-label {
            color: #617086;
            font-size: 0.88rem;
        }

        .ml-context-value {
            color: #14243a;
            font-size: 0.9rem;
            font-weight: 700;
            text-align: right;
        }

        .ml-return-positive {
            color: #167455;
        }

        .ml-return-negative {
            color: #b44444;
        }

        .ml-alignment-panel {
            border-radius: 14px;
            padding: 1.55rem;
            margin-top: 1rem;
        }

        .ml-alignment-confirmed {
            background: #edf8f3;
            border: 1px solid #b9dfcc;
        }

        .ml-alignment-divergent {
            background: #fff6e8;
            border: 1px solid #efd2a1;
        }

        .ml-alignment-mixed {
            background: #f3f6fa;
            border: 1px solid #d4dde8;
        }

        .ml-alignment-label {
            color: #102033;
            font-size: 1.35rem;
            font-weight: 750;
            margin-bottom: 0.35rem;
        }

        .ml-alignment-summary {
            color: #43536a;
            font-size: 0.94rem;
            line-height: 1.55;
        }

        .ml-status-card {
            border-radius: 14px;
            padding: 1.6rem;
            margin-top: 1rem;
        }

        .ml-status-ready {
            background: #eaf7f1;
            border: 1px solid #b8ddcc;
        }

        .ml-status-watch {
            background: #fff4df;
            border: 1px solid #edcb8c;
        }

        .ml-status-review {
            background: #eef3f9;
            border: 1px solid #ccd8e6;
        }

        .ml-status-label {
            color: #102033;
            font-size: 1.65rem;
            font-weight: 800;
            letter-spacing: -0.025em;
            margin-bottom: 0.5rem;
        }

        .ml-status-description {
            color: #43536a;
            font-size: 0.96rem;
            line-height: 1.6;
        }

        @media (max-width: 900px) {
            .ml-research-hero-grid {
                grid-template-columns: 1fr;
            }
        }
        
        .ml-compact-card {
            background: #ffffff;
            border: 1px solid #d8e0e9;
            border-radius: 12px;
            padding: 1rem 1.1rem;
            min-height: 96px;
            box-shadow: 0 2px 8px rgba(15, 35, 63, 0.04);
        }

        .ml-compact-label {
            color: #5c6b7e;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.045em;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }

        .ml-compact-value {
            color: #10233f;
            font-size: 1.55rem;
            font-weight: 800;
            letter-spacing: -0.025em;
        }

        .ml-compact-note {
            color: #66758a;
            font-size: 0.8rem;
            margin-top: 0.3rem;
        }

        .ml-positive-card {
            border-top: 3px solid #278063;
        }

        .ml-positive-card .ml-compact-value {
            color: #237258;
        }

        .ml-negative-card {
            border-top: 3px solid #b44b4b;
        }

        .ml-negative-card .ml-compact-value {
            color: #a63e3e;
        }

        .ml-neutral-card {
            border-top: 3px solid #c6973d;
        }

        .ml-context-compact {
            background: #ffffff;
            border: 1px solid #d8e0e9;
            border-radius: 13px;
            padding: 1.25rem 1.35rem;
            height: 100%;
            box-shadow: 0 2px 8px rgba(15, 35, 63, 0.04);
        }

        .ml-context-compact-title {
            color: #10233f;
            font-size: 1.08rem;
            font-weight: 800;
            margin-bottom: 0.8rem;
        }

        .ml-compact-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            border-top: 1px solid #edf1f5;
            padding: 0.72rem 0;
            color: #59697e;
            font-size: 0.9rem;
        }

        .ml-compact-row:first-of-type {
            border-top: none;
        }

        .ml-compact-row strong {
            color: #12243b;
            font-size: 0.92rem;
            text-align: right;
        }

        .ml-decision-watch {
            background: linear-gradient(
                90deg,
                #fff7e8 0%,
                #ffffff 100%
            );
            border: 1px solid #eac98e;
            border-left: 5px solid #d4962f;
            border-radius: 13px;
            padding: 1.4rem 1.5rem;
        }

        .ml-decision-watch-title {
            color: #9b6819;
            font-size: 1.65rem;
            font-weight: 850;
            margin-bottom: 0.4rem;
        }

        .ml-decision-watch-text {
            color: #38495f;
            font-size: 0.98rem;
            line-height: 1.6;
        }
        .ml-pricing-card {
            background: #f7f9fc;
            border: 1px solid #d5deea;
            border-left: 5px solid #2d5f9a;
            border-radius: 13px;
            padding: 1.4rem 1.5rem;
            margin-top: 1rem;
        }

        .ml-pricing-label {
            color: #2d5f9a;
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-bottom: 0.45rem;
        }

        .ml-pricing-title {
            color: #10233f;
            font-size: 1.45rem;
            font-weight: 800;
            margin-bottom: 0.9rem;
        }

        .ml-pricing-row {
            margin-top: 0.8rem;
        }

        .ml-pricing-row strong {
            color: #10233f;
        }

        .ml-pricing-row span {
            color: #46566d;
            line-height: 1.55;
        }
        .ml-alignment-strip {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            background: #ffffff;
            border: 1px solid #d8e0e9;
            border-radius: 11px;
            margin-top: 0.75rem;
            overflow: hidden;
        }

        .ml-alignment-strip-item {
            padding: 0.9rem 1rem;
            border-left: 1px solid #e8edf3;
        }

        .ml-alignment-strip-item:first-child {
            border-left: none;
        }

        .ml-alignment-strip-label {
            color: #657489;
            font-size: 0.72rem;
            font-weight: 750;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }

        .ml-alignment-strip-value {
            color: #12243b;
            font-size: 1rem;
            font-weight: 800;
            margin-top: 0.25rem;
        }

        .ml-decision-framework {
            background: #ffffff;
            border: 1px solid #d8e0e9;
            border-radius: 13px;
            overflow: hidden;
        }

        .ml-decision-header {
            background: #10233f;
            padding: 1.25rem 1.4rem;
        }

        .ml-decision-header-label {
            color: #aebed2;
            font-size: 0.75rem;
            font-weight: 750;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .ml-decision-header-value {
            color: #ffffff;
            font-size: 1.65rem;
            font-weight: 850;
            margin-top: 0.3rem;
        }

        .ml-decision-body {
            padding: 1.3rem 1.4rem;
        }

        .ml-decision-row {
            padding: 0.8rem 0;
            border-top: 1px solid #edf1f5;
        }

        .ml-decision-row:first-child {
            border-top: none;
            padding-top: 0;
        }

        .ml-decision-row strong {
            display: block;
            color: #10233f;
            font-size: 0.84rem;
            margin-bottom: 0.25rem;
        }

        .ml-decision-row span {
            color: #46566d;
            font-size: 0.94rem;
            line-height: 1.55;
        }

        @media (max-width: 800px) {
            .ml-alignment-strip {
                grid-template-columns: 1fr;
            }

            .ml-alignment-strip-item {
                border-left: none;
                border-top: 1px solid #e8edf3;
            }

            .ml-alignment-strip-item:first-child {
                border-top: none;
            }
        }
        .ml-history-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 1rem;
        }

        .ml-history-card {
            background: #ffffff;
            border: 1px solid #d8e0e9;
            border-radius: 13px;
            padding: 1.25rem 1.35rem;
        }

        .ml-history-source {
            color: #64748b;
            font-size: 0.74rem;
            font-weight: 800;
            letter-spacing: 0.055em;
            text-transform: uppercase;
            margin-bottom: 0.4rem;
        }

        .ml-history-environment {
            color: #10233f;
            font-size: 1.12rem;
            font-weight: 800;
            margin-bottom: 0.85rem;
        }

        .ml-history-row {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            border-top: 1px solid #edf1f5;
            padding: 0.62rem 0;
            color: #59697e;
            font-size: 0.88rem;
        }

        .ml-history-row strong {
            color: #12243b;
            text-align: right;
        }

        .ml-history-assessment {
            background: #f7f9fc;
            border: 1px solid #d5deea;
            border-left: 5px solid #647b99;
            border-radius: 13px;
            padding: 1.3rem 1.4rem;
            margin-top: 1rem;
        }

        .ml-history-assessment-label {
            color: #10233f;
            font-size: 1.05rem;
            font-weight: 800;
            margin-bottom: 0.4rem;
        }

        .ml-history-assessment-text {
            color: #46566d;
            font-size: 0.94rem;
            line-height: 1.6;
        }

        @media (max-width: 800px) {
            .ml-history-grid {
                grid-template-columns: 1fr;
            }
        }    

        .ml-update-card {
            background: #ffffff;
            border: 1px solid #d8e0e9;
            border-left: 5px solid #64748b;
            border-radius: 14px;
            padding: 1.35rem 1.45rem;
            margin-bottom: 1.25rem;
        }

        .ml-update-material {
            border-left-color: #c27a20;
            background: #fffaf2;
        }

        .ml-update-unchanged {
            border-left-color: #278063;
            background: #f8fcfa;
        }

        .ml-update-initial {
            border-left-color: #2d5f9a;
            background: #f7f9fc;
        }

        .ml-update-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1.5rem;
        }

        .ml-update-eyebrow {
            color: #64748b;
            font-size: 0.74rem;
            font-weight: 800;
            letter-spacing: 0.065em;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }

        .ml-update-title {
            color: #10233f;
            font-size: 1.4rem;
            font-weight: 850;
            margin-bottom: 0.35rem;
        }

        .ml-update-summary {
            color: #46566d;
            font-size: 0.93rem;
            line-height: 1.55;
        }

        .ml-update-stance {
            min-width: 170px;
            background: #10233f;
            border-radius: 10px;
            padding: 0.85rem 1rem;
        }

        .ml-update-stance-label {
            color: #afbdd0;
            font-size: 0.7rem;
            font-weight: 750;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .ml-update-stance-value {
            color: #ffffff;
            font-size: 1.15rem;
            font-weight: 850;
            margin-top: 0.25rem;
        }

        .ml-update-meta {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            border-top: 1px solid #e8edf3;
            margin-top: 1rem;
            padding-top: 0.8rem;
            color: #6a788c;
            font-size: 0.8rem;
        }

        .ml-update-changes {
            margin-top: 0.9rem;
        }

        .ml-update-change-row {
            border-top: 1px solid #edf1f5;
            padding: 0.7rem 0;
        }

        .ml-update-change-label {
            color: #526176;
            font-size: 0.78rem;
            font-weight: 750;
        }

        .ml-update-change-values {
            color: #10233f;
            font-size: 0.92rem;
            font-weight: 750;
            margin-top: 0.2rem;
        }

        .ml-update-change-values span {
            color: #8a97a8;
            padding: 0 0.35rem;
        }

        .ml-update-badge {
            display: inline-block;
            background: #fff0d8;
            color: #9a6115;
            border-radius: 999px;
            padding: 0.1rem 0.42rem;
            margin-left: 0.35rem;
            font-size: 0.62rem;
            text-transform: uppercase;
        }

        .ml-update-no-changes {
            color: #46566d;
            font-size: 0.9rem;
            line-height: 1.55;
        }

        @media (max-width: 800px) {
            .ml-update-top,
            .ml-update-meta {
                flex-direction: column;
            }

            .ml-update-stance {
                width: 100%;
            }
        }
        /* =========================================================
           RESEARCH WORKSPACE — PAGE HIERARCHY
           ========================================================= */

        .ml-research-page-header {
            max-width: 980px;
            margin: 18px auto 24px;
            text-align: center;
        }

        .ml-research-title {
            margin: 0;
            color: #10233f;
            font-size: 2.35rem;
            font-weight: 900;
            letter-spacing: -0.045em;
            line-height: 1.08;
        }

        .ml-research-subtitle {
            max-width: 760px;
            margin: 9px auto 0;
            color: #33465e;
            font-size: 1rem;
            font-weight: 550;
            line-height: 1.6;
        }

        .ml-research-reading-path {
            display: inline-flex;
            align-items: center;
            flex-wrap: wrap;
            justify-content: center;
            gap: 0.55rem;
            margin-top: 13px;
            padding: 7px 12px;
            border: 1px solid #d8e1ea;
            border-radius: 999px;
            background: #f7f9fc;
            color: #40536b;
            font-size: 0.76rem;
            font-weight: 750;
        }

        .ml-research-reading-path span {
            color: #8a99aa;
        }


        /* ---------- Review update ---------- */

        .ml-update-title {
            color: #10233f;
            font-size: 1.5rem;
            font-weight: 900;
        }

        .ml-update-summary {
            max-width: 740px;
            color: #273b53;
            font-size: 0.97rem;
            font-weight: 550;
            line-height: 1.6;
        }

        .ml-update-eyebrow {
            color: #40536b;
            font-size: 0.75rem;
            font-weight: 850;
        }

        .ml-update-stance-label {
            color: #d8e3ef;
            font-size: 0.72rem;
            font-weight: 800;
        }

        .ml-update-meta {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0;
            margin-top: 1rem;
            padding-top: 0;
            border-top: 1px solid #dce4ec;
        }

        .ml-update-meta-item {
            padding: 0.9rem 1rem 0.15rem;
            border-left: 1px solid #dce4ec;
        }

        .ml-update-meta-item:first-child {
            padding-left: 0;
            border-left: none;
        }

        .ml-update-meta-item span {
            display: block;
            color: #52647b;
            font-size: 0.68rem;
            font-weight: 850;
            letter-spacing: 0.055em;
            text-transform: uppercase;
        }

        .ml-update-meta-item strong {
            display: block;
            margin-top: 5px;
            color: #152a43;
            font-size: 0.86rem;
            font-weight: 800;
            line-height: 1.45;
        }

        .ml-update-no-changes {
            color: #273b53;
            font-size: 0.94rem;
            font-weight: 550;
        }


        /* ---------- Current view summary ---------- */

        .ml-view-summary {
            margin-bottom: 1.1rem;
            overflow: hidden;
            border: 1px solid #ced9e4;
            border-radius: 14px;
            background: #ffffff;
            box-shadow: 0 5px 18px rgba(15, 35, 63, 0.045);
        }

        .ml-view-summary-heading {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            padding: 1.2rem 1.35rem;
            border-bottom: 1px solid #dce4ec;
            background: #f8fafc;
        }

        .ml-view-summary-eyebrow {
            color: #52647b;
            font-size: 0.7rem;
            font-weight: 850;
            letter-spacing: 0.065em;
            text-transform: uppercase;
        }

        .ml-view-summary-asset {
            margin-top: 4px;
            color: #10233f;
            font-size: 1.4rem;
            font-weight: 900;
        }

        .ml-view-summary-horizon {
            padding: 6px 10px;
            border-radius: 999px;
            background: #eaf0f7;
            color: #365b88;
            font-size: 0.72rem;
            font-weight: 800;
        }

        .ml-view-summary-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
        }

        .ml-view-summary-item {
            min-height: 190px;
            padding: 1.2rem 1.25rem;
            border-left: 1px solid #e2e8ef;
        }

        .ml-view-summary-item:first-child {
            border-left: none;
        }

        .ml-view-summary-item > span {
            display: block;
            color: #52647b;
            font-size: 0.7rem;
            font-weight: 850;
            letter-spacing: 0.055em;
            text-transform: uppercase;
        }

        .ml-view-summary-item > strong {
            display: block;
            margin-top: 9px;
            color: #10233f;
            font-size: 1.45rem;
            font-weight: 900;
            letter-spacing: -0.025em;
        }

        .ml-view-summary-item p {
            margin: 10px 0 0;
            color: #33465e;
            font-size: 0.86rem;
            font-weight: 550;
            line-height: 1.55;
        }

        .ml-view-summary-classification {
            margin-top: 4px;
            color: #a64242;
            font-size: 0.82rem;
            font-weight: 800;
        }

        .ml-view-summary-stance {
            background: #10233f;
        }

        .ml-view-summary-stance > span {
            color: #b9c7d8;
        }

        .ml-view-summary-stance > strong {
            color: #ffffff;
        }

        .ml-view-summary-stance p {
            color: #dbe4ee;
        }


        /* ---------- Improve small card copy ---------- */

        .ml-compact-label {
            color: #40536b;
            font-size: 0.72rem;
            font-weight: 850;
        }

        .ml-compact-note {
            color: #33465e;
            font-size: 0.84rem;
            font-weight: 550;
            line-height: 1.45;
        }

        .ml-context-label,
        .ml-compact-row {
            color: #33465e;
        }

        .ml-context-value,
        .ml-compact-row strong {
            color: #10233f;
        }


        /* ---------- Responsive ---------- */

        @media (max-width: 950px) {
            .ml-view-summary-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }

            .ml-view-summary-item:nth-child(3) {
                border-left: none;
                border-top: 1px solid #e2e8ef;
            }

            .ml-view-summary-item:nth-child(4) {
                border-top: 1px solid #e2e8ef;
            }
        }

        @media (max-width: 700px) {
            .ml-update-meta {
                grid-template-columns: 1fr;
            }

            .ml-update-meta-item {
                padding: 0.75rem 0;
                border-left: none;
                border-top: 1px solid #dce4ec;
            }

            .ml-update-meta-item:first-child {
                border-top: none;
            }

            .ml-view-summary-grid {
                grid-template-columns: 1fr;
            }

            .ml-view-summary-item {
                min-height: auto;
                border-left: none;
                border-top: 1px solid #e2e8ef;
            }

            .ml-view-summary-item:first-child {
                border-top: none;
            }
        }
        /* =========================================================
           RESEARCH WORKSPACE — LOWER PAGE STRUCTURE
           ========================================================= */

        .ml-workspace-section-header {
            display: flex;
            align-items: flex-start;
            gap: 1rem;
            margin: 2.7rem 0 1.2rem;
            padding-top: 1.8rem;
            border-top: 1px solid #d8e1ea;
        }

        .ml-workspace-section-number {
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

        .ml-workspace-section-title {
            color: #10233f;
            font-size: 1.55rem;
            font-weight: 900;
            letter-spacing: -0.03em;
        }

        .ml-workspace-section-description {
            max-width: 760px;
            margin-top: 4px;
            color: #33465e;
            font-size: 0.92rem;
            font-weight: 550;
            line-height: 1.55;
        }


        /* ---------- Combined confirmation panel ---------- */

        .ml-confirmation-panel {
            margin-top: 1rem;
            overflow: hidden;
            border: 1px solid #d4dde7;
            border-radius: 14px;
            background: #ffffff;
            box-shadow: 0 5px 16px rgba(15, 35, 63, 0.04);
        }

        .ml-confirmation-header {
            display: flex;
            justify-content: space-between;
            gap: 1.5rem;
            padding: 1.35rem 1.45rem;
            border-bottom: 1px solid #dfe6ed;
            background: #f8fafc;
        }

        .ml-confirmation-eyebrow {
            color: #52647b;
            font-size: 0.7rem;
            font-weight: 850;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .ml-confirmation-title {
            margin-top: 5px;
            color: #10233f;
            font-size: 1.55rem;
            font-weight: 900;
        }

        .ml-confirmation-summary {
            max-width: 690px;
            margin-top: 5px;
            color: #33465e;
            font-size: 0.92rem;
            font-weight: 550;
            line-height: 1.55;
        }

        .ml-confirmation-status {
            min-width: 185px;
            padding: 0.8rem 1rem;
            border-radius: 9px;
            background: #10233f;
        }

        .ml-confirmation-status span {
            display: block;
            color: #c0cddd;
            font-size: 0.67rem;
            font-weight: 800;
            letter-spacing: 0.055em;
            text-transform: uppercase;
        }

        .ml-confirmation-status strong {
            display: block;
            margin-top: 5px;
            color: #ffffff;
            font-size: 1rem;
            font-weight: 850;
        }

        .ml-confirmation-strip {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            border-bottom: 1px solid #dfe6ed;
        }

        .ml-confirmation-strip-item {
            padding: 1rem 1.3rem;
            border-left: 1px solid #dfe6ed;
        }

        .ml-confirmation-strip-item:first-child {
            border-left: none;
        }

        .ml-confirmation-strip-item span {
            display: block;
            color: #52647b;
            font-size: 0.68rem;
            font-weight: 850;
            letter-spacing: 0.055em;
            text-transform: uppercase;
        }

        .ml-confirmation-strip-item strong {
            display: block;
            margin-top: 5px;
            color: #10233f;
            font-size: 1rem;
            font-weight: 850;
        }

        .ml-confirmation-body {
            padding: 0.5rem 1.45rem 1.35rem;
        }

        .ml-confirmation-row {
            padding: 1rem 0;
            border-bottom: 1px solid #e6ebf1;
        }

        .ml-confirmation-row strong {
            color: #10233f;
            font-size: 0.9rem;
            font-weight: 850;
        }

        .ml-confirmation-row p {
            margin: 5px 0 0;
            color: #2d4159;
            font-size: 0.94rem;
            font-weight: 550;
            line-height: 1.6;
        }

        .ml-confirmation-conclusion {
            margin-top: 1rem;
            padding: 1rem 1.1rem;
            border-left: 4px solid #2d5f9a;
            background: #f3f7fb;
        }

        .ml-confirmation-conclusion span {
            display: block;
            color: #52647b;
            font-size: 0.68rem;
            font-weight: 850;
            text-transform: uppercase;
        }

        .ml-confirmation-conclusion strong {
            display: block;
            margin-top: 5px;
            color: #10233f;
            font-size: 0.95rem;
            line-height: 1.55;
        }


        /* ---------- Thesis ---------- */

        .ml-thesis-panel {
            overflow: hidden;
            border: 1px solid #d3dde7;
            border-left: 5px solid #2d5f9a;
            border-radius: 13px;
            background: #ffffff;
        }

        .ml-thesis-label {
            padding: 1rem 1.35rem 0;
            color: #2d5f9a;
            font-size: 0.7rem;
            font-weight: 850;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .ml-thesis-text {
            padding: 0.65rem 1.35rem 1.25rem;
            color: #152a43;
            font-size: 1.05rem;
            font-weight: 600;
            line-height: 1.7;
        }

        .ml-thesis-footer {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            border-top: 1px solid #dfe6ed;
            background: #f8fafc;
        }

        .ml-thesis-footer > div {
            padding: 0.9rem 1.3rem;
            border-left: 1px solid #dfe6ed;
        }

        .ml-thesis-footer > div:first-child {
            border-left: none;
        }

        .ml-thesis-footer span {
            display: block;
            color: #52647b;
            font-size: 0.66rem;
            font-weight: 850;
            text-transform: uppercase;
        }

        .ml-thesis-footer strong {
            display: block;
            margin-top: 4px;
            color: #10233f;
            font-size: 0.9rem;
            font-weight: 850;
        }


        /* ---------- Subsection headings ---------- */

        .ml-subsection-header {
            margin: 1.8rem 0 0.9rem;
        }

        .ml-subsection-title {
            color: #10233f;
            font-size: 1.2rem;
            font-weight: 900;
            letter-spacing: -0.02em;
        }

        .ml-subsection-description {
            margin-top: 4px;
            color: #33465e;
            font-size: 0.88rem;
            font-weight: 550;
        }


        /* ---------- Evidence cards ---------- */

        .ml-evidence-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.85rem;
        }

        .ml-evidence-card {
            padding: 1.1rem 1.15rem;
            border: 1px solid #d8e1ea;
            border-top: 4px solid #2d7d66;
            border-radius: 11px;
            background: #ffffff;
        }

        .ml-evidence-category {
            color: #236b57;
            font-size: 0.7rem;
            font-weight: 850;
            letter-spacing: 0.055em;
            text-transform: uppercase;
        }

        .ml-evidence-message {
            margin-top: 8px;
            color: #182e47;
            font-size: 0.91rem;
            font-weight: 600;
            line-height: 1.55;
        }

        .ml-evidence-source {
            margin-top: 12px;
            padding-top: 10px;
            border-top: 1px solid #e6ebf1;
            color: #64758a;
            font-size: 0.72rem;
            font-weight: 700;
        }


        /* ---------- Limitations ---------- */

        .ml-limitations-panel {
            margin-top: 1.6rem;
            overflow: hidden;
            border: 1px solid #ead4ae;
            border-radius: 13px;
            background: #fffbf4;
        }

        .ml-limitations-heading {
            padding: 1.15rem 1.3rem;
            border-bottom: 1px solid #eadfc9;
        }

        .ml-limitations-title {
            color: #80571a;
            font-size: 1.1rem;
            font-weight: 900;
        }

        .ml-limitations-description {
            margin-top: 4px;
            color: #604d31;
            font-size: 0.85rem;
            font-weight: 550;
        }

        .ml-limitations-list {
            padding: 0 1.3rem;
        }

        .ml-limitation-row {
            display: flex;
            gap: 0.8rem;
            padding: 0.9rem 0;
            border-top: 1px solid #eadfc9;
            color: #463a29;
            font-size: 0.9rem;
            font-weight: 550;
            line-height: 1.55;
        }

        .ml-limitation-row:first-child {
            border-top: none;
        }

        .ml-limitation-marker {
            display: flex;
            width: 21px;
            height: 21px;
            flex: 0 0 21px;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            background: #f3dcae;
            color: #80571a;
            font-size: 0.72rem;
            font-weight: 900;
        }


        /* ---------- Decision framework width ---------- */

        .ml-decision-framework-centered {
            width: 100%;
            max-width: 900px;
            margin: 0 auto;
        }


        /* ---------- Responsive ---------- */

        @media (max-width: 850px) {
            .ml-confirmation-header {
                flex-direction: column;
            }

            .ml-confirmation-status {
                width: 100%;
            }

            .ml-confirmation-strip,
            .ml-thesis-footer,
            .ml-evidence-grid {
                grid-template-columns: 1fr;
            }

            .ml-confirmation-strip-item,
            .ml-thesis-footer > div {
                border-left: none;
                border-top: 1px solid #dfe6ed;
            }

            .ml-confirmation-strip-item:first-child,
            .ml-thesis-footer > div:first-child {
                border-top: none;
            }
        }
        .ml-view-summary-heading-left {
            display: flex;
            align-items: center;
            gap: 0.85rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def _metric_card(
    label: str,
    value: str,
    tone: str = "",
    note: str | None = None,
) -> None:
    note_html = (
        f'<div class="ml-compact-note">{note}</div>'
        if note
        else ""
    )

    _html(
        f"""
        <div class="ml-compact-card {tone}">
            <div class="ml-compact-label">{label}</div>
            <div class="ml-compact-value">{value}</div>
            {note_html}
        </div>
        """
    )


def _context_card(
    title: str,
    rows: list[tuple[str, str]],
) -> None:
    rows_html = "".join(
        f"""
        <div class="ml-compact-row">
            <span>{label}</span>
            <strong>{value}</strong>
        </div>
        """
        for label, value in rows
    )

    _html(
        f"""
        <div class="ml-context-compact">
            <div class="ml-context-compact-title">{title}</div>
            {rows_html}
        </div>
        """
    )

def _optional_return(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.1%}"


def _optional_rate(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.0%}"


def _render_historical_context(
    context: HistoricalContext,
) -> None:
    cards_html = ""

    for item in context.items:
        cards_html += f"""
        <div class="ml-history-card">
            <div class="ml-history-source">
                {item.source}
            </div>

            <div class="ml-history-environment">
                {item.environment}
            </div>

            <div class="ml-history-row">
                <span>Observations</span>
                <strong>{item.observations}</strong>
            </div>

            <div class="ml-history-row">
                <span>Evidence quality</span>
                <strong>{item.confidence_label}</strong>
            </div>

            <div class="ml-history-row">
                <span>Average {context.horizon_months}M return</span>
                <strong>{_optional_return(item.average_return)}</strong>
            </div>

            <div class="ml-history-row">
                <span>Median {context.horizon_months}M return</span>
                <strong>{_optional_return(item.median_return)}</strong>
            </div>

            <div class="ml-history-row">
                <span>Frequency of decline</span>
                <strong>{_optional_rate(item.down_rate)}</strong>
            </div>
        </div>
        """

    _html(
        f"""
        <div class="ml-history-grid">
            {cards_html}
        </div>

        <div class="ml-history-assessment">
            <div class="ml-history-assessment-label">
                {context.assessment_label}
            </div>

            <div class="ml-history-assessment-text">
                {context.assessment}
            </div>
        </div>
        """
    )

def _render_snapshot_update(
    comparison: SnapshotComparison,
    existing_today: DecisionSnapshot | None,
    last_material_change_date,
) -> None:
    if comparison.previous is None:
        status_label = (
            "First Review Saved"
            if existing_today is not None
            else "First Review Not Yet Saved"
        )

        initial_summary = (
            (
                f"This is the first recorded assessment for "
                f"{comparison.current.display_name}. Future reviews "
                "will be compared against this state."
            )
            if existing_today is not None
            else (
                f"Save the current assessment for "
                f"{comparison.current.display_name} to establish the "
                "starting point for future comparisons."
            )
        )

        status_class = "ml-update-initial"

        last_reviewed = (
            "No earlier comparison is available."
        )
    elif comparison.has_material_change:
        status_label = "Material Change Detected"
        status_class = "ml-update-material"
        last_reviewed = (
            f"Compared with the snapshot saved on "
            f"{comparison.previous.snapshot_date:%B %d, %Y}."
        )
    elif comparison.changes:
        status_label = "No Material Change"
        status_class = "ml-update-unchanged"
        last_reviewed = (
            f"Last compared with "
            f"{comparison.previous.snapshot_date:%B %d, %Y}."
        )
    else:
        status_label = "Unchanged"
        status_class = "ml-update-unchanged"
        last_reviewed = (
            f"No material change since "
            f"{comparison.previous.snapshot_date:%B %d, %Y}."
        )

    changes_html = ""

    if comparison.changes:
        for change in comparison.changes:
            material_label = (
                '<span class="ml-update-badge">Material</span>'
                if change.material
                else ""
            )

            changes_html += f"""
            <div class="ml-update-change-row">
                <div>
                    <div class="ml-update-change-label">
                        {change.label}
                        {material_label}
                    </div>
                    <div class="ml-update-change-values">
                        {change.previous_value}
                        <span>→</span>
                        {change.current_value}
                    </div>
                </div>
            </div>
            """
    elif comparison.previous is not None:
        changes_html = """
        <div class="ml-update-no-changes">
            Macro direction, price trend, alignment and decision stance
            remain unchanged.
        </div>
        """
    else:
        changes_html = """
        <div class="ml-update-no-changes">
            Future changes in macro direction, price trend, alignment
            and system stance will be measured against this review.
        </div>
        """

    saved_today_text = (
        f"Review saved today at "
        f"{existing_today.created_at:%H:%M}."
        if existing_today is not None
        else "Today’s review has not yet been saved."
    )

    _html(
        f"""
        <div class="ml-update-card {status_class}">
            <div class="ml-update-top">
                <div>
                    <div class="ml-update-eyebrow">
                        Today’s Review
                    </div>

                    <div class="ml-update-title">
                        {status_label}
                    </div>

                    <div class="ml-update-summary">
                        {initial_summary if comparison.previous is None else comparison.summary}
                    </div>
                </div>

                <div class="ml-update-stance">
                    <div class="ml-update-stance-label">
                        System Stance
                    </div>

                    <div class="ml-update-stance-value">
                        {comparison.current.decision_stance}
                    </div>
                </div>
            </div>

            <div class="ml-update-meta">
                <div class="ml-update-meta-item">
                    <span>Last material change</span>
                    <strong>
                        {last_material_change_date:%B %d, %Y}
                    </strong>
                </div>

                <div class="ml-update-meta-item">
                    <span>Comparison status</span>
                    <strong>{last_reviewed}</strong>
                </div>

                <div class="ml-update-meta-item">
                    <span>Review status</span>
                    <strong>{saved_today_text}</strong>
                </div>
            </div>

            <div class="ml-update-changes">
                {changes_html}
            </div>
        </div>
        """
    )

def _render_research_evidence(
    evidence: tuple,
) -> None:
    if not evidence:
        _html(
            """
            <div class="ml-evidence-empty-state">
                No supporting evidence is currently available.
            </div>
            """
        )
        return

    cards_html = ""

    for item in evidence:
        cards_html += f"""
        <article class="ml-evidence-card">
            <div class="ml-evidence-category">
                {item.category}
            </div>

            <div class="ml-evidence-message">
                {item.message}
            </div>

            <div class="ml-evidence-source">
                {item.source}
            </div>
        </article>
        """

    _html(
        f"""
        <div class="ml-subsection-header">
            <div class="ml-subsection-title">
                Supporting Evidence
            </div>

            <div class="ml-subsection-description">
                The strongest model-based evidence behind the
                current directional view.
            </div>
        </div>

        <div class="ml-evidence-grid">
            {cards_html}
        </div>
        """
    )

def _render_research_limitations(
    limitations: tuple[str, ...],
) -> None:
    if not limitations:
        return

    items_html = "".join(
        f"""
        <div class="ml-limitation-row">
            <div class="ml-limitation-marker">!</div>
            <div>{limitation}</div>
        </div>
        """
        for limitation in limitations
    )

    _html(
        f"""
        <section class="ml-limitations-panel">
            <div class="ml-limitations-heading">
                <div class="ml-limitations-title">
                    Research Limitations
                </div>

                <div class="ml-limitations-description">
                    Factors that reduce the strength or completeness
                    of the current assessment.
                </div>
            </div>

            <div class="ml-limitations-list">
                {items_html}
            </div>
        </section>
        """
    )

def render_research_workspace_page() -> None:
    _inject_research_workspace_css()

    available_assets = get_available_assets()

    asset_classes = sorted(
        {
            asset.asset_class
            for asset in available_assets
        }
    )

    class_col, asset_col, horizon_col = st.columns(
        [1, 1.5, 1]
    )

    with class_col:
        selected_asset_class = st.selectbox(
            "Asset Class",
            options=asset_classes,
            index=0,
            key="decision_asset_class",
        )

    filtered_assets = tuple(
        asset
        for asset in available_assets
        if asset.asset_class == selected_asset_class
    )

    asset_labels = {
        asset.display_name: asset.key
        for asset in filtered_assets
    }

    with asset_col:
        selected_asset_label = st.selectbox(
            "Asset",
            options=list(asset_labels),
            index=0,
            key="decision_asset",
        )

    with horizon_col:
        selected_horizon = st.selectbox(
            "Horizon",
            options=[1, 3, 6],
            index=1,
            format_func=lambda value: (
                f"{value} Month"
                if value == 1
                else f"{value} Months"
            ),
            key="decision_horizon",
        )

    selected_asset_key = asset_labels[selected_asset_label]

    with st.spinner(
        f"Building {selected_asset_label} decision workspace..."
    ):
        workspace = load_decision_workspace(
            asset_key=selected_asset_key,
            horizon_months=selected_horizon,
        )

    idea = workspace.idea
    market = workspace.market
    alignment = workspace.alignment
    pricing = workspace.pricing
    historical_context = workspace.historical_context
    decision = workspace.decision
    
    current_snapshot = build_snapshot(workspace)

    previous_snapshot = load_latest_snapshot(
        workspace.asset_key,
        before_date=current_snapshot.snapshot_date,
    )

    existing_today = load_latest_snapshot(
        workspace.asset_key,
    )

    if (
        existing_today is not None
        and existing_today.snapshot_date
        != current_snapshot.snapshot_date
    ):
        existing_today = None

    snapshot_comparison = compare_snapshots(
        current=current_snapshot,
        previous=previous_snapshot,
    )
    
    last_material_change_date = find_last_material_change_date(
        workspace.asset_key,
    )

    if (
        previous_snapshot is not None
        and snapshot_comparison.has_material_change
    ):
        last_material_change_date = current_snapshot.snapshot_date

    if last_material_change_date is None:
        last_material_change_date = current_snapshot.snapshot_date

    direction_class = _direction_class(
        idea.model_direction
    )

    _html(
        f"""
        <div class="ml-research-page-header">
            <div class="ml-research-title">
                {workspace.display_name} Research Idea
            </div>

            <div class="ml-research-subtitle">
                A structured assessment of macro conditions, market
                behaviour and historical evidence.
            </div>

            <div class="ml-research-reading-path">
                Macro View
                <span>→</span>
                Market Confirmation
                <span>→</span>
                Historical Evidence
                <span>→</span>
                System Stance
            </div>
        </div>
        """
    )

    _render_snapshot_update(
        comparison=snapshot_comparison,
        existing_today=existing_today,
        last_material_change_date=last_material_change_date,
    )

    score_label = _score_interpretation(
        idea.directional_score
    )

    _html(
        f"""
        <section class="ml-view-summary">
            <div class="ml-view-summary-heading">
                <div class="ml-view-summary-heading-left">
                    <div class="ml-workspace-section-number">01</div>

                    <div>
                        <div class="ml-view-summary-eyebrow">
                            Current Model View
                        </div>

                        <div class="ml-view-summary-asset">
                            {idea.asset}
                        </div>
                    </div>
                </div>

                <div class="ml-view-summary-horizon">
                    {idea.horizon_months}-Month Horizon
                </div>
            </div>

            <div class="ml-view-summary-grid">
                <div class="ml-view-summary-item">
                    <span>Macro Direction</span>

                    <strong class="{direction_class}">
                        {idea.model_direction}
                    </strong>

                    <p>
                        The relative economic backdrop currently
                        favours one side of the currency pair.
                    </p>
                </div>

                <div class="ml-view-summary-item">
                    <span>Macro Score</span>

                    <strong>
                        {_format_score(idea.directional_score)}
                    </strong>

                    <div class="ml-view-summary-classification">
                        {score_label}
                    </div>

                    <p>
                        Scores closer to −1 are increasingly bearish;
                        scores closer to +1 are increasingly bullish.
                    </p>
                </div>

                <div class="ml-view-summary-item">
                    <span>Market Alignment</span>

                    <strong>
                        {alignment.label}
                    </strong>

                    <p>
                        {alignment.summary}
                    </p>
                </div>

                <div class="ml-view-summary-item ml-view-summary-stance">
                    <span>System Stance</span>

                    <strong>
                        {decision.stance}
                    </strong>

                    <p>
                        {decision.reason}
                    </p>
                </div>
            </div>
        </section>
        """
    )

    metric_columns = st.columns(4)

    top_metrics = [
        (
            "Current Price",
            _format_price(market.current_price),
            "",
            f"Market data through {market.as_of_date:%b %d}",
        ),
        (
            "Model Confidence",
            _format_percentage(idea.model_confidence),
            "",
            "How reliably the model classified the current environment",
        ),
        (
            "Model Conviction",
            _format_percentage(idea.model_conviction),
            "ml-neutral-card",
            "How strongly the underlying macro pillars agree",
        ),
        (
            "Historical Support",
            idea.historical_support,
            "ml-neutral-card",
            "Strength and relevance of the available historical sample",
        ),
    ]

    for column, metric in zip(metric_columns, top_metrics):
        with column:
            _metric_card(*metric)

    _html(
        """
        <div class="ml-workspace-section-header">
            <div class="ml-workspace-section-number">02</div>

            <div>
                <div class="ml-workspace-section-title">
                    Market Confirmation
                </div>

                <div class="ml-workspace-section-description">
                    Compare the macro thesis with current price behaviour,
                    momentum and market conditions.
                </div>
            </div>
        </div>
        """
    )

    _html(
        """
        <div class="ml-subsection-header">
            <div class="ml-subsection-title">
                Recent Price Action
            </div>

            <div class="ml-subsection-description">
                Short-term market performance across the selected horizon.
            </div>
        </div>
        """
    )

    return_columns = st.columns(4)

    recent_returns = [
        ("1 Day", market.daily_return),
        ("1 Week", market.weekly_return),
        ("1 Month", market.monthly_return),
        ("3 Months", market.quarterly_return),
    ]

    for column, (label, value) in zip(
        return_columns,
        recent_returns,
    ):
        tone = (
            "ml-positive-card"
            if value is not None and value > 0
            else "ml-negative-card"
            if value is not None and value < 0
            else "ml-neutral-card"
        )

        with column:
            _metric_card(
                label=label,
                value=_format_return(value),
                tone=tone,
            )

    market_col, macro_col = st.columns(2)

    with market_col:
        _context_card(
            "Price and Market Context",
            [
                ("Price trend", market.trend_label),
                ("Momentum", market.momentum_label),
                (
                    "Position in 52-week range",
                    f"{market.range_percentile_52w:.0%}",
                ),
                (
                    "Below 52-week high",
                    f"{abs(market.distance_from_high_52w):.2%}",
                ),
                (
                    "20-day realised volatility",
                    (
                        f"{market.realized_volatility_20d:.1%} "
                        f"({market.volatility_label})"
                    ),
                ),
            ],
        )

    with macro_col:
        _context_card(
            "Macro Signal Context",
            [
                ("Directional view", idea.model_direction),
                (
                    "Macro score",
                    (
                        f"{_format_score(idea.directional_score)} · "
                        f"{_score_interpretation(idea.directional_score)}"
                    ),
                ),
                (
                    "Model confidence",
                    _format_percentage(idea.model_confidence),
                ),
                (
                    "Model conviction",
                    _format_percentage(idea.model_conviction),
                ),
                (
                    "Historical support",
                    idea.historical_support,
                ),
            ],
        )

    _html(
        f"""
        <section class="ml-confirmation-panel">
            <div class="ml-confirmation-header">
                <div>
                    <div class="ml-confirmation-eyebrow">
                        Macro–Market Relationship
                    </div>

                    <div class="ml-confirmation-title">
                        {alignment.label}
                    </div>

                    <div class="ml-confirmation-summary">
                        {alignment.summary}
                    </div>
                </div>

                <div class="ml-confirmation-status">
                    <span>Pricing Status</span>
                    <strong>{pricing.label}</strong>
                </div>
            </div>

            <div class="ml-confirmation-strip">
                <div class="ml-confirmation-strip-item">
                    <span>Macro Direction</span>
                    <strong class="{direction_class}">
                        {alignment.macro_direction}
                    </strong>
                </div>

                <div class="ml-confirmation-strip-item">
                    <span>Price Trend</span>
                    <strong>{alignment.price_trend}</strong>
                </div>

                <div class="ml-confirmation-strip-item">
                    <span>Momentum</span>
                    <strong>{alignment.momentum}</strong>
                </div>
            </div>

            <div class="ml-confirmation-body">
                <div class="ml-confirmation-row">
                    <strong>What price is doing</strong>
                    <p>{pricing.price_behaviour}</p>
                </div>

                <div class="ml-confirmation-row">
                    <strong>What it means</strong>
                    <p>{pricing.interpretation}</p>
                </div>

                <div class="ml-confirmation-conclusion">
                    <span>Research conclusion</span>
                    <strong>{pricing.conclusion}</strong>
                </div>
            </div>
        </section>
        """
    )

    _html(
        """
        <div class="ml-workspace-section-header">
            <div class="ml-workspace-section-number">03</div>

            <div>
                <div class="ml-workspace-section-title">
                    Research Evidence
                </div>

                <div class="ml-workspace-section-description">
                    Review the core thesis, supporting macro evidence,
                    historical outcomes and limitations of the analysis.
                </div>
            </div>
        </div>
        """
    )

    _html(
        f"""
        <section class="ml-thesis-panel">
            <div class="ml-thesis-label">
                Investment Thesis
            </div>

            <div class="ml-thesis-text">
                {idea.thesis}
            </div>

            <div class="ml-thesis-footer">
                <div>
                    <span>Direction</span>
                    <strong class="{direction_class}">
                        {idea.model_direction}
                    </strong>
                </div>

                <div>
                    <span>Time Horizon</span>
                    <strong>{idea.horizon_months} Months</strong>
                </div>

                <div>
                    <span>System Stance</span>
                    <strong>{decision.stance}</strong>
                </div>
            </div>
        </section>
        """
    )

    _render_research_evidence(
        idea.supporting_evidence,
    )

    non_historical_contradictions = tuple(
        item
        for item in idea.contradicting_evidence
        if item.category != "Historical evidence"
    )

    display_limitations = tuple(
        limitation
        for limitation in idea.limitations
        if "environment history" not in limitation.lower()
        and "exact historical match" not in limitation.lower()
        and "market price confirmation" not in limitation.lower()
    )

    if non_historical_contradictions:

        with st.container(border=True):
            _render_evidence_section(
                "Other Contradicting Evidence",
                non_historical_contradictions,
                "",
            )

    _html(
        f"""
        <div class="ml-subsection-header">
            <div class="ml-subsection-title">
                Historical Evidence
            </div>

            <div class="ml-subsection-description">
                {historical_context.horizon_months}-month forward
                performance after comparable macro environments.
            </div>
        </div>
        """
    )

    _render_historical_context(historical_context)

    _render_research_limitations(
        display_limitations,
    )

    _html(
        """
        <div class="ml-workspace-section-header">
            <div class="ml-workspace-section-number">04</div>

            <div>
                <div class="ml-workspace-section-title">
                    Decision Framework
                </div>

                <div class="ml-workspace-section-description">
                    Translate the combined macro, market and historical
                    evidence into a clear review status.
                </div>
            </div>
        </div>
        """
    )

    _html(
        f"""
        <div class="ml-decision-framework ml-decision-framework-centered">
            <div class="ml-decision-header">
                <div class="ml-decision-header-label">
                    System Stance
                </div>

                <div class="ml-decision-header-value">
                    {decision.stance}
                </div>
            </div>

            <div class="ml-decision-body">
                <div class="ml-decision-row">
                    <strong>Why the model is here</strong>
                    <span>{decision.reason}</span>
                </div>

                <div class="ml-decision-row">
                    <strong>Confirmation required</strong>
                    <span>{decision.trigger}</span>
                </div>

                <div class="ml-decision-row">
                    <strong>What would invalidate the thesis</strong>
                    <span>{decision.invalidation}</span>
                </div>
            </div>
        </div>
        """
    )
    
    st.divider()

    save_label = (
        "Update Today’s Review"
        if existing_today is not None
        else "Save Today’s Review"
    )

    save_col, note_col = st.columns([1, 2])

    with save_col:
        if st.button(
            save_label,
            type="primary",
            use_container_width=True,
        ):
            save_snapshot(current_snapshot)

            st.success(
                f"Review saved for "
                f"{current_snapshot.snapshot_date:%B %d, %Y}."
            )

            st.rerun()

    with note_col:
        st.caption(
            "One review is stored per asset each day. "
            "Saving again replaces today’s earlier review."
        )
    
    st.caption(
        f"Macro snapshot: {idea.as_of_date:%B %d, %Y} • "
        f"Market data: {market.as_of_date:%B %d, %Y}"
    )