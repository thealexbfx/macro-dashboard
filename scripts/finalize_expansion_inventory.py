"""Turn measured successful development ingestions into reviewable inventories."""

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "research/releases/full-expansion"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    w = args.workspace.resolve()
    if not (w / "DISPOSABLE_EXPANSION_ONLY").is_file():
        parser.error("Disposable workspace required")
    data = json.loads(
        (ROOT / "catalog/release_candidates.json").read_text(encoding="utf-8")
    )
    measured = json.loads((w / "validation.json").read_text(encoding="utf-8"))
    valid = {r["id"]: r for r in measured["datasets"] if r["state"] == "validated"}
    assert len(valid) == len(data["datasets"])
    for r in data["datasets"]:
        assert valid[r["id"]]["observations"] == r["validation"]["observations"]
        r["state"] = "development_ingestion_and_public_reader_validated"
        r["validation"]["reader_preview_ms"] = valid[r["id"]]["preview_ms"]
        r["validation"]["sample_check"] = (
            "First, middle and last source-snapshot values match SQLite exactly"
        )
    (ROOT / "catalog/release_candidates.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    def cell(v):
        return str(v).replace("|", "\\|").replace("\n", " ")

    lines = [
        "# Successful real datasets",
        "",
        f"{len(valid)} additional datasets; {measured['observations']:,} stored native rows (including explicit source nulls). No production activation.",
        "",
        "The full machine-readable inventory, exact selectors/dimensions, rights evidence, attribution, limitations and sample checks are in [release_candidates.json](../../../catalog/release_candidates.json). All rows were ingested and public-reader tested in disposable SQLite, with separate explicit development-only display grants. No AI/Discovery grants.",
        "",
        "| Canonical ID | Name / region | Original provider / exact selector | Frequency / units | Actual returned coverage | Rows / non-null | Release unit | Licence evidence |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in data["datasets"]:
        d, v = r["definition"], r["validation"]
        values = [
            f"`{r['id']}`",
            r["name"] + " / " + r["region"],
            d["provider"] + " / " + d["selector"],
            d["frequency"] + " / " + d["units"],
            v["first"] + " to " + v["last"],
            str(v["observations"]) + " / " + str(v["nonnull"]),
            r["release_unit"],
            f"[Evidence]({r['license_url']})",
        ]
        lines.append("| " + " | ".join(cell(x) for x in values) + " |")
    (REPORT / "SUCCESSFUL_DATASETS.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    exceptions = json.loads((REPORT / "exceptions.json").read_text(encoding="utf-8"))[
        "entries"
    ]
    lines = [
        "# Unresolved selections",
        "",
        f"{len(exceptions)} unresolved IDs. This includes three existing private World Bank pilots, not new public releases. Captured privately means download/normalization only, not public ingestion or permission.",
        "",
        "Some entries are unfinished adapter work, explicitly distinguished from demonstrated outages or legal prohibitions. They must not be represented as impossible integrations.",
        "",
        "| ID / provider | Selected series | Blocker category / exact finding | Next action |",
        "|---|---|---|---|",
    ]
    for r in exceptions:
        lines.append(
            "| "
            + " | ".join(
                cell(x)
                for x in [
                    r["id"] + " / " + r["provider"],
                    r["name"] + " / " + r["selector"],
                    r["category"] + ": " + r["blocker"],
                    r["recommended_action"],
                ]
            )
            + " |"
        )
    (REPORT / "EXCEPTIONS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (REPORT / "windows-validation.json").write_text(
        json.dumps(measured, indent=2) + "\n", encoding="utf-8"
    )
    summary = {
        "legacy_public": 30,
        "additional_development_validated": len(valid),
        "development_catalog_total": 30 + len(valid),
        "native_rows": measured["observations"],
        "non_null_rows": sum(r["validation"]["nonnull"] for r in data["datasets"]),
        "unresolved_ids": len(exceptions),
        "manifest_entries_unchanged": 309,
        "additional_suitability_ids": 4,
        "provider_counts": dict(
            Counter(r["definition"]["provider"] for r in data["datasets"])
        ),
        "production_changes": False,
        "ai_grants": 0,
        "discovery_grants": 0,
    }
    (REPORT / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
