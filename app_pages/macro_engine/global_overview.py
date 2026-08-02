from __future__ import annotations
from macro_engine.cache.storage import load_cache
from dataclasses import dataclass
from datetime import date
from html import escape
from typing import Callable

import streamlit as st

from app_pages.macro_engine.loaders import (
    CACHE_TTL_SECONDS,
    JAPAN_HISTORY_START_DATE,
    STANDARD_HISTORY_START_DATE,
    load_euro_environment_history,
    load_euro_macro_environment,
    load_japan_environment_history,
    load_japan_macro_environment,
    load_uk_environment_history,
    load_uk_macro_environment,
    load_usa_environment_history,
    load_usa_macro_environment,
)
from components.macro_engine.formatting import (
    display_date,
    format_percentage,
)
from macro_engine.comparison import (
    build_recent_environment_change,
    economy_display_name,
    pillar_for,
)
from macro_engine.models.environment import MacroEnvironmentResult
from macro_engine.pipelines.history import HistoricalEnvironmentRun
from styles.macro_engine import inject_macro_engine_css


@dataclass(frozen=True)
class EconomySource:
    name: str
    page: str
    history_start_date: date
    environment_loader: Callable[
        [],
        MacroEnvironmentResult,
    ]
    history_loader: Callable[
        [date, date],
        HistoricalEnvironmentRun,
    ]


@dataclass(frozen=True)
class EconomyLoad:
    source: EconomySource
    result: MacroEnvironmentResult | None = None
    history_run: HistoricalEnvironmentRun | None = None
    environment_error: str | None = None
    history_error: str | None = None



ECONOMIES = (
    EconomySource(
        "United States",
        "MacroEngineUSA",
        STANDARD_HISTORY_START_DATE,
        load_usa_macro_environment,
        load_usa_environment_history,
    ),
    EconomySource(
        "Euro Area",
        "MacroEngineEuro",
        STANDARD_HISTORY_START_DATE,
        load_euro_macro_environment,
        load_euro_environment_history,
    ),
    EconomySource(
        "United Kingdom",
        "MacroEngineUK",
        STANDARD_HISTORY_START_DATE,
        load_uk_macro_environment,
        load_uk_environment_history,
    ),
    EconomySource(
        "Japan",
        "MacroEngineJapan",
        JAPAN_HISTORY_START_DATE,
        load_japan_macro_environment,
        load_japan_environment_history,
    ),
)


PILLAR_NAMES = ("Growth", "Inflation", "Labor", "Liquidity", "Policy")


def _load_economy(
    source: EconomySource,
) -> EconomyLoad:

    CACHE_NAMES = {
        "United States": "usa_environment",
        "Euro Area": "euro_environment",
        "United Kingdom": "uk_environment",
        "Japan": "japan_environment",
    }

    try:

        result = load_cache(
            CACHE_NAMES[source.name]
        )

    except Exception as exc:

        return EconomyLoad(
            source=source,
            environment_error=str(exc),
        )

    return EconomyLoad(
        source=source,
        result=result,
        history_run=None,
    )


def _pillar_tone(pillar) -> str:
    label = pillar.state_label.casefold()
    if "very strong" in label or label == "strong":
        return "positive"
    if "very weak" in label:
        return "negative"
    if "weak" in label:
        return "caution"
    return "neutral"


def _pillar_profile_label(name: str, score: float, state_label: str) -> str:
    if name in {"Liquidity", "Policy"}:
        if score >= 0.10:
            return "Supportive"
        if score <= -0.10:
            return "Restrictive"
        return "Neutral"
    return state_label


def _environment_tone(label: str) -> str:
    normalized = label.casefold()
    if "contraction" in normalized or "slowdown" in normalized:
        return "environment-negative"
    if "recovery" in normalized or "disinflationary expansion" in normalized:
        return "environment-recovery"
    if "expansion" in normalized or "reflation" in normalized:
        return "environment-positive"
    return "environment-transition"


def _recent_change(load: EconomyLoad):
    if load.result is None:
        return None
    history = getattr(load.history_run, "history", None)
    snapshots = getattr(history, "snapshots", ())
    return build_recent_environment_change(load.result, snapshots)


def _short_name(economy: str) -> str:
    return {
        "United States": "US",
        "United Kingdom": "UK",
        "Euro Area": "Euro Area",
        "Japan": "Japan",
    }.get(economy, economy)


def _pillar_extreme(
    results: tuple[MacroEnvironmentResult, ...],
    pillar_name: str,
    *,
    strongest: bool,
):
    available = [(result, pillar_for(result, pillar_name)) for result in results]
    available = [(result, pillar) for result, pillar in available if pillar is not None]
    if not available:
        return None
    selector = max if strongest else min
    return selector(available, key=lambda item: item[1].state_score)


def _takeaway_for(
    result: MacroEnvironmentResult,
    results: tuple[MacroEnvironmentResult, ...],
) -> str:
    economy = economy_display_name(result.economy)
    strongest_growth = _pillar_extreme(results, "Growth", strongest=True)
    weakest_liquidity = _pillar_extreme(results, "Liquidity", strongest=False)

    if strongest_growth and strongest_growth[0] is result:
        return f"{_short_name(economy)} growth continues to lead."
    if weakest_liquidity and weakest_liquidity[0] is result:
        labor = pillar_for(result, "Labor")
        if labor is not None and labor.state_score >= 0.20:
            return f"Liquidity remains weakest despite {labor.state_label.lower()} labour."
        return "Liquidity remains the weakest pillar."
    if economy == "United Kingdom":
        impulse = result.inflation_impulse_label.casefold()
        inflation_story = "Inflation is easing" if "eas" in impulse else "Inflation is moderating"
        return f"{inflation_story} while policy stays restrictive."

    stable_pillars = sum(
        1
        for name in PILLAR_NAMES
        if (pillar := pillar_for(result, name)) is not None
        and pillar.trend_label.casefold() == "stable"
    )
    if stable_pillars >= 3:
        return "Broadly stable across most pillars."
    return "The current profile is holding broadly steady."



def _meter(value: float, *, score: bool = False) -> str:
    percent = (value + 1.0) * 50.0 if score else value * 100.0
    return f"{max(4.0, min(100.0, percent)):.0f}%"


def _direction_mark(direction: str) -> str:
    normalized = direction.casefold()
    if "improv" in normalized or "acceler" in normalized or "expand" in normalized:
        return "↑"
    if "deterior" in normalized or "weaken" in normalized or "contract" in normalized:
        return "↓"
    return "→"


def _scoreboard_html(
    loads: tuple[EconomyLoad, ...],
    results: tuple[MacroEnvironmentResult, ...],
) -> str:
    cards = []
    for load in loads:
        if load.result is None:
            cards.append(
                f"""
                <div class="ml-overview-economy unavailable">
                    <div class="ml-overview-country">{escape(load.source.name)}</div>
                    <strong>Temporarily unavailable</strong>
                    <p>The current model output could not be loaded.</p>
                </div>
                """
            )
            continue

        result = load.result
        pillar_rows = []
        for name in PILLAR_NAMES:
            pillar = pillar_for(result, name)
            if pillar is None:
                continue
            tone = _pillar_tone(pillar)
            profile_label = _pillar_profile_label(name, pillar.state_score, pillar.state_label)
            pillar_rows.append(
                f"""
                <div class="ml-overview-pillar-row">
                    <span>{escape(name)}</span>
                    <div class="ml-overview-pillar-track"><i class="{tone}" style="width:{_meter(pillar.state_score, score=True)}"></i></div>
                    <strong>{escape(profile_label)}</strong>
                </div>
                """
            )

        cards.append(
            f"""
            <a class="ml-overview-economy {_environment_tone(result.environment_label)}" href="?page={load.source.page}" target="_self">
                <div class="ml-overview-card-top">
                    <div class="ml-overview-country">{escape(load.source.name)}</div>
                    <span>Full analysis →</span>
                </div>
                <div class="ml-overview-regime">{escape(result.environment_label)}</div>
                <div class="ml-overview-direction">{_direction_mark(result.overall_direction)} {escape(result.overall_direction)}</div>
                <div class="ml-overview-card-metrics">
                    <div>
                        <label><span>Confidence</span><b>{format_percentage(result.confidence_score)}</b></label>
                        <div class="ml-overview-metric-track"><i class="confidence" style="width:{_meter(result.confidence_score)}"></i></div>
                    </div>
                    <div>
                        <label><span>Conviction</span><b>{format_percentage(result.environment_conviction_score)}</b></label>
                        <div class="ml-overview-metric-track"><i class="conviction {'low' if result.environment_conviction_score < 0.35 else ''}" style="width:{_meter(result.environment_conviction_score)}"></i></div>
                    </div>
                </div>
                <div class="ml-overview-profile-head"><b>Macro profile</b><span>Weak</span><span>Strong</span></div>
                <div class="ml-overview-pillars">{''.join(pillar_rows)}</div>
                <div class="ml-overview-takeaway">{escape(_takeaway_for(result, results))}</div>
                <div class="ml-overview-asof">As of {display_date(result.as_of_date)}</div>
            </a>
            """
        )
    return f'<div class="ml-overview-economy-grid">{"".join(cards)}</div>'


def _morning_brief_html(
    loads: tuple[EconomyLoad, ...],
    results: tuple[MacroEnvironmentResult, ...],
) -> str:
    if not results:
        return ""

    strongest_growth = _pillar_extreme(
        results,
        "Growth",
        strongest=True,
    )

    weakest_liquidity = _pillar_extreme(
        results,
        "Liquidity",
        strongest=False,
    )

    brief_items: list[
        tuple[str, str, str]
    ] = []

    if strongest_growth:
        result, pillar = strongest_growth
        economy = economy_display_name(
            result.economy
        )

        brief_items.append(
            (
                "Growth Leader",
                economy,
                (
                    f"{_short_name(economy)} activity remains "
                    f"the strongest of the four tracked economies, "
                    f"with growth currently classified as "
                    f"{pillar.state_label.lower()}."
                ),
            )
        )

    if weakest_liquidity:
        result, pillar = weakest_liquidity
        economy = economy_display_name(
            result.economy
        )

        labor = pillar_for(
            result,
            "Labor",
        )

        if (
            labor is not None
            and labor.state_score >= 0.20
        ):
            explanation = (
                f"Liquidity remains the weakest in {economy}, "
                f"despite {labor.state_label.lower()} labour "
                "conditions."
            )
        else:
            explanation = (
                f"{economy} currently has the weakest liquidity "
                f"profile, classified as "
                f"{pillar.state_label.lower()}."
            )

        brief_items.append(
            (
                "Liquidity Watch",
                economy,
                explanation,
            )
        )

    uk_result = next(
        (
            result
            for result in results
            if economy_display_name(
                result.economy
            ) == "United Kingdom"
        ),
        None,
    )

    if uk_result is not None:
        policy = pillar_for(
            uk_result,
            "Policy",
        )

        if (
            policy is not None
            and policy.state_score <= -0.10
        ):
            uk_story = (
                "Inflation momentum is easing, but restrictive "
                "policy continues to constrain the outlook."
            )
        else:
            uk_story = (
                "The UK remains in a transitional environment "
                "with limited model conviction."
            )

        brief_items.append(
            (
                "Policy–Inflation Gap",
                "United Kingdom",
                uk_story,
            )
        )

    cards_html = "".join(
        f"""
        <article class="ml-overview-brief-item">
            <div class="ml-overview-brief-item-label">
                {escape(label)}
            </div>

            <div class="ml-overview-brief-item-economy">
                {escape(economy)}
            </div>

            <p>
                {escape(explanation)}
            </p>
        </article>
        """
        for label, economy, explanation
        in brief_items[:3]
    )

    return f"""
    <section class="ml-overview-brief">
        <div class="ml-overview-brief-header">
            <div>
                <div class="ml-overview-brief-kicker">
                    Daily Model Summary
                </div>

                <div class="ml-overview-brief-title">
                    Morning Brief
                </div>
            </div>

            <div class="ml-overview-brief-note">
                Key conditions surfaced by the current models
            </div>
        </div>

        <div class="ml-overview-brief-grid">
            {cards_html}
        </div>
    </section>
    """


def _comparison_html(
    loads: tuple[EconomyLoad, ...],
    results: tuple[MacroEnvironmentResult, ...],
) -> str:
    abbreviations = ("US", "EA", "UK", "JP")
    matrix_rows = []
    for name in PILLAR_NAMES:
        cells = []
        for load in loads:
            pillar = pillar_for(load.result, name) if load.result is not None else None
            if pillar is None:
                cells.append('<span class="unavailable">—</span>')
            else:
                cells.append(
                    f'<span class="{_pillar_tone(pillar)}" title="{escape(pillar.state_label)} · {escape(pillar.trend_label)}"></span>'
                )
        matrix_rows.append(
            f'<div class="ml-overview-heat-row"><b>{escape(name)}</b>{"".join(cells)}</div>'
        )

    highlight_specs = []
    growth = _pillar_extreme(results, "Growth", strongest=True)
    liquidity = _pillar_extreme(results, "Liquidity", strongest=False)
    inflation = _pillar_extreme(results, "Inflation", strongest=True)
    if growth:
        name = economy_display_name(growth[0].economy)
        highlight_specs.append((name, "Strongest Growth", f"{_short_name(name)} growth continues to lead the four tracked economies."))
    if liquidity:
        name = economy_display_name(liquidity[0].economy)
        highlight_specs.append((name, "Weakest Liquidity", f"{name} continues to have the weakest liquidity conditions."))
    if inflation:
        name = economy_display_name(inflation[0].economy)
        highlight_specs.append((name, "Highest Inflation", f"Inflation pressures remain strongest in {_short_name(name)}."))
    if results:
        lowest_conviction = min(results, key=lambda item: item.environment_conviction_score)
        name = economy_display_name(lowest_conviction.economy)
        highlight_specs.append((name, "Lowest Conviction", f"{name} has the lowest model conviction this month."))

    highlights = "".join(
        f"""
        <article class="ml-overview-highlight">
            <div class="ml-overview-insight-state {('positive' if title in {'Strongest Growth'} else 'caution' if title == 'Lowest Conviction' else 'negative')}"></div>
            <div><h3>{escape(title)}</h3><h4>{escape(name)}</h4><p>{escape(story)}</p></div>
        </article>
        """
        for name, title, story in highlight_specs
    )

    return f"""
    <div class="ml-overview-two-up">
        <section class="ml-overview-panel ml-overview-comparison">
            <div class="ml-overview-panel-title">Cross-Economy Heatmap</div>
            <div class="ml-overview-heat-head"><span></span>{''.join(f'<b>{abbr}</b>' for abbr in abbreviations)}</div>
            {''.join(matrix_rows)}
            <div class="ml-overview-legend"><span class="positive"></span> Strong <span class="neutral"></span> Normal <span class="caution"></span> Caution <span class="negative"></span> Weak</div>
        </section>
        <section class="ml-overview-panel ml-overview-highlights">
            <div class="ml-overview-panel-title">Key Model Insights</div>
            <div class="ml-overview-highlight-list">{highlights}</div>
        </section>
    </div>
    """


def _changes_html(loads: tuple[EconomyLoad, ...]) -> str:
    cards = []
    for load in loads:
        if load.result is None:
            body = '<div class="ml-overview-no-change">Current model unavailable</div>'
            status = "unavailable"
        else:
            change = _recent_change(load)
            if change is None:
                body = '<div class="ml-overview-no-change">History unavailable</div>'
                status = "unavailable"
            elif change.changed:
                body = f"""
                    <span class="ml-overview-new-badge">New</span>
                    <div class="ml-overview-regime-shift">
                        <span>{escape(change.previous_environment)}</span>
                        <i>↓</i>
                        <strong>{escape(change.current_environment)}</strong>
                    </div>
                """
                status = "changed"
            else:
                body = f'<div class="ml-overview-no-change">Stable this month<small>Current regime: {escape(change.current_environment)}</small></div>'
                status = "unchanged"
        cards.append(
            f'<article class="ml-overview-change-card {status}"><h3>{escape(load.source.name)}</h3><div class="ml-overview-timeline-dot"></div>{body}</article>'
        )

    return f"""
    <section class="ml-overview-panel ml-overview-changes">
        <div class="ml-overview-panel-title">What Changed This Month</div>
        <div class="ml-overview-change-grid">{''.join(cards)}</div>
    </section>
    """


def _resources_html(
    results: tuple[MacroEnvironmentResult, ...],
) -> str:
    watch_items = []

    for result in sorted(
        results,
        key=lambda item: (
            item.environment_conviction_score
        ),
    ):
        name = economy_display_name(
            result.economy
        )

        pillars = [
            pillar_for(
                result,
                pillar_name,
            )
            for pillar_name in PILLAR_NAMES
        ]

        pillars = [
            pillar
            for pillar in pillars
            if pillar is not None
        ]

        weakest = (
            min(
                pillars,
                key=lambda item: item.state_score,
            )
            if pillars
            else None
        )

        labor = pillar_for(
            result,
            "Labor",
        )

        liquidity = pillar_for(
            result,
            "Liquidity",
        )

        policy = pillar_for(
            result,
            "Policy",
        )

        if (
            liquidity is not None
            and labor is not None
            and liquidity.state_score <= -0.50
            and labor.state_score >= 0.20
        ):
            label = "Liquidity Divergence"
            reason = (
                "Liquidity is very weak while labour remains "
                "strong."
            )
            tone = "negative"

        elif (
            policy is not None
            and policy.state_score <= -0.20
            and "eas" in (
                result.inflation_impulse_label.casefold()
            )
        ):
            label = "Policy–Inflation Gap"
            reason = (
                "Inflation is easing, but policy remains "
                "restrictive."
            )
            tone = "caution"

        elif (
            result.environment_conviction_score
            < 0.35
        ):
            label = "Low Conviction"
            reason = (
                "The current environment classification is "
                "less firmly established than in peer economies."
            )
            tone = "caution"

        elif (
            "transition"
            in result.environment_label.casefold()
        ):
            label = "Transitional Regime"
            reason = (
                "The economy remains between more clearly "
                "defined macro environments."
            )
            tone = "caution"

        elif weakest is not None:
            pillar_name = (
                weakest.name.split()[-1]
            )

            label = f"{pillar_name} Watch"

            reason = (
                f"{pillar_name} is currently "
                f"{weakest.state_label.lower()} and "
                f"{weakest.trend_label.lower()}."
            )

            tone = _pillar_tone(
                weakest
            )

        else:
            label = "Model Watch"
            reason = (
                "Monitor the next scheduled model update."
            )
            tone = "neutral"

        watch_items.append(
            f"""
            <article class="ml-overview-watch-item">
                <div class="ml-overview-watch-marker {tone}">
                </div>

                <div class="ml-overview-watch-content">
                    <div class="ml-overview-watch-top">
                        <strong>{escape(name)}</strong>

                        <span class="{tone}">
                            {escape(label)}
                        </span>
                    </div>

                    <p>{escape(reason)}</p>
                </div>
            </article>
            """
        )

    return f"""
    <div class="ml-overview-two-up ml-overview-resources">
        <section class="ml-overview-panel ml-overview-watch-panel">
            <div class="ml-overview-panel-heading">
                <div>
                    <div class="ml-overview-panel-kicker">
                        Model Monitoring
                    </div>

                    <div class="ml-overview-panel-title">
                        Watchlist
                    </div>
                </div>

                <span>
                    {len(watch_items)} economies
                </span>
            </div>

            <div class="ml-overview-watchlist">
                {''.join(watch_items)}
            </div>
        </section>

        <section class="ml-overview-panel ml-overview-research-panel">
            <div class="ml-overview-panel-heading">
                <div>
                    <div class="ml-overview-panel-kicker">
                        MacroLens Publications
                    </div>

                    <div class="ml-overview-panel-title">
                        Latest Research
                    </div>
                </div>
            </div>

            <div class="ml-overview-research-empty">
                <div class="ml-overview-research-empty-label">
                    Research Library
                </div>

                <strong>
                    No published research yet
                </strong>

                <p>
                    Structured MacroLens outlooks and research
                    notes will appear here as they are published.
                </p>

                <a
                    href="?page=ResearchNotes"
                    target="_self"
                >
                    Open Research Notes →
                </a>
            </div>
        </section>
    </div>
    """


def render_macro_engine_global_page() -> None:
    inject_macro_engine_css()

    with st.spinner(
        "Loading macro environments..."
    ):
        loads = tuple(
            _load_economy(source)
            for source in ECONOMIES
        )

    results = tuple(
        load.result
        for load in loads
        if load.result is not None
    )

    st.html(
        f"""
        <main class="ml-global-dashboard">
            <section class="ml-overview-hero">
                <h1>Global Macro Monitor</h1>

                <p>
                    A comparative view of current macroeconomic conditions
                    across the United States, Euro Area, United Kingdom
                    and Japan.
                </p>
            </section>
            {_morning_brief_html(loads, results)}
            {_scoreboard_html(loads, results)}
            {_comparison_html(loads, results)}
            {_resources_html(results)}
            <footer class="ml-overview-methodology">
                Macro Engine classifications are objective model outputs—not forecasts or investment views.
                Economy pages contain the underlying evidence and full analysis.
            </footer>
        </main>
        """
    )
