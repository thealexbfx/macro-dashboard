"""Compact provenance for existing comparisons; no IO, permissions or frozen arrays."""

import hashlib
import json
from datetime import UTC, datetime

METHOD_VERSION = "macrolens-comparison-1"


def fingerprint(value):
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode()
    ).hexdigest()


def input_receipt(metadata, observations):
    definition = {
        k: metadata.get(k)
        for k in (
            "id",
            "provider",
            "provider_id",
            "source",
            "units",
            "frequency",
            "seasonal_adjustment",
            "representation",
            "native_calendar",
        )
    }
    provenance = metadata.get("stored_provenance") or {}
    return {
        "dataset_id": metadata["id"],
        "provider": metadata.get("provider"),
        "source_identifier": metadata.get("provider_id"),
        "source_url": metadata.get("source_url"),
        "definition_identifier": provenance.get("definition_hash")
        or fingerprint(definition),
        "definition_identifier_kind": "native_definition_hash"
        if provenance.get("definition_hash")
        else "registered_metadata_fingerprint",
        "units": metadata["units"],
        "frequency": metadata["frequency"],
        "seasonal_adjustment": metadata.get("seasonal_adjustment"),
        "retrieved_at": metadata.get("retrieved_at"),
        "source_checked_at": (metadata.get("release_metadata") or {}).get(
            "last_source_success_at"
        )
        or provenance.get("source_checked_at"),
        "generation_references": provenance.get("generation_references", []),
        "generation_reference_count": provenance.get("generation_reference_count", 0),
        "input_fingerprint": fingerprint(observations),
        "input_count": len(observations),
        "input_start": observations[0]["date"] if observations else None,
        "input_end": observations[-1]["date"] if observations else None,
        "input_scope": "Validated fetched inputs supplied to calculation, including historical lookback; may include unused earlier history. Not a publication-time vintage.",
    }


def calculation_receipt(request, result, inputs):
    parameters = request.model_dump(mode="json")
    summaries = [
        {k: v for k, v in row.items() if k != "rolling"} for row in result["statistics"]
    ]
    return {
        "schema_version": 1,
        "method_version": METHOD_VERSION,
        "calculated_at": datetime.now(UTC).isoformat(),
        "parameters": parameters,
        "parameter_fingerprint": fingerprint(parameters),
        "datasets": inputs,
        "result_fingerprint": fingerprint(
            {
                "series": result["series"],
                "statistics": result["statistics"],
                "alignment": result["alignment"],
            }
        ),
        "effective_ranges": [
            {
                "dataset_id": s["id"],
                "start": next(
                    (o["date"] for o in s["observations"] if o["value"] is not None),
                    None,
                ),
                "end": next(
                    (
                        o["date"]
                        for o in reversed(s["observations"])
                        if o["value"] is not None
                    ),
                    None,
                ),
                "units": s["units"],
                "transformation": s["transformation"],
            }
            for s in result["series"]
        ],
        "statistics": summaries,
        "limitations": result["warnings"],
        "exact_replay": {
            "available": False,
            "reason": "Receipt preserves parameters, fingerprints and compact results, not frozen observations. Generation references do not guarantee a historical read API.",
        },
    }
