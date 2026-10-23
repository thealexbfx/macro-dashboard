from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from backend.app.registry.economic_indicators import EconomicIndicatorRegistry
from backend.app.registry.markets import MarketRegistry
from backend.app.services.historical_relationships import RelationshipSeriesRegistry


class ResearchIntent(str, Enum):
    FACTUAL_LOOKUP = "factual_lookup"
    MARKET_LOOKUP = "market_lookup"
    MARKET_CALCULATION = "market_calculation"
    CONCEPT_EXPLANATION = "concept_explanation"
    CURRENT_MARKET_MOVE = "current_market_move"
    MACRO_ANALYSIS = "macro_analysis"
    HISTORICAL_RELATIONSHIP = "historical_relationship"
    SCENARIO_ANALYSIS = "scenario_analysis"
    OUT_OF_SCOPE = "out_of_scope"


@dataclass(frozen=True)
class ResearchPlan:
    intent: ResearchIntent
    assets: tuple[str, ...] = ()
    economies: tuple[str, ...] = ()
    indicators: tuple[str, ...] = ()
    timeframe: str | None = None
    data_needs: tuple[str, ...] = ()
    answer_depth: str = "answer"
    requires_web: bool = False
    supported_now: bool = False
    rationale: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["intent"] = self.intent.value
        for key in ("assets", "economies", "indicators", "data_needs"):
            payload[key] = list(payload[key])
        return payload


class ResearchPlanner:
    """Deterministic production planner.

    V1 starts inspectable and cheap. A constrained LLM interpretation layer can be
    added later without changing this plan contract or granting the model tool access.
    """

    def __init__(self) -> None:
        self.markets = MarketRegistry()
        self.relationship_series = RelationshipSeriesRegistry()
        self.indicators = EconomicIndicatorRegistry()

    @staticmethod
    def _timeframe(q: str) -> str | None:
        mappings = (
            (("year to date", "ytd"), "ytd"),
            (("six months", "6 months", "6-month", "6 month"), "6_months"),
            (("three months", "3 months", "3-month", "3 month"), "3_months"),
            (("one year", "1 year", "12 months", "year"), "1_year"),
            (("one month", "1 month", "month"), "1_month"),
            (("one week", "1 week", "week"), "1_week"),
            (("today", "this morning", "intraday"), "today"),
        )
        for terms, value in mappings:
            if any(term in q for term in terms):
                return value
        return None

    def plan(self, question: str) -> ResearchPlan:
        q = " ".join(question.lower().split())
        assets = tuple(spec.key for spec in self.relationship_series.resolve_all(q))
        economy = "usa"
        if any(x in q for x in ("uk", "britain", "british", "united kingdom")):
            economy = "uk"
        elif any(x in q for x in ("euro area", "eurozone", "ecb")):
            economy = "euro"
        elif "japan" in q or "boj" in q:
            economy = "japan"
        indicator = self.indicators.resolve(q, economy=economy)
        timeframe = self._timeframe(q)

        movement_terms = ("why", "what happened", "driving", "driver", "causing", "spike", "rally", "selloff", "falling", "rising")
        relationship_terms = ("relationship", "correlation", "move inversely", "moves inversely", "when", "historically", "normally happen", " versus ", " vs ", "lead", "lag")
        calculation_terms = ("how much", "return", "performed", "performance", "change over", "moved over", "risen", "fallen")
        macro_terms = ("recession", "economy", "economic", "inflation", "labour market", "labor market", "growth", "liquidity", "fed", "ecb", "boe", "boj", "policy")
        explicit_current = any(x in q for x in ("today", "this morning", "right now", "currently", "latest move", "what happened"))
        conceptual = any(x in q for x in ("why do", "why does", "how does", "what does", "explain", "mean")) and not explicit_current

        if indicator and not (len(assets) >= 2 and any(x in q for x in relationship_terms)) and any(x in q for x in ("latest", "current", "what was", "what is", "print", "reading", "rate")):
            return ResearchPlan(ResearchIntent.FACTUAL_LOOKUP, economies=(economy,), indicators=(indicator.key,), data_needs=("economic_data",), supported_now=(economy == "usa"), rationale="Resolved a registered economic indicator lookup.")

        if len(assets) >= 2 and any(x in q for x in relationship_terms) and not conceptual:
            return ResearchPlan(ResearchIntent.HISTORICAL_RELATIONSHIP, assets=assets[:2], timeframe=timeframe or "5_years", data_needs=("market_history", "calculation", "historical_context", "macro_regimes"), answer_depth="investigate", supported_now=True, rationale="Detected a historical relationship question between supported market series.")

        if len(assets) >= 2 and any(x in q for x in ("correlation", "move inversely", "moves inversely", "relationship", "historically")):
            return ResearchPlan(ResearchIntent.HISTORICAL_RELATIONSHIP, assets=assets[:2], timeframe=timeframe or "5_years", data_needs=("market_history", "calculation", "historical_context", "macro_regimes"), answer_depth="investigate", supported_now=True, rationale="Detected a historical relationship question between supported market series.")

        if assets and any(x in q for x in calculation_terms) and timeframe:
            return ResearchPlan(ResearchIntent.MARKET_CALCULATION, assets=(assets[0],), timeframe=timeframe, data_needs=("market_history", "calculation"), answer_depth="answer", supported_now=True, rationale="Detected a period market calculation.")

        if conceptual:
            return ResearchPlan(ResearchIntent.CONCEPT_EXPLANATION, assets=assets[:2], economies=(economy,), indicators=(indicator.key,) if indicator else (), data_needs=("macro_engine", "economic_data") if indicator else (), answer_depth="explain", supported_now=False, rationale="Detected a conceptual/mechanism explanation rather than a claim about the current move.")

        if assets and any(x in q for x in movement_terms):
            supported_assets = {"gold", "dxy", "sp500", "us2y", "us10y", "us30y"}
            return ResearchPlan(ResearchIntent.CURRENT_MARKET_MOVE, assets=(assets[0],), timeframe=timeframe or "current", data_needs=("market_snapshot", "cross_asset_evidence", "macro_engine", "web_research"), answer_depth="investigate", requires_web=True, supported_now=assets[0] in supported_assets, rationale="Detected a current market-move investigation using MacroLens cross-market evidence and targeted catalyst research.")

        if assets and any(x in q for x in ("latest", "current", "price", "trading", "level", "where is")):
            return ResearchPlan(ResearchIntent.MARKET_LOOKUP, assets=(assets[0],), data_needs=("market_snapshot",), supported_now=True, rationale="Detected a direct market lookup.")

        if any(x in q for x in macro_terms):
            return ResearchPlan(ResearchIntent.MACRO_ANALYSIS, economies=(economy,), data_needs=("macro_engine",), answer_depth="explain", supported_now=True, rationale="Detected a macro question that can use the existing MacroLens environment engine.")

        if any(x in q for x in ("what if", "if the fed", "if inflation", "would happen", "scenario")):
            return ResearchPlan(ResearchIntent.SCENARIO_ANALYSIS, assets=assets[:1], economies=(economy,), data_needs=("macro_engine", "historical_context"), answer_depth="explain", supported_now=False, rationale="Detected a scenario question; production scenario execution is not wired yet.")

        if any(x in q for x in ("what does", "why do", "why does", "explain", "mean")):
            return ResearchPlan(ResearchIntent.CONCEPT_EXPLANATION, assets=assets[:1], economies=(economy,) if economy else (), answer_depth="explain", supported_now=False, rationale="Detected a conceptual explanation. AI synthesis is intentionally not the first production slice.")

        return ResearchPlan(ResearchIntent.OUT_OF_SCOPE, assets=assets[:2], economies=(economy,) if economy else (), supported_now=False, rationale="No production-safe V1 capability matched the question yet.")
