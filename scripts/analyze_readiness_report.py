"""Generic offline summaries/metadata queues from an operator-supplied audit report.

No embedded production findings, observations, DB access, network or publication.
Output stays in a new operator-selected local directory, outside repository data.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from backend.app.catalog.operations import registry
from backend.app.catalog.readiness import adjustment_status, capabilities
from backend.app.catalog.research_metadata import review_queue
from backend.app.v2.definitions import SPECS


def analyze(report, rows):
    datasets = report["datasets"]
    ids = [d["id"] for d in datasets]
    if len(set(ids)) != len(ids) or len(ids) != report["scope"]["actual_public"]:
        raise ValueError("Report scope/identity mismatch")
    findings = {
        "source_audit_time": report["as_of"],
        "source_evidence_origin": report["evidence_origin"],
        "not_a_new_production_audit": True,
        "public_count": len(ids),
    }
    findings["provider_breakdown"] = []
    for provider in sorted({r["metadata"]["provider"] for r in datasets}):
        group = [r for r in datasets if r["metadata"]["provider"] == provider]
        gaps = [
            r for r in group if any(i["code"] == "history_gaps" for i in r["issues"])
        ]
        findings["provider_breakdown"].append(
            {
                "provider": provider,
                "datasets": len(group),
                "missing_descriptions": sum(
                    any(i["code"] == "description_missing" for i in r["issues"])
                    for r in group
                ),
                "gap_warnings": len(gaps),
                "gap_frequencies": dict(
                    Counter(r["metadata"]["frequency"] for r in gaps)
                ),
                "explicit_nulls_in_gap_flagged_series": sum(
                    r["historical_quality"]["null_value_count"] for r in gaps
                ),
                "absent_periods_in_gap_flagged_series": sum(
                    r["historical_quality"]["absent_periods"] or 0 for r in gaps
                ),
                "extreme_change_warnings": sum(
                    any(i["code"] == "large_changes_review" for i in r["issues"])
                    for r in group
                ),
            }
        )
    findings["markets"] = []
    for r in datasets:
        spec = SPECS.get(r["id"])
        applicability = adjustment_status(spec, r["metadata"]["adjustment"])
        if applicability != "not_applicable":
            continue
        missing = [k for k in r["metadata"]["missing_fields"] if k != "adjustment"]
        h = r["historical_quality"]
        findings["markets"].append(
            {
                "id": r["id"],
                "valid_observations": h["valid_value_count"],
                "longest_complete_run": h["longest_complete_run"],
                "invalid_count": h["invalid_count"],
                "duplicate_count": h["duplicate_period_count"],
                "original_missing_metadata": r["metadata"]["missing_fields"],
                "adjustment_status": applicability,
                "original_reasons": r["research_suitability"]["comparisons"]["reasons"],
                "reassessed_descriptive_capabilities": capabilities(
                    h,
                    r["metadata"]["frequency"],
                    not missing,
                    blocked=any(
                        i["code"] == "publication_evidence_invalid" for i in r["issues"]
                    ),
                ),
                "retained_limitations": r["known_limitations"],
            }
        )
    findings["refresh_exceptions"] = [
        {"id": r["id"], "refresh": r["refresh"], "freshness": r["freshness"]}
        for r in datasets
        if any(
            i["code"] in {"refresh_failure", "source_check_unverified"}
            for i in r["issues"]
        )
    ]
    findings["lag_review"] = [
        {
            "id": r["id"],
            "frequency": r["metadata"]["frequency"],
            "last_reference_start": r["historical_quality"]["last_valid_observation"],
        }
        for r in datasets
        if any(i["code"] == "observation_lag_review" for i in r["issues"])
    ]
    return findings, review_queue(report, rows)


def render(findings):
    lines = [
        "# Supplied audit report analysis",
        "",
        f"Source time: {findings['source_audit_time']}; operator-declared origin: {findings['source_evidence_origin']}; public IDs: {findings['public_count']}.",
        f"Input SHA-256: `{findings.get('input_sha256', 'not supplied')}`.",
        "",
        "This analyzes stored summaries only. It is not a new production audit or independent source verification. Warning counts are not counts of proven data errors.",
        "",
        "| Provider | Public | Missing descriptions | Gap flags | Explicit nulls in flagged series | Absent periods in flagged series | Extreme flags |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for p in findings["provider_breakdown"]:
        lines.append(
            f"| {p['provider']} | {p['datasets']} | {p['missing_descriptions']} | {p['gap_warnings']} | {p['explicit_nulls_in_gap_flagged_series']} | {p['absent_periods_in_gap_flagged_series']} | {p['extreme_change_warnings']} |"
        )
    lines += [
        "",
        "Review missing economic definitions by provider/table family using metadata-review-queue.json. Explicit nulls, absent rows, market-calendar exclusions, boundary coverage and genuine internal gaps need separate interpretation. Extreme changes can be real events or methodological effects; no observations were repaired or discarded.",
        "",
        "## Refresh exceptions",
        "",
        "| Dataset | Stored successful check | Failures | Interpretation at supplied snapshot |",
        "|---|---|---:|---|",
    ]
    for row in findings["refresh_exceptions"]:
        f = row["refresh"]
        interpretation = (
            "Recorded failure; root cause not established"
            if f["failure_count"] or f["error_present"]
            else "Incomplete success telemetry; no failure established"
        )
        lines.append(
            f"| {row['id']} | {f['last_successful_source_check']} | {f['failure_count']} | {interpretation} |"
        )
    lines += [
        "",
        "See findings.json for the separate history, integrity and metadata gate reassessment. No pairwise, causal, vintage, release-calendar or current-worker certification is implied. No capability grants AI or Discovery permission.",
        "",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.audit.stat().st_size > 16 * 1024 * 1024:
        parser.error("Report size exceeds bound")
    raw = args.audit.read_bytes()
    findings, queue = analyze(json.loads(raw.decode("utf-8-sig")), registry())
    findings["input_sha256"] = hashlib.sha256(raw).hexdigest()
    args.output.mkdir(parents=True, exist_ok=False)
    for name, payload in (
        ("findings.json", findings),
        ("metadata-review-queue.json", queue),
    ):
        (args.output / name).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    (args.output / "findings.md").write_text(render(findings), encoding="utf-8")
    print(
        f"Analyzed {findings['public_count']} supplied reports; queued {len(queue)} metadata reviews. No database accessed."
    )


if __name__ == "__main__":
    main()
