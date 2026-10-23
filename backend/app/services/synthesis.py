from __future__ import annotations
import json, os
from dataclasses import replace
from typing import Protocol

from backend.app.schemas.customer_answer import CustomerAnswer


class AnswerSynthesizer(Protocol):
    def synthesize(self, *, question: str, answer: CustomerAnswer) -> CustomerAnswer: ...


class PassThroughSynthesizer:
    def synthesize(self, *, question: str, answer: CustomerAnswer) -> CustomerAnswer:
        return answer


class OpenAIEvidenceSynthesizer:
    """Optional wording layer. It may rewrite only the conclusion using supplied evidence.

    It does not fetch data, add facts, alter blocks, create sources, or change confidence.
    The deterministic CustomerAnswer remains the source of truth.
    """
    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or os.getenv("MACROLENS_SYNTHESIS_MODEL", "gpt-5.6-luna")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

    def synthesize(self, *, question: str, answer: CustomerAnswer) -> CustomerAnswer:
        if not self.api_key or answer.status != "ok":
            return answer
        from openai import OpenAI
        evidence = {
            "question": question,
            "deterministic_answer": answer.answer,
            "confidence": answer.confidence,
            "blocks": [{"type": b.type, "title": b.title, "data": b.data} for b in answer.blocks],
            "limitations": list(answer.limitations),
        }
        prompt = (
            "Write the primary MacroLens answer in no more than 120 words. Use ONLY the supplied structured evidence. "
            "Do not add numbers, events, causes, certainty, or facts not present. Preserve uncertainty and contradictions. "
            "Do not mention being an AI. Return JSON only as {\"answer\": \"...\"}.\n\n" + json.dumps(evidence, default=str)
        )
        try:
            response = OpenAI(api_key=self.api_key).responses.create(model=self.model, input=prompt)
            payload = json.loads((getattr(response, "output_text", "") or "").strip())
            text = str(payload.get("answer", "")).strip()
            if not text:
                return answer
            return replace(answer, answer=text, metadata={**answer.metadata, "synthesis": "openai_evidence_only"})
        except Exception:
            return replace(answer, metadata={**answer.metadata, "synthesis": "deterministic_fallback"})


def default_synthesizer() -> AnswerSynthesizer:
    enabled = os.getenv("MACROLENS_ENABLE_AI_SYNTHESIS", "false").strip().lower() in {"1", "true", "yes", "on"}
    return OpenAIEvidenceSynthesizer() if enabled else PassThroughSynthesizer()
