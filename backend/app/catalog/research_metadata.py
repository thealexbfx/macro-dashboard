"""Reviewed descriptive overlay on canonical rows; never a dataset/rights registry.

Consumers supply a row from operations.registry(). No observations or network IO.
Unknown publication/revision conventions stay unknown until a reviewed PR supplies
evidence. The default review file is empty, not 158 generated descriptions.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

REVIEWS = Path(__file__).resolve().parents[3] / "catalog/research_metadata.json"
FIELDS = {
    "id",
    "identity_sha256",
    "definition",
    "observation_convention",
    "publication_behavior",
    "revision_behavior",
    "references",
    "reviewed_at",
    "reviewer",
}


def identity(row):
    definition = row.get("native_definition") or {}
    payload = {
        k: row.get(k)
        for k in (
            "id",
            "provider",
            "source_identifier",
            "region",
            "units",
            "frequency",
            "adjustment",
            "definition_hash",
        )
    }
    payload["unit_multiplier"] = definition.get("unit_multiplier", 0)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=True).encode()
    ).hexdigest()


def load_reviews(path=REVIEWS):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if (
        data.get("schema_version") != 1
        or not isinstance(data.get("reviews"), list)
        or len(data["reviews"]) > 1000
    ):
        raise ValueError("Invalid descriptive reviews")
    result = {}
    for review in data["reviews"]:
        if set(review) != FIELDS or review["id"] in result:
            raise ValueError("Unknown fields/permissions or duplicate review")
        if any(
            not isinstance(review[k], str)
            or not review[k].strip()
            or len(review[k]) > 8000
            for k in (
                "id",
                "identity_sha256",
                "definition",
                "observation_convention",
                "reviewed_at",
                "reviewer",
            )
        ):
            raise ValueError("Incomplete review")
        if datetime.fromisoformat(review["reviewed_at"]).tzinfo is None:
            raise ValueError("Review timestamp requires timezone")
        for field in ("publication_behavior", "revision_behavior"):
            if review[field] is not None and (
                not isinstance(review[field], str)
                or not review[field].strip()
                or len(review[field]) > 8000
            ):
                raise ValueError("Unknown behavior must be null")
        references = review["references"]
        if not isinstance(references, list) or not 1 <= len(references) <= 20:
            raise ValueError("Reviewed source references required")
        for reference in references:
            parsed = urlsplit(reference)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
                or len(reference) > 4096
            ):
                raise ValueError("Invalid reference")
        result[review["id"]] = review
    return result


def resolve(row, reviews=None):
    """Portable metadata contract for Explorer/Investigate and future research tools.

    This does not check or grant public/AI/Discovery access. Callers must first use
    their existing permission boundary. Definition-bound overlay changes no values.
    """
    reviews = load_reviews() if reviews is None else reviews
    review = reviews.get(row["id"])
    if review and review["identity_sha256"] != identity(row):
        raise ValueError("Descriptive review does not match canonical definition")
    native = row.get("native_definition") or {}
    return {
        "id": row["id"],
        "identity_sha256": identity(row),
        "definition": review["definition"]
        if review
        else row.get("description") or None,
        "provider": row.get("provider"),
        "source_identifier": row.get("source_identifier"),
        "geography": row.get("region"),
        "frequency": row.get("frequency"),
        "units": row.get("units"),
        "unit_multiplier": native.get("unit_multiplier", 0),
        "seasonal_adjustment": row.get("adjustment"),
        "native_reference_calendar": {
            k: v
            for k, v in native.get("calendar", {}).items()
            if k not in {"releases", "holidays", "evidence"}
        },
        "observation_convention": review["observation_convention"] if review else None,
        "publication_behavior": review["publication_behavior"] if review else None,
        "revision_behavior": review["revision_behavior"] if review else None,
        "status": "reviewed_overlay"
        if review
        else "existing_definition"
        if row.get("description")
        else "pending_definition_review",
        "provenance": review
        if review
        else {
            "source_owner_evidence": row.get("source_owner_evidence"),
            "source_evidence": row.get("source_evidence", []),
        },
        "grants_permissions": False,
    }


def review_queue(report, rows):
    """Prioritize actual report gaps; copy canonical facts, never draft invented prose."""
    by_id = {row["id"]: row for row in rows}
    queue = []
    for dataset in report["datasets"]:
        if not any(i["code"] == "description_missing" for i in dataset["issues"]):
            continue
        row = by_id[dataset["id"]]
        # Proven anomalies/gaps need interpretation first; this is review priority,
        # not an automatic assertion of bad data or a provider-specific exemption.
        codes = {i["code"] for i in dataset["issues"]}
        priority = 1 if codes & {"observation_lag_review", "history_gaps"} else 2
        queue.append(
            {
                "priority": priority,
                "id": row["id"],
                "provider": row["provider"],
                "name": row["name"],
                "canonical_facts": resolve(row, reviews={}),
                "required_review": [
                    "Verify economic definition against selected provider series and source owner",
                    "Verify date labels and publication/revision behavior; leave unverified facts null",
                    "Add explicit reviewed_at/reviewer/references and matching identity_sha256 in a review-only PR",
                ],
                "source_audit_time": report["as_of"],
            }
        )
    return sorted(queue, key=lambda row: (row["priority"], row["provider"], row["id"]))
