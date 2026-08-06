from __future__ import annotations

from datetime import date
from textwrap import dedent

import streamlit as st
from components.page_intro import render_page_intro

from macro_engine.decision.active_ideas import (
    ActiveIdea,
    build_active_ideas,
)
from macro_engine.decision.assets import get_available_assets

from macro_engine.utils.timing import log_runtime

CACHE_TTL_SECONDS = 1800


@st.cache_data(
    ttl=CACHE_TTL_SECONDS,
    show_spinner=False,
)
def load_active_ideas(
    asset_class: str | None,
    horizon_months: int,
) -> tuple[ActiveIdea, ...]:
    with log_runtime(
        (
            "Active Ideas "
            f"class={asset_class or 'All'} "
            f"horizon={horizon_months}M"
        )
    ):
        return build_active_ideas(
            asset_class=asset_class,
            horizon_months=horizon_months,
        )


def _html(content: str) -> None:
    st.html(
        dedent(content).strip()
    )


def _format_score(value: float) -> str:
    return f"{value:+.2f}"


def _format_percentage(value: float) -> str:
    return f"{value:.0%}"


def _format_last_change(
    idea: ActiveIdea,
) -> str:
    change_date = idea.last_material_change_date

    if change_date is None:
        return "No saved material change"

    days = idea.days_since_material_change

    if days == 0:
        return f"Today · {change_date:%b %d, %Y}"

    if days == 1:
        return f"Yesterday · {change_date:%b %d, %Y}"

    return f"{days} days ago · {change_date:%b %d, %Y}"


def _direction_class(direction: str) -> str:
    return {
        "Bullish": "ml-active-bullish",
        "Bearish": "ml-active-bearish",
        "Neutral": "ml-active-neutral",
    }.get(
        direction,
        "ml-active-neutral",
    )


def _status_class(idea: ActiveIdea) -> str:
    if idea.has_material_change:
        return "ml-active-material"

    if idea.existing_today is None:
        return "ml-active-unsaved"

    return "ml-active-stable"


def _stance_class(stance: str) -> str:
    return {
        "READY FOR REVIEW": "ml-stance-ready",
        "WATCH": "ml-stance-watch",
        "REVIEW": "ml-stance-review",
    }.get(
        stance,
        "ml-stance-review",
    )


def _build_change_rows(
    idea: ActiveIdea,
) -> str:
    if not idea.changes:
        return """
            <div class="ml-active-no-change">
                Macro direction, market alignment and decision stance
                remain unchanged.
            </div>
            """

    rows = ""

    for change in idea.changes[:4]:
        badge = (
            '<span class="ml-active-change-badge">Material</span>'
            if change.material
            else ""
        )

        rows += f"""
        <div class="ml-active-change-row">
            <div class="ml-active-change-label">
                {change.label}
                {badge}
            </div>

            <div class="ml-active-change-values">
                {change.previous_value}
                <span>→</span>
                {change.current_value}
            </div>
        </div>
        """

    remaining = len(idea.changes) - 4

    if remaining > 0:
        rows += f"""
        <div class="ml-active-more">
            +{remaining} additional change{
                "" if remaining == 1 else "s"
            }
        </div>
        """

    return rows


def _workspace_link(
    idea: ActiveIdea,
    horizon_months: int,
) -> str:
    return (
        "?page=ResearchWorkspace"
        f"&asset={idea.asset_key}"
        f"&horizon={horizon_months}"
    )


def _render_idea_card(
    idea: ActiveIdea,
    horizon_months: int,
) -> None:
    card_class = _status_class(idea)
    direction_class = _direction_class(
        idea.macro_direction
    )
    stance_class = _stance_class(
        idea.stance
    )

    changes_html = _build_change_rows(idea)
    workspace_link = _workspace_link(
        idea,
        horizon_months,
    )

    attention_html = (
        """
        <div class="ml-active-attention">
            Requires Attention
        </div>
        """
        if idea.needs_attention
        else ""
    )

    _html(
        f"""
        <div class="ml-active-content-shell ml-active-card {card_class}">
            <div class="ml-active-card-top">
                <div>
                    <div class="ml-active-class">
                        {idea.asset_class}
                    </div>

                    <div class="ml-active-name">
                        {idea.display_name}
                    </div>
                </div>

                <div class="ml-active-right">
                    {attention_html}

                    <div class="ml-active-stance {stance_class}">
                        {idea.stance}
                    </div>
                </div>
            </div>

            <div class="ml-active-summary">
                <div class="ml-active-status-title">
                    {idea.status_label}
                </div>

                <div class="ml-active-status-text">
                    {idea.summary}
                </div>
            </div>

            <div class="ml-active-metrics">
                <div class="ml-active-metric">
                    <span>Macro View</span>
                    <strong class="{direction_class}">
                        {idea.macro_direction}
                    </strong>
                </div>

                <div class="ml-active-metric">
                    <span>Macro Score</span>
                    <strong>
                        {_format_score(idea.directional_score)}
                    </strong>
                </div>

                <div class="ml-active-metric">
                    <span>Alignment</span>
                    <strong>{idea.alignment}</strong>
                </div>

                <div class="ml-active-metric">
                    <span>Confidence</span>
                    <strong>
                        {_format_percentage(idea.model_confidence)}
                    </strong>
                </div>
            </div>

            <div class="ml-active-changes">
                {changes_html}
            </div>

            <div class="ml-active-footer">
                <div>
                    <span>Last material change</span>
                    <strong>{_format_last_change(idea)}</strong>
                </div>

                <a
                    class="ml-active-open"
                    href="{workspace_link}"
                    target="_self"
                >
                    Open Decision Workspace
                </a>
            </div>
        </div>
        """
    )


def _inject_active_ideas_css() -> None:
    st.markdown(
        """
        <style>
        .ml-active-page-title {
            color: #0f172a;
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -0.035em;
            margin-bottom: 0.35rem;
        }

        .ml-active-page-subtitle {
            color: #5f6f83;
            font-size: 0.98rem;
            line-height: 1.55;
            margin-bottom: 1.4rem;
        }

        .ml-active-summary-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 1rem;
            margin: 1rem 0 1.5rem;
        }

        .ml-active-summary-card {
            background: #ffffff;
            border: 1px solid #d8e0e9;
            border-radius: 12px;
            padding: 1rem 1.1rem;
        }

        .ml-active-summary-label {
            color: #66758a;
            font-size: 0.74rem;
            font-weight: 800;
            letter-spacing: 0.055em;
            text-transform: uppercase;
        }

        .ml-active-summary-value {
            color: #10233f;
            font-size: 1.65rem;
            font-weight: 850;
            margin-top: 0.3rem;
        }

        .ml-active-section-title {
            color: #10233f;
            font-size: 1.28rem;
            font-weight: 800;
            margin: 1.7rem 0 0.25rem;
        }

        .ml-active-section-subtitle {
            color: #66758a;
            font-size: 0.9rem;
            margin-bottom: 0.9rem;
        }

        .ml-active-card {
            background: #ffffff;
            border: 1px solid #d8e0e9;
            border-left: 5px solid #94a3b8;
            border-radius: 14px;
            padding: 1.25rem 1.35rem;
            margin-bottom: 1rem;
            box-shadow: 0 3px 10px rgba(15, 35, 63, 0.04);
        }

        .ml-active-material {
            border-left-color: #c66f2f;
            background: #fffaf4;
        }

        .ml-active-unsaved {
            border-left-color: #2d5f9a;
            background: #f8faff;
        }

        .ml-active-stable {
            border-left-color: #278063;
            background: #fbfdfc;
        }

        .ml-active-card-top {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1rem;
        }

        .ml-active-class {
            color: #748195;
            font-size: 0.7rem;
            font-weight: 800;
            letter-spacing: 0.07em;
            text-transform: uppercase;
        }

        .ml-active-name {
            color: #10233f;
            font-size: 1.45rem;
            font-weight: 850;
            margin-top: 0.15rem;
        }

        .ml-active-right {
            text-align: right;
        }

        .ml-active-attention {
            color: #6a788c;
            font-size: 0.72rem;
            font-weight: 750;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }

        .ml-active-stance {
            display: inline-block;
            border-radius: 999px;
            padding: 0.35rem 0.7rem;
            font-size: 0.72rem;
            font-weight: 850;
            letter-spacing: 0.035em;
        }

        .ml-stance-ready {
            background: #e7f5ee;
            color: #1f7555;
        }

        .ml-stance-watch {
            background: #fff0d6;
            color: #976114;
        }

        .ml-stance-review {
            background: #eaf0f7;
            color: #365b88;
        }

        .ml-active-summary {
            margin-top: 1rem;
            padding-top: 0.9rem;
            border-top: 1px solid #e8edf3;
        }

        .ml-active-status-title {
            color: #10233f;
            font-size: 1rem;
            font-weight: 800;
        }

        .ml-active-status-text {
            color: #56667a;
            font-size: 0.9rem;
            line-height: 1.55;
            margin-top: 0.2rem;
        }

        .ml-active-metrics {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.7rem;
            margin-top: 1rem;
        }

        .ml-active-metric {
            background: rgba(255,255,255,.75);
            border: 1px solid #e2e8ef;
            border-radius: 9px;
            padding: 0.7rem 0.8rem;
        }

        .ml-active-metric span {
            display: block;
            color: #748195;
            font-size: 0.68rem;
            font-weight: 750;
            text-transform: uppercase;
            margin-bottom: 0.2rem;
        }

        .ml-active-metric strong {
            color: #17283f;
            font-size: 0.88rem;
        }

        .ml-active-bullish {
            color: #237258 !important;
        }

        .ml-active-bearish {
            color: #a64242 !important;
        }

        .ml-active-neutral {
            color: #98701e !important;
        }

        .ml-active-changes {
            margin-top: 0.9rem;
        }

        .ml-active-change-row {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            border-top: 1px solid #e8edf3;
            padding: 0.65rem 0;
        }

        .ml-active-change-label {
            color: #59697e;
            font-size: 0.82rem;
            font-weight: 700;
        }

        .ml-active-change-values {
            color: #17283f;
            font-size: 0.84rem;
            font-weight: 750;
            text-align: right;
        }

        .ml-active-change-values span {
            color: #96a1b0;
            padding: 0 0.3rem;
        }

        .ml-active-change-badge {
            background: #fff0d8;
            color: #9a6115;
            border-radius: 999px;
            padding: 0.08rem 0.35rem;
            margin-left: 0.35rem;
            font-size: 0.58rem;
            text-transform: uppercase;
        }

        .ml-active-no-change,
        .ml-active-more {
            color: #69788b;
            font-size: 0.84rem;
            padding-top: 0.65rem;
            border-top: 1px solid #e8edf3;
        }

        .ml-active-footer {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            gap: 1rem;
            border-top: 1px solid #e8edf3;
            margin-top: 1rem;
            padding-top: 0.9rem;
        }

        .ml-active-footer span {
            display: block;
            color: #748195;
            font-size: 0.68rem;
            font-weight: 750;
            text-transform: uppercase;
        }

        .ml-active-footer strong {
            color: #26384f;
            font-size: 0.83rem;
        }

        .ml-active-open {
            display: inline-block;
            background: #10233f;
            color: #ffffff !important;
            border-radius: 8px;
            padding: 0.65rem 0.85rem;
            text-decoration: none !important;
            font-size: 0.8rem;
            font-weight: 800;
        }

        .ml-active-open:hover {
            background: #18395f;
        }

        @media (max-width: 850px) {
            .ml-active-summary-grid,
            .ml-active-metrics {
                grid-template-columns: 1fr 1fr;
            }

            .ml-active-footer {
                align-items: stretch;
                flex-direction: column;
            }

            .ml-active-open {
                text-align: center;
            }
        }

        @media (max-width: 550px) {
            .ml-active-summary-grid,
            .ml-active-metrics {
                grid-template-columns: 1fr;
            }

            .ml-active-card-top,
            .ml-active-change-row {
                flex-direction: column;
            }

            .ml-active-right,
            .ml-active-change-values {
                text-align: left;
            }
        }
        .ml-today-panel {
            background: #fffaf3;
            border: 1px solid #ecd3ad;
            border-left: 5px solid #c97832;
            border-radius: 14px;
            padding: 1.25rem 1.35rem;
            margin: 0 0 1.5rem;
        }

        .ml-today-panel-header {
            margin-bottom: 1rem;
        }

        .ml-today-eyebrow {
            color: #68778a;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.065em;
            text-transform: uppercase;
        }

        .ml-today-panel-title {
            color: #10233f;
            font-size: 1.35rem;
            font-weight: 850;
            margin-top: 0.2rem;
        }

        .ml-today-panel-subtitle {
            color: #5b6a7d;
            font-size: 0.88rem;
            line-height: 1.5;
            margin-top: 0.25rem;
        }

        .ml-today-grid {
            display: grid;
            grid-template-columns: repeat(
                2,
                minmax(0, 1fr)
            );
            gap: 0.85rem;
        }

        .ml-today-change-card {
            background: #ffffff;
            border: 1px solid #e1e6ed;
            border-radius: 11px;
            padding: 1rem 1.05rem;
        }

        .ml-today-change-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1rem;
        }

        .ml-today-asset-class {
            color: #778497;
            font-size: 0.65rem;
            font-weight: 800;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .ml-today-asset-name {
            color: #10233f;
            font-size: 1.1rem;
            font-weight: 850;
            margin-top: 0.1rem;
        }

        .ml-today-stance {
            background: #fff0d7;
            color: #946014;
            border-radius: 999px;
            padding: 0.28rem 0.55rem;
            font-size: 0.65rem;
            font-weight: 850;
        }

        .ml-today-change-list {
            border-top: 1px solid #e8edf3;
            margin-top: 0.8rem;
            padding-top: 0.4rem;
        }

        .ml-today-change-row {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            padding: 0.48rem 0;
        }

        .ml-today-change-row span {
            color: #627186;
            font-size: 0.78rem;
            font-weight: 700;
        }

        .ml-today-change-row strong {
            color: #17283f;
            font-size: 0.8rem;
            text-align: right;
        }

        .ml-today-change-row em {
            color: #98a3b2;
            font-style: normal;
            padding: 0 0.25rem;
        }

        .ml-today-more {
            color: #738094;
            font-size: 0.75rem;
            padding-top: 0.45rem;
        }

        .ml-today-open {
            display: inline-block;
            color: #173c68 !important;
            font-size: 0.78rem;
            font-weight: 800;
            text-decoration: none !important;
            margin-top: 0.8rem;
        }

        .ml-today-open:hover {
            text-decoration: underline !important;
        }

        .ml-today-clear {
            background: #f3faf6;
            border: 1px solid #cce5d8;
            border-left: 5px solid #278063;
            border-radius: 13px;
            padding: 1rem 1.2rem;
            margin: 0 0 1.5rem;
        }

        .ml-today-clear-main {
            display: flex;
            align-items: center;
            gap: 0.9rem;
        }

        .ml-today-clear-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 34px;
            height: 34px;
            flex: 0 0 34px;
            border-radius: 50%;
            background: #dff1e8;
            color: #237258;
            font-size: 1rem;
            font-weight: 900;
        }

        .ml-today-clear-title {
            color: #123d30;
            font-size: 1rem;
            font-weight: 850;
            margin-top: 0.1rem;
        }

        .ml-today-clear-text {
            color: #526b61;
            font-size: 0.84rem;
            line-height: 1.5;
            margin-top: 0.15rem;
        }

        @media (max-width: 800px) {
            .ml-today-grid {
                grid-template-columns: 1fr;
            }

            .ml-today-change-row {
                flex-direction: column;
                gap: 0.15rem;
            }

            .ml-today-change-row strong {
                text-align: left;
            }
        }
        /* =========================================================
           ACTIVE IDEAS — FINAL PAGE LAYOUT
           ========================================================= */

        .ml-active-page-header {
            max-width: 1120px;
            margin: 18px auto 20px;
            text-align: center;
        }

        .ml-active-page-title {
            margin: 0;
            color: #10233f;
            font-size: 2.35rem;
            font-weight: 900;
            letter-spacing: -0.045em;
            line-height: 1.08;
        }

        .ml-active-page-subtitle {
            max-width: 760px;
            margin: 9px auto 0;
            color: #53647a;
            font-size: 0.96rem;
            font-weight: 550;
            line-height: 1.6;
        }

        .ml-active-content-shell {
            width: 100%;
            max-width: 1120px;
            margin-left: auto;
            margin-right: auto;
        }


        /* ---------- Compact selectors ---------- */

        div[data-testid="stSelectbox"] label p {
            color: #526176 !important;
            font-size: 0.75rem !important;
            font-weight: 750 !important;
        }

        div[data-testid="stSelectbox"] > div {
            min-height: 42px;
        }


        /* ---------- Compact summary ---------- */

        .ml-active-summary-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 0.8rem;
            margin: 1.15rem 0 1.25rem;
        }

        .ml-active-summary-card {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1rem;

            min-height: 66px;
            padding: 0.8rem 1rem;

            background: #ffffff;
            border: 1px solid #d8e0e9;
            border-radius: 10px;
            box-shadow: 0 3px 10px rgba(15, 35, 63, 0.035);
        }

        .ml-active-summary-label {
            color: #5c6c81;
            font-size: 0.69rem;
            font-weight: 850;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }

        .ml-active-summary-value {
            margin: 0;
            color: #10233f;
            font-size: 1.5rem;
            font-weight: 900;
            line-height: 1;
        }


        /* ---------- Today's changes ---------- */

        .ml-today-clear,
        .ml-today-panel {
            max-width: none;
            margin: 0 0 1.25rem;
        }

        .ml-today-clear {
            padding: 0.9rem 1.05rem;
        }

        .ml-today-clear-title {
            font-size: 1.02rem;
        }

        .ml-today-clear-text {
            color: #465f55;
            font-size: 0.86rem;
            font-weight: 550;
        }


        /* ---------- Section structure ---------- */

        .ml-active-section-divider {
            width: 100%;
            height: 1px;
            margin: 1.7rem 0 1.25rem;
            background: #dbe3eb;
        }

        .ml-active-section-header {
            margin-bottom: 0.9rem;
        }

        .ml-active-section-title {
            margin: 0;
            color: #10233f;
            font-size: 1.35rem;
            font-weight: 900;
            letter-spacing: -0.025em;
        }

        .ml-active-section-subtitle {
            margin: 4px 0 0;
            color: #53647a;
            font-size: 0.9rem;
            font-weight: 550;
            line-height: 1.5;
        }


        /* ---------- Research cards ---------- */

        .ml-active-card {
            padding: 1.15rem 1.25rem;
            margin-bottom: 0.9rem;
            border-radius: 11px;
        }

        .ml-active-name {
            color: #10233f;
            font-size: 1.5rem;
            font-weight: 900;
        }

        .ml-active-class {
            color: #67778c;
            font-size: 0.67rem;
            font-weight: 850;
        }

        .ml-active-status-title {
            color: #10233f;
            font-size: 1.03rem;
            font-weight: 850;
        }

        .ml-active-status-text {
            color: #4f6075;
            font-size: 0.88rem;
            font-weight: 550;
            line-height: 1.5;
        }

        .ml-active-metrics {
            gap: 0.6rem;
            margin-top: 0.85rem;
        }

        .ml-active-metric {
            padding: 0.7rem 0.8rem;
            border-radius: 8px;
        }

        .ml-active-metric span {
            color: #65758a;
            font-size: 0.66rem;
            font-weight: 800;
        }

        .ml-active-metric strong {
            color: #10233f;
            font-size: 0.96rem;
            font-weight: 850;
        }

        .ml-active-no-change {
            color: #526176;
            font-size: 0.85rem;
            font-weight: 550;
        }

        .ml-active-footer span {
            color: #65758a;
            font-size: 0.66rem;
            font-weight: 800;
        }

        .ml-active-footer strong {
            color: #20344e;
            font-size: 0.88rem;
            font-weight: 800;
        }

        .ml-active-open {
            padding: 0.6rem 0.82rem;
            font-size: 0.78rem;
        }


        /* ---------- Mobile ---------- */

        @media (max-width: 850px) {
            .ml-active-page-title {
                font-size: 1.95rem;
            }

            .ml-active-summary-grid {
                grid-template-columns: 1fr;
            }

            .ml-active-summary-card {
                min-height: 58px;
            }
        }
        
        /* Align section headings with Today's Changes and idea cards */

        .ml-active-content-shell {
            width: 100%;
            max-width: 1120px;
            margin-left: auto;
            margin-right: auto;
            box-sizing: border-box;
        }

        .ml-active-section-header {
            width: 100%;
            padding-left: 0;
            padding-right: 0;
            box-sizing: border-box;
        }

        .ml-active-section-divider {
            width: 100%;
            margin-left: 0;
            margin-right: 0;
        }

        .ml-today-clear,
        .ml-today-panel,
        .ml-active-card {
            width: 100%;
            box-sizing: border-box;
        }
        
        .ml-active-card.ml-active-content-shell {
            margin-left: auto;
            margin-right: auto;
            margin-bottom: 0.9rem;
        }

        .ml-today-clear.ml-active-content-shell,
        .ml-today-panel.ml-active-content-shell {
            margin-left: auto;
            margin-right: auto;
            margin-bottom: 1.25rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_todays_changes(
    attention_ideas: tuple[ActiveIdea, ...],
    horizon_months: int,
) -> None:
    material_ideas = tuple(
        idea
        for idea in attention_ideas
        if idea.has_material_change
    )

    unsaved_ideas = tuple(
        idea
        for idea in attention_ideas
        if (
            not idea.has_material_change
            and idea.existing_today is None
        )
    )

    if not material_ideas:
        unsaved_note = ""

        if unsaved_ideas:
            unsaved_note = (
                f"{len(unsaved_ideas)} asset"
                f"{'' if len(unsaved_ideas) == 1 else 's'} "
                "still require a baseline snapshot."
            )

        _html(
            f"""
            <div class="ml-active-content-shell ml-today-clear">
                <div class="ml-today-clear-main">
                    <div class="ml-today-clear-icon">✓</div>

                    <div>
                        <div class="ml-today-eyebrow">
                            Today's Changes
                        </div>

                        <div class="ml-today-clear-title">
                            No material changes detected
                        </div>

                        <div class="ml-today-clear-text">
                            Macro direction, alignment and decision stance
                            remain unchanged across monitored assets.
                            {unsaved_note}
                        </div>
                    </div>
                </div>
            </div>
            """
        )
        return

    cards_html = ""

    for idea in material_ideas:
        material_changes = tuple(
            change
            for change in idea.changes
            if change.material
        )

        change_rows = ""

        for change in material_changes[:3]:
            change_rows += f"""
            <div class="ml-today-change-row">
                <span>{change.label}</span>

                <strong>
                    {change.previous_value}
                    <em>→</em>
                    {change.current_value}
                </strong>
            </div>
            """

        remaining = len(material_changes) - 3

        if remaining > 0:
            change_rows += f"""
            <div class="ml-today-more">
                +{remaining} additional material change{
                    "" if remaining == 1 else "s"
                }
            </div>
            """

        workspace_link = _workspace_link(
            idea,
            horizon_months,
        )

        cards_html += f"""
        <div class="ml-today-change-card">
            <div class="ml-today-change-header">
                <div>
                    <div class="ml-today-asset-class">
                        {idea.asset_class}
                    </div>

                    <div class="ml-today-asset-name">
                        {idea.display_name}
                    </div>
                </div>

                <div class="ml-today-stance">
                    {idea.stance}
                </div>
            </div>

            <div class="ml-today-change-list">
                {change_rows}
            </div>

            <a
                class="ml-today-open"
                href="{workspace_link}"
                target="_self"
            >
                Review Changes →
            </a>
        </div>
        """

    _html(
        f"""
        <div class="ml-active-content-shell ml-today-panel">
            <div class="ml-today-panel-header">
                <div>
                    <div class="ml-today-eyebrow">
                        Today's Changes
                    </div>

                    <div class="ml-today-panel-title">
                        {len(material_ideas)} asset{
                            "" if len(material_ideas) == 1 else "s"
                        } require review
                    </div>

                    <div class="ml-today-panel-subtitle">
                        These assets experienced a material change in
                        macro, price alignment or decision status.
                    </div>
                </div>
            </div>

            <div class="ml-today-grid">
                {cards_html}
            </div>
        </div>
        """
    )

def render_active_ideas_page() -> None:
    _inject_active_ideas_css()
    
    render_page_intro(
        title="Active Ideas",
        description=(
            "See which monitored markets have experienced meaningful changes "
            "in macro conditions, price behaviour or research status. This page "
            "highlights assets that deserve further review rather than providing "
            "automatic trading signals."
        ),
        guide=(
            "Start with Today's Changes to see which assets require attention. "
            "Then open the Research Workspace to understand what changed, why it "
            "matters and whether the current macro view still aligns with market "
            "behaviour."
        ),
        max_width=1120,
    )

    available_assets = get_available_assets()

    asset_classes = sorted(
        {
            asset.asset_class
            for asset in available_assets
        }
    )


    # ---------------------------------------------------------
    # Compact centered controls
    # ---------------------------------------------------------

    left_space, filter_col, horizon_col, right_space = st.columns(
        [1.4, 1, 1, 1.4]
    )

    with filter_col:
        selected_class = st.selectbox(
            "Asset Class",
            options=["All"] + asset_classes,
            index=0,
            key="active_ideas_asset_class",
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
            key="active_ideas_horizon",
        )

    resolved_class = (
        None
        if selected_class == "All"
        else selected_class
    )

    with st.spinner("Reviewing active research ideas..."):
        ideas = load_active_ideas(
            asset_class=resolved_class,
            horizon_months=selected_horizon,
        )

    attention_ideas = tuple(
        idea
        for idea in ideas
        if idea.needs_attention
    )

    stable_ideas = tuple(
        idea
        for idea in ideas
        if not idea.needs_attention
    )

    # ---------------------------------------------------------
    # Summary metrics
    # ---------------------------------------------------------

    _html(
        f"""
        <div class="ml-active-content-shell">
            <div class="ml-active-summary-grid">
                <div class="ml-active-summary-card">
                    <div class="ml-active-summary-label">
                        Assets Monitored
                    </div>

                    <div class="ml-active-summary-value">
                        {len(ideas)}
                    </div>
                </div>

                <div class="ml-active-summary-card">
                    <div class="ml-active-summary-label">
                        Require Attention
                    </div>

                    <div class="ml-active-summary-value">
                        {len(attention_ideas)}
                    </div>
                </div>

                <div class="ml-active-summary-card">
                    <div class="ml-active-summary-label">
                        Current Views
                    </div>

                    <div class="ml-active-summary-value">
                        {len(stable_ideas)}
                    </div>
                </div>
            </div>
        </div>
        """
    )

    # ---------------------------------------------------------
    # Today's change summary
    # ---------------------------------------------------------

    _render_todays_changes(
        attention_ideas=attention_ideas,
        horizon_months=selected_horizon,
    )

    # ---------------------------------------------------------
    # Assets requiring attention
    # ---------------------------------------------------------

    if attention_ideas:
        _html(
            """
            <div class="ml-active-content-shell">
                <div class="ml-active-section-divider"></div>

                <div class="ml-active-section-header">
                    <div class="ml-active-section-title">
                        Requires Attention
                    </div>

                    <div class="ml-active-section-subtitle">
                        Material model changes or unsaved states
                        that should be reviewed.
                    </div>
                </div>
            </div>
            """
        )

        for idea in attention_ideas:
            _render_idea_card(
                idea,
                selected_horizon,
            )

    # ---------------------------------------------------------
    # Current asset views
    # ---------------------------------------------------------

    if stable_ideas:
        _html(
            """
            <div class="ml-active-content-shell">
                <div class="ml-active-section-divider"></div>

                <div class="ml-active-section-header">
                    <div class="ml-active-section-title">
                        Current Views
                    </div>

                    <div class="ml-active-section-subtitle">
                        The latest model view for each monitored asset.
                    </div>
                </div>
            </div>
            """
        )

        for idea in stable_ideas:
            _render_idea_card(
                idea,
                selected_horizon,
            )