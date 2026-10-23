from datetime import date, timedelta
from types import SimpleNamespace

from backend.app.research.planner import ResearchIntent, ResearchPlanner
from backend.app.services.ask import AskService
from backend.app.services.catalysts import CatalystCandidate, CatalystSearchResult
from backend.app.services.current_moves import CurrentMoveInvestigationService
from backend.app.services.direct_answers import DirectAnswerService
from backend.app.services.historical_relationships import HistoricalRelationshipService, MacroRegimeHistoryProvider
from backend.app.services.synthesis import PassThroughSynthesizer


class FakeProvider:
    def market_series(self, spec, start, end):
        n = max((end-start).days, 45)
        rows=[]
        for i in range(n):
            d=start+timedelta(days=i)
            base={"gold":2000,"dxy":100,"sp500":5000,"eurusd":1.08,"gbpusd":1.27,"usdjpy":145}.get(spec.key,100)
            # deterministic alternating daily changes; gold opposes DXY
            sign=1 if i%2==0 else -1
            delta=(i*0.3 + sign*2) if spec.key=="gold" else (i*0.01 - sign*0.1)
            rows.append((d,base+delta))
        return rows
    def fred_series(self, series_id, start, end):
        n=max((end-start).days,45); rows=[]
        inverse = series_id == "DFII10"
        for i in range(n):
            d=start+timedelta(days=i); sign=1 if i%2==0 else -1
            value=4.0 + i*0.0005 + (sign*0.02 if inverse else -sign*0.01)
            rows.append((d,value))
        return rows


class FakeCatalysts:
    def search(self, *, asset, market_context):
        return CatalystSearchResult("ok", (CatalystCandidate("Fed repricing after data","Rates moved after a macro release.","macro_data",None,"Official source","https://example.com",0.8),), ({"title":"Official source","url":"https://example.com"},))


class FakeRegimeProvider(MacroRegimeHistoryProvider):
    def __init__(self): pass
    def snapshots(self, economy="usa"):
        return tuple(SimpleNamespace(as_of_date=date(2022,1,1)+timedelta(days=30*i), environment_label="Disinflationary Expansion" if i%2==0 else "Late Cycle", activity_label="Accelerating" if i%2==0 else "Slowing", inflation_impulse_label="Disinflationary", financial_impulse_label="Easing") for i in range(60))


def test_planner_recognises_real_yield_relationship():
    plan=ResearchPlanner().plan("Does gold move inversely to real yields historically?")
    assert plan.intent == ResearchIntent.HISTORICAL_RELATIONSHIP
    assert "gold" in plan.assets and "us10y_real" in plan.assets
    assert plan.supported_now is True


def test_concept_question_is_not_mistaken_for_live_move():
    plan=ResearchPlanner().plan("Why do 10 year yields go higher when inflation goes higher?")
    assert plan.intent == ResearchIntent.CONCEPT_EXPLANATION


def test_historical_relationship_returns_macrolens_regime_context():
    svc=HistoricalRelationshipService(provider=FakeProvider(),regimes=FakeRegimeProvider(),today_fn=lambda:date(2026,9,2))
    answer=svc.analyze("gold","us10y_real","5_years")
    assert answer.status == "ok"
    block=answer.blocks[0]
    assert block.type == "historical_relationship"
    assert block.data["regime_context"] is not None
    assert "current_environment" in block.data["regime_context"]


def test_current_move_uses_cross_market_evidence_and_catalyst():
    svc=CurrentMoveInvestigationService(provider=FakeProvider(),catalysts=FakeCatalysts(),today_fn=lambda:date(2026,9,2))
    answer=svc.investigate("gold")
    assert answer.status == "ok"
    assert answer.blocks[0].type == "market_evidence"
    assert answer.blocks[0].data["catalyst_status"] == "ok"
    assert "Fed repricing" in answer.answer


def test_ask_executes_historical_relationship_instead_of_failing_closed():
    relationships=HistoricalRelationshipService(provider=FakeProvider(),regimes=FakeRegimeProvider(),today_fn=lambda:date(2026,9,2))
    current=CurrentMoveInvestigationService(provider=FakeProvider(),catalysts=FakeCatalysts(),today_fn=lambda:date(2026,9,2))
    service=AskService(direct=DirectAnswerService(provider=FakeProvider(),today_fn=lambda:date(2026,9,2)), relationships=relationships,current_moves=current,synthesizer=PassThroughSynthesizer())
    payload=service.ask("Does gold move inversely to real yields historically?")
    assert payload["customer_answer"]["status"] == "ok"
    assert payload["research_plan"]["intent"] == "historical_relationship"


def test_ask_executes_supported_current_move():
    relationships=HistoricalRelationshipService(provider=FakeProvider(),regimes=FakeRegimeProvider(),today_fn=lambda:date(2026,9,2))
    current=CurrentMoveInvestigationService(provider=FakeProvider(),catalysts=FakeCatalysts(),today_fn=lambda:date(2026,9,2))
    service=AskService(direct=DirectAnswerService(provider=FakeProvider(),today_fn=lambda:date(2026,9,2)), relationships=relationships,current_moves=current,synthesizer=PassThroughSynthesizer())
    payload=service.ask("Why is gold rising today?")
    assert payload["customer_answer"]["status"] == "ok"
    assert payload["customer_answer"]["blocks"][0]["type"] == "market_evidence"
