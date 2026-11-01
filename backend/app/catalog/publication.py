"""Independent future publication gates. Not wired into the deployed reader yet.

Nothing here can approve rights, populate ingestion jobs, change legacy CHECK
constraints or publish a planning entry. Explicit reviewed registration, rights,
dataset completeness, cursor and artifact agreement are all required.
"""

import re
from dataclasses import dataclass

SCOPES = frozenset({"public_display", "ai", "discovery"})


@dataclass(frozen=True)
class Review:
    dataset_id: str
    scope: str
    rights_state: str = "unreviewed"
    approved: bool = False
    evidence: str = ""
    reviewed_definition_hash: str = ""


@dataclass(frozen=True)
class Completeness:
    dataset_id: str
    batch_id: str
    source_hash: str
    definition_hash: str
    cursor: str | None = None
    state: str = "pending"
    quality_passed: bool = False


def permits(
    *,
    dataset_id,
    scope,
    registration,
    review,
    completeness,
    source_hash,
    definition_hash,
):
    """Fail closed; a grant for one scope never grants another scope."""
    hashes = (source_hash, definition_hash)
    if (
        not isinstance(scope, str)
        or scope not in SCOPES
        or registration is not True
        or not isinstance(review, Review)
        or not isinstance(completeness, Completeness)
        or any(
            not isinstance(h, str) or not re.fullmatch(r"[0-9a-f]{64}", h)
            for h in hashes
        )
    ):
        return False
    if not isinstance(review.evidence, str) or not isinstance(
        completeness.batch_id, str
    ):
        return False
    return bool(
        review.dataset_id == completeness.dataset_id == dataset_id
        and review.scope == scope
        and review.rights_state == "permitted"
        and review.approved is True
        and review.evidence.strip()
        and review.reviewed_definition_hash == definition_hash
        and completeness.definition_hash == definition_hash
        and completeness.source_hash == source_hash
        and completeness.batch_id
        and completeness.cursor is None
        and completeness.state == "complete"
        and completeness.quality_passed is True
    )
