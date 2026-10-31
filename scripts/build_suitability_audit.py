"""Rebuild audit artifacts from reviewed notes and metadata, never ingest observations.

Only writes research/audits/2026-10-30-dataset-suitability. No network, Store,
application lifespan, permission writer or data-provider execution.
"""

import json
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.v2.definitions import SPECS

AUDIT = ROOT / "research/audits/2026-10-30-dataset-suitability"


def render():
    def read(name):
        return json.loads((AUDIT / name).read_text(encoding="utf-8"))

    assessments, evidence = read("assessments.json"), read("sources.json")
    fred = {r["id"]: r for r in read("metadata_verification.json")["public_fred"]}
    yahoo = {r["symbol"]: r for r in read("yahoo_metadata_check.json")["series"]}
    manifest = json.loads((ROOT / "catalog/datasets.json").read_text(encoding="utf-8"))
    entries = {e["id"]: e for e in manifest["datasets"]}
    notes = {r["id"]: r for r in assessments["datasets"]}
    assert len(notes) == len(SPECS) == 30 and set(notes) == set(SPECS)
    rows = []
    for key, spec in SPECS.items():
        note = notes[key]
        assert note["classification"] in {
            "KEEP",
            "KEEP + SUPPLEMENT",
            "REPLACE",
            "FLAG",
        }
        assert all(ref in evidence["sources"] for ref in note["evidence"])
        assert note["revision"] in assessments["revision_profiles"]
        profile = evidence["rights_profiles"][note["license"]]
        if key in fred:
            checked = fred[key]
            assert checked["status"] == "verified metadata"
            start, end = checked["Date Range"].split(" to ")
            history = {
                "source_first_listed": start,
                "source_last_listed": end,
                "status": "verified current FRED metadata range, not gap-free coverage",
                "evidence_url": checked["metadata_url"],
            }
            transport = "T_FRED"
        else:
            checked = yahoo[spec.provider_id]
            history = {
                "source_first_listed": checked["first_trade_utc"][:10],
                "source_last_listed": None,
                "status": "secondary vendor firstTradeDate only; contract/backcast continuity and actual endpoint span unverified",
                "evidence_url": checked["url"],
            }
            transport = "T_YAHOO"
        rows.append(
            {
                "id": key,
                "name": spec.name,
                "current_provider": spec.provider,
                "current_selector": spec.provider_id,
                "current_source_url": spec.source_url,
                "definition": spec.definition,
                "frequency": spec.frequency,
                "units": spec.units,
                "adjustment": spec.seasonal_adjustment,
                "original_source": note["producer"],
                "original_identifier": note["original_identifier"],
                "original_definition_url": note["original_url"],
                "history": history,
                "application_history_floor": "1990-01-01",
                "revision_methodology": assessments["revision_profiles"][
                    note["revision"]
                ],
                "suitable_for": note["suitable"],
                "unsuitable_for": note["unsuitable"],
                "continuity_and_presentation_risks": note["continuity"],
                "alternatives_or_complements": note["alternatives"],
                "classification": note["classification"],
                "underlying_rights_code": note["license"],
                "underlying_rights_assessment": profile["underlying_status"],
                "transport_rights_code": transport,
                "publication_approval_changed": False,
                "evidence": note["evidence"],
            }
        )
    public = {r["id"]: r for r in rows}
    screen = []
    for key in sorted(entries):
        e = entries[key]
        provider = e["source"]["provider"]
        risks = []
        if e["kind"] == "selection":
            risks.append(
                "Resolve panel/components/flows into documented atomic selections; do not ingest an invented aggregate"
            )
        if provider == "fred":
            risks.append(
                "Review source-specific rights and FRED transport scope; prefer cleared original-producer routes where appropriate"
            )
        if provider in {"yahoo", "lme", "world_bank", "mpa", "worldsteel"}:
            risks.append(
                "Underlying owner/benchmark and onward distribution require separate evidence"
            )
        if provider in {"oecd", "eurostat", "ons", "japan_dashboard", "boj"}:
            risks.append(
                "Validate all dimensions, adjustment, native/fiscal periods and unit multipliers; retain revisions"
            )
        if provider == "nbs_china":
            risks.append(
                "Distinguish Jan-Feb combined data, YTD/cumulative values, single-month rates, nominal/real and published growth concepts"
            )
        if e["category"].lower() in {
            "construction",
            "commodities",
            "energy",
            "materials",
        } or provider in {
            "eia",
            "jodi",
            "usgs",
            "comtrade",
            "hmrc",
            "desnz",
            "modot",
            "uk_building_materials",
        }:
            risks.append(
                "Distinguish price/stock/flow, gross/net trade, material grade/geography, physical units and conversion factors"
            )
        if "unverified" in (e["units"] + " " + e["seasonal_adjustment"]).lower():
            risks.append("Units or adjustment are explicitly unverified")
        screen.append(
            {
                "id": key,
                "planning_refs": e["planning_refs"],
                "provider": provider,
                "selector": e["source"]["selector"],
                "kind": e["kind"],
                "existing_public_review": public[key]["classification"]
                if key in public
                else None,
                "status": "audited concept; permission unchanged"
                if key in public
                else "pending source-specific suitability review",
                "prior_rights_state": e["rights"]["status"],
                "required_gates": [
                    "concept/question fit",
                    "original source and exact selection",
                    "units/adjustment/calendar",
                    "coverage/gaps/revisions",
                    "underlying and transport rights",
                    "publication/AI/Discovery separately",
                    "bounded resource/restore validation",
                ],
                "risk_prompts": risks,
            }
        )
    assert (
        len(screen) == 309
        and sum(r["existing_public_review"] is not None for r in screen) == 30
    )
    counts = dict(sorted(Counter(r["classification"] for r in rows).items()))
    matrix = {
        "checked_at": "2026-10-30",
        "base": "1bf62919d1395149ffad8b39c0664adfee4d956d",
        "scope": assessments["classification_scope"],
        "counts": counts,
        "limitations": "No production DB read or full numerical history reconciliation. Source range metadata and documented breaks were checked; no gap-free or real-time-vintage guarantee.",
        "datasets": rows,
    }
    planned = {
        "scope": "All 309 existing manifest entries screened using prior planning evidence, not 279 new source validations or publication grants.",
        "counts": {
            "entries": len(screen),
            "public_audited": 30,
            "pending_source_specific_review": 279,
            "selection_panels": sum(e["kind"] == "selection" for e in entries.values()),
        },
        "entries": screen,
    }
    identity = {
        key: {
            field: asdict(spec)[field]
            for field in (
                "id",
                "provider",
                "provider_id",
                "frequency",
                "units",
                "seasonal_adjustment",
                "allowed_transformations",
                "representation",
            )
        }
        for key, spec in SPECS.items()
    }
    text = [
        "# Public dataset suitability matrix",
        "",
        "Checked 30 October 2026. All 30 current public IDs; no source/permission changes.",
        "",
        "Classification concerns research use, not permission. REPLACE means a new source/role under a new ID while preserving the legacy ID and saved references.",
        "",
        "History is source metadata, not application coverage: the legacy app requests history from 1990, and a source can begin later. First/last dates do not establish continuity. Yahoo dates are vendor metadata, not validated contract histories.",
        "",
        "Full machine-readable fields: [PUBLIC_DATASET_MATRIX.json](PUBLIC_DATASET_MATRIX.json). Rights codes and evidence: [sources.json](sources.json). Current FRED-route restrictions are evaluated separately from original-government-data rights; all flags stay unchanged.",
        "",
        "| ID / selected identifier | Original producer; frequency / units / adjustment | Source history checked | Classification | Suitable / unsuitable research | Main continuity risk; better or complementary data | Rights code |",
        "|---|---|---|---|---|---|---|",
    ]

    def cell(value):
        return str(value).replace("|", "/").replace("\n", " ")

    for r in rows:
        h = r["history"]
        vals = [
            f"`{r['id']}` / `{r['current_selector']}`",
            f"{r['original_source']}; {r['frequency']}; {r['units']}; {r['adjustment'] or 'No SA convention / market price'}",
            f"{h['source_first_listed']} to {h['source_last_listed'] or 'unverified'}",
            r["classification"],
            f"Use: {r['suitable_for']} Avoid: {r['unsuitable_for']}",
            f"{r['continuity_and_presentation_risks']} Compare: {r['alternatives_or_complements']}",
            f"{r['underlying_rights_code']} + {r['transport_rights_code']}",
        ]
        text.append("| " + " | ".join(cell(v) for v in vals) + " |")
    text += ["", "## Revision methodology and exact source evidence", ""]
    for r in rows:
        text += [
            f"### `{r['id']}`",
            "",
            f"Original selection: {r['original_identifier']}. [Producer]({r['original_definition_url']}); [current selected source]({r['current_source_url']}); [history metadata]({r['history']['evidence_url']}).",
            "",
            r["revision_methodology"],
            "",
            "Evidence: "
            + ", ".join(
                f"[{ref}]({evidence['sources'][ref]['url']})" for ref in r["evidence"]
            )
            + ".",
            "",
        ]
    return {
        "PUBLIC_DATASET_MATRIX.json": json.dumps(matrix, indent=2, ensure_ascii=False)
        + "\n",
        "PUBLIC_DATASET_MATRIX.md": "\n".join(text) + "\n",
        "EXPANSION_QUALITY_SCREEN.json": json.dumps(
            planned, indent=2, ensure_ascii=False
        )
        + "\n",
        "public_identity_baseline.json": json.dumps(
            identity, indent=2, ensure_ascii=False
        )
        + "\n",
    }


def main():
    outputs = render()
    for name, text in outputs.items():
        if "--check" in sys.argv:
            assert (AUDIT / name).read_text(encoding="utf-8") == text, name
        else:
            (AUDIT / name).write_text(text, encoding="utf-8")
    print(
        json.dumps(
            {
                "public_datasets": 30,
                "manifest_screen": 309,
                "outputs": len(outputs),
                "check_only": "--check" in sys.argv,
            }
        )
    )


if __name__ == "__main__":
    main()
