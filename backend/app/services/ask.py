from __future__ import annotations

from backend.app.research.planner import ResearchIntent, ResearchPlanner
from backend.app.schemas.customer_answer import AnswerBlock, CustomerAnswer, ExperienceLink
from backend.app.services.current_moves import CurrentMoveInvestigationService
from backend.app.services.direct_answers import DirectAnswerService
from backend.app.services.historical_relationships import HistoricalRelationshipService
from backend.app.services.macro import MacroService
from backend.app.services.synthesis import AnswerSynthesizer, default_synthesizer


class AskService:
    def __init__(self, planner: ResearchPlanner | None = None, direct: DirectAnswerService | None = None,
                 macro: MacroService | None = None, relationships: HistoricalRelationshipService | None = None,
                 current_moves: CurrentMoveInvestigationService | None = None, synthesizer: AnswerSynthesizer | None = None) -> None:
        self.planner = planner or ResearchPlanner()
        self.direct = direct or DirectAnswerService()
        self.macro = macro or MacroService()
        self.relationships = relationships or HistoricalRelationshipService()
        self.current_moves = current_moves or CurrentMoveInvestigationService()
        self.synthesizer = synthesizer or default_synthesizer()

    def ask(self, question: str) -> dict:
        plan = self.planner.plan(question)
        try:
            if plan.intent == ResearchIntent.MARKET_LOOKUP and plan.assets:
                answer = self.direct.market_lookup(plan.assets[0])
            elif plan.intent == ResearchIntent.MARKET_CALCULATION and plan.assets:
                answer = self.direct.market_calculation(plan.assets[0], plan.timeframe)
            elif plan.intent == ResearchIntent.FACTUAL_LOOKUP and plan.economies and plan.indicators:
                answer = self.direct.economic_lookup(plan.economies[0], plan.indicators[0])
            elif plan.intent == ResearchIntent.HISTORICAL_RELATIONSHIP and len(plan.assets) >= 2:
                answer = self.relationships.analyze(plan.assets[0], plan.assets[1], plan.timeframe, economy=plan.economies[0] if plan.economies else "usa")
            elif plan.intent == ResearchIntent.CURRENT_MARKET_MOVE and plan.assets and plan.supported_now:
                answer = self.current_moves.investigate(plan.assets[0])
            elif plan.intent == ResearchIntent.MACRO_ANALYSIS and plan.economies:
                env = self.macro.get_current_environment(plan.economies[0])
                payload = env.to_dict()
                answer = CustomerAnswer(
                    status="ok",
                    answer=payload["environment_summary"] or f"MacroLens currently classifies {payload['economy']} as {payload['environment_label']}.",
                    confidence=payload.get("confidence_label"),
                    blocks=(AnswerBlock("macro_environment", "MacroLens macro context", payload),),
                    limitations=("This answer is grounded in the current MacroLens environment model. Question-specific synthesis is allowed only after the evidence is assembled.",),
                    follow_up_questions=("Which MacroLens pillar has changed most?", "What would change this macro view?"),
                    explore=(ExperienceLink("Explore the full macro picture", "See Growth, Inflation, Labour, Liquidity and Policy together.", f"/macro/{plan.economies[0]}", "Explore macro"),),
                )
            else:
                answer = CustomerAnswer(
                    status="planned_not_implemented" if plan.intent != ResearchIntent.OUT_OF_SCOPE else "unsupported",
                    answer="MacroLens understands the type of research needed, but this production capability is not wired yet." if plan.intent != ResearchIntent.OUT_OF_SCOPE else "MacroLens does not currently support this question reliably.",
                    limitations=("MacroLens will not manufacture an answer when the required evidence path is not production-ready.",),
                )
        except Exception as exc:
            answer = CustomerAnswer(
                status="data_unavailable",
                answer="MacroLens understood the question, but the required data could not be retrieved reliably.",
                limitations=(str(exc),),
            )
        answer = self.synthesizer.synthesize(question=question, answer=answer)
        return {"question": question, "research_plan": plan.to_dict(), "customer_answer": answer.to_dict()}
