from datetime import date

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.registry.markets import MarketSpec
from backend.app.research.planner import ResearchIntent, ResearchPlanner
from backend.app.services.ask import AskService
from backend.app.services.direct_answers import DirectAnswerService


class FakeSeriesProvider:
    def market_series(self, spec: MarketSpec, start: date, end: date):
        if spec.kind == "yield":
            return [(date(2026, 3, 2), 4.50), (date(2026, 9, 2), 4.80)]
        return [(date(2026, 3, 2), 2000.0), (date(2026, 9, 2), 2300.0)]

    def fred_series(self, series_id: str, start: date, end: date):
        if series_id == "CPIAUCSL":
            # 15 monthly observations; latest YoY = 3.0%, prior YoY = 2.0%.
            values = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.12, 114.24]
            return [(date(2025 + (i // 12), (i % 12) + 1, 1), value) for i, value in enumerate(values)]
        return [(date(2026, 3, 2), 4.50), (date(2026, 9, 2), 4.80)]


def test_planner_distinguishes_lookup_calculation_and_investigation():
    planner = ResearchPlanner()
    assert planner.plan("What is the latest gold price?").intent == ResearchIntent.MARKET_LOOKUP
    assert planner.plan("How much has gold moved over six months?").intent == ResearchIntent.MARKET_CALCULATION
    assert planner.plan("Why is gold rising today?").intent == ResearchIntent.CURRENT_MARKET_MOVE


def test_market_lookup_returns_unified_customer_answer():
    service = AskService(direct=DirectAnswerService(provider=FakeSeriesProvider(), today_fn=lambda: date(2026, 9, 2)))
    payload = service.ask("What is the latest gold price?")
    assert payload["customer_answer"]["status"] == "ok"
    assert payload["customer_answer"]["blocks"][0]["type"] == "market_metric"
    assert payload["research_plan"]["intent"] == "market_lookup"


def test_market_period_calculation_is_computed_by_macrolens():
    service = AskService(direct=DirectAnswerService(provider=FakeSeriesProvider(), today_fn=lambda: date(2026, 9, 2)))
    payload = service.ask("How much has gold moved over six months?")
    block = payload["customer_answer"]["blocks"][0]
    assert block["type"] == "period_change"
    assert round(block["data"]["return_pct"], 1) == 15.0


def test_cpi_lookup_uses_registry_and_structured_evidence():
    service = AskService(direct=DirectAnswerService(provider=FakeSeriesProvider(), today_fn=lambda: date(2026, 9, 2)))
    payload = service.ask("What was the latest US CPI print?")
    assert payload["research_plan"]["intent"] == "factual_lookup"
    block = payload["customer_answer"]["blocks"][0]
    assert block["type"] == "economic_indicator"
    assert block["data"]["macro_pillar"] == "Inflation"


def test_current_move_is_now_planned_as_supported_research():
    plan = ResearchPlanner().plan("Why is gold rising today?")
    assert plan.intent == ResearchIntent.CURRENT_MARKET_MOVE
    assert plan.supported_now is True
    assert plan.requires_web is True


def test_plan_endpoint_is_available():
    client = TestClient(app)
    response = client.post("/api/ask/plan", json={"question": "How much has gold moved over six months?"})
    assert response.status_code == 200
    assert response.json()["research_plan"]["intent"] == "market_calculation"
