from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class AnswerBlock:
    type: str
    title: str
    data: dict[str, Any]


@dataclass(frozen=True)
class ExperienceLink:
    title: str
    description: str
    route: str
    action_label: str


@dataclass(frozen=True)
class CustomerAnswer:
    status: str
    answer: str
    confidence: str | None = None
    blocks: tuple[AnswerBlock, ...] = ()
    limitations: tuple[str, ...] = ()
    sources: tuple[dict[str, str], ...] = ()
    follow_up_questions: tuple[str, ...] = ()
    explore: tuple[ExperienceLink, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
