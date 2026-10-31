"""Build reviewed candidate/exception inventories from actual development captures.

No database/network access, permission activation or observation files in git.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from backend.app.v2.definitions import SPECS

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "research/releases/full-expansion"

RIGHTS = {
    "eurostat": (
        "https://ec.europa.eu/eurostat/help/copyright-notice",
        "EU statistical data reuse; selected EU/euro-area macro tables, not excluded third-country or restricted detailed trade data",
        "Eurostat",
    ),
    "ons": (
        "https://www.ons.gov.uk/help/terms-conditions",
        "OGL v3; original ONS statistical tables, no licensed images or other excluded material",
        "Office for National Statistics, Crown copyright, OGL v3",
    ),
    "desnz": (
        "https://www.gov.uk/government/statistics/energy-trends-september-2026",
        "OGL v3; original Energy Trends statistics; native table units and notes retained",
        "DESNZ, Energy Trends September 2026, Crown copyright, OGL v3",
    ),
    "uk_building_materials": (
        "https://www.gov.uk/help/reuse-govuk-content",
        "OGL v3 applies to selected DBT-authored columns only; BCIS and MPA columns excluded",
        "Department for Business and Trade, Crown copyright, OGL v3",
    ),
    "eia": (
        "https://www.eia.gov/about/copyrights_reuse.php",
        "EIA-authored statistics in these identified historical files; no separately protected third-party material selected",
        "US Energy Information Administration",
    ),
    "usgs": (
        "https://www.usgs.gov/faqs/are-usgs-reportspublications-copyrighted",
        "USGS-authored domestic Mineral Industry Surveys tables; estimated totals and units retained",
        "US Geological Survey, Mineral Industry Surveys",
    ),
    "bls": (
        "https://www.bls.gov/bls/linksite.htm",
        "Original federal BLS statistical observations, public domain; no proprietary third-party index selected",
        "US Bureau of Labor Statistics",
    ),
    "bea": (
        "https://www.bea.gov/help/faq/147",
        "Original BEA NIPA tables, public domain; no third-party content selected",
        "US Bureau of Economic Analysis",
    ),
    "census": (
        "https://www.copyright.gov/title17/92chap1.html#105",
        "Original Census C30 statistical tables are federal works; not a licence inference from mere API availability",
        "US Census Bureau, Value of Construction Put in Place",
    ),
    "federal_reserve": (
        "https://www.federalreserve.gov/disclaimer.htm",
        "Original Board/Treasury statistics; H15 effective federal funds rate requires separate NY Fed reference-rate notice review",
        "Board of Governors of the Federal Reserve System",
    ),
    "ecb": (
        "https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html",
        "Selected ESCB-produced rates, reference FX and monetary statistics; source metadata unchanged, third-party data excluded",
        "ECB statistics",
    ),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    workspace = args.workspace.resolve()
    if not (workspace / "DISPOSABLE_EXPANSION_ONLY").is_file():
        parser.error("Marked development capture directory required")
    captures = json.loads(
        (workspace / "source-results.json").read_text(encoding="utf-8")
    )
    entries = {
        e["id"]: e
        for e in json.loads(
            (ROOT / "catalog/datasets.json").read_text(encoding="utf-8")
        )["datasets"]
    }
    overrides = json.loads(
        (ROOT / "catalog/source_overrides.json").read_text(encoding="utf-8")
    )["datasets"]
    entries.update({e["id"]: e for e in overrides})
    successes, exceptions = [], []
    for key, entry in sorted(entries.items()):
        if key in SPECS:
            continue
        result = captures.get(key, {})
        provider = result.get("definition", {}).get(
            "provider", entry["source"]["provider"]
        )
        if (
            result.get("state") == "captured"
            and provider in RIGHTS
            and key != "fred_f007c60ecacde1bf5fb2"
        ):
            license_url, basis, source = RIGHTS[provider]
            url = result.get("source_url")
            if not url:
                snapshot = json.loads(
                    Path(result["snapshot_path"]).read_text(encoding="utf-8")
                )
                url = snapshot["source_url"]
            limitation = [
                "Native source observations; no resampling/filling. Current revised history is not a real-time vintage."
            ]
            m = result["metadata"]
            for field in (
                "history_limit",
                "definition_note",
                "scope",
                "revision_note",
                "update_risk",
                "source_definition_note",
            ):
                if m.get(field):
                    limitation.append(m[field])
            if provider == "ons" and entry["source"]["selector"].split("/")[0] in {
                "MGSX",
                "LF24",
            }:
                limitation.append(
                    "LFS rates refer to overlapping three-month periods; monthly labels are not independent monthly surveys. Survey weighting/method changes require care."
                )
            if key == "ons_a007e11b21ed0f67ccf1":
                limitation.append(
                    "ONS September 2026 QNA identifies 2024 as the chained-volume reference year. These are real-volume GBP millions, not current-price pounds. Benchmark changes require renewed review: https://www.ons.gov.uk/economy/grossdomesticproductgdp/bulletins/quarterlynationalaccounts/apriltojune2026"
                )
            if key == "ons_2cc6678249f2ade3e2b2":
                limitation.append(
                    "The September 2026 retail release moved the reference period to 2024=100. Retail statistical months use a source-specific four/five-week calendar; date labels are reference periods, not calendar-day sales: https://www.ons.gov.uk/businessindustryandtrade/retailindustry/bulletins/retailsales/august2026"
                )
            if provider == "ecb":
                limitation.append(
                    "Original ECB data/metadata retained. Any transformed chart is a MacroLens calculation, not an ECB-produced statistic. Policy rates are effective states, not FOMC/ECB announcement timestamps; fixed-tender MRR coverage has genuine gaps."
                )
            if provider == "bls":
                limitation.append(
                    "Employment series count payroll jobs, not unique people. Producer price indexes measure specified output prices, not physical construction activity; current seasonal/benchmark revisions are retained."
                )
            if provider == "eia":
                limitation.append(
                    "Keep price, end-period inventory stocks and production/product-supplied flows separate. Product supplied is an apparent-consumption proxy, not measured final road-material use; spot prices are not futures total returns."
                )
            if key == "fred_cc3466cd68878ef9a36f":
                limitation.append(
                    "M2 money stock is not the monetary base. The 2020 Regulation D/reporting changes affect component classification; current revised levels are not release-time vintages."
                )
            if key == "fred_eebc9f99bdbab57ba333":
                limitation.append(
                    "Total reserves are not total Federal Reserve assets. Reserve requirements fell to zero in March 2020; regulatory/method changes affect comparisons."
                )
            name = entry["name"]
            if (
                provider == "uk_building_materials"
                and result["definition"]["adjustment"] == "Seasonally adjusted"
            ):
                name += " (seasonally adjusted)"
            region = (
                "UK (Great Britain)"
                if provider == "uk_building_materials"
                else entry["region"]
            )
            if provider == "eurostat":
                region = m["dimension_labels"]["geo"]
                name += " — " + region
                limitation.append(
                    "Geography is the exact selected source composition, not a silently changing aggregate; native adjustment and volume/price definitions are retained."
                )
            row = {
                "id": key,
                "name": name,
                "category": entry["category"],
                "region": region,
                "definition": result["definition"],
                "source_url": url,
                "license_url": license_url,
                "rights_evidence": "EXPANSION_REVIEW_2026_10_30:" + provider,
                "rights_basis": basis,
                "attribution": [
                    source + "; accessed 2026-10-30. Source link and licence retained."
                ],
                "limitations": limitation,
                "ai_allowed": False,
                "discovery_allowed": False,
                "planning_refs": entry.get("planning_refs", []),
                "release_unit": provider
                + ("_" + region.replace(" ", "_") if provider == "eurostat" else ""),
                "validation": {
                    k: result[k]
                    for k in (
                        "observations",
                        "nonnull",
                        "first",
                        "last",
                        "source_bytes",
                        "snapshot_hash",
                    )
                },
                "source_metadata": m,
                "state": "captured_awaiting_ingestion_validation",
            }
            successes.append(row)
            continue
        reason = result.get("reason", "")
        category = "technical failure"
        action = "Implement and validate an exact original-producer adapter; keep private until complete."
        if key.startswith("wb_"):
            reason = "Existing private pilot: underlying benchmark rights remain unreviewed; iron-ore unit/benchmark conflict unresolved. Existing observations untouched."
            category = "licensing"
        elif provider in {
            "world_bank",
            "lme",
            "mpa",
            "worldsteel",
            "boj",
            "oecd",
            "nbs_china",
            "comtrade",
            "hmrc",
            "jodi",
        }:
            category = "licensing"
            reason = (
                reason
                or "Source-specific onward rights / original-owner evidence not cleared; provider availability is not permission."
            )
            if provider == "oecd":
                reason = (
                    "OECD underlying national/third-party source ownership not cleared for this exact selection; "
                    + (
                        "real history captured privately"
                        if result.get("state") == "captured"
                        else (reason or "capture not complete")
                    )
                )
            if provider == "boj":
                reason = "BOJ terms require prior permission for commercial copying; data endpoint works but permission not granted."
            action = "Resolve exact source-owner rights and required attribution; do not switch flags based on API access."
        elif "BCIS/MPA" in reason:
            category = "licensing"
            action = "Obtain underlying BCIS/MPA redistribution permission or use separately selected original statistics."
        elif "unit" in reason.lower() or "benchmark" in reason.lower():
            category = "benchmark/unit mismatch"
            action = "Resolve official native unit/reference base and historical changes; then add guarded parser."
        elif provider == "boe":
            reason = "Official CSV endpoint redirected to ErrorPage.asp?ei=905 (HTTP 200 HTML), including documented TN format test. Database OGL terms verified; do not parse the error page as observations."
            category = "source access"
            action = "Check official IADB availability and current documented export parameters; no proxy or access-control workaround."
        elif provider == "japan_dashboard":
            reason = "Official e-Stat dashboard endpoint returned HTTP 502 in both initial and follow-up checks."
            category = "source access"
            action = "Retry after service recovery, validate exact dimensions and source-specific PDL terms."
        elif "credential" in reason:
            category = "source access"
            action = "Use a free operator-supplied EIA key or a documented original downloadable table; no key committed."
        elif "selector" in reason.lower() or entry["kind"] == "selection":
            category = "ambiguous selector"
            action = "Pin actual atomic source columns/rows, units and geography; do not invent aggregate observations."
        if key == "fred_f007c60ecacde1bf5fb2":
            category = "licensing"
            reason = "Full Board daily effective-rate history captured; complete NY Fed reference-rate republication disclaimer review before display. This is not a target-event calendar."
            action = "Retain the source-specific NY Fed terms/required notice; then activate as a separate release unit."
        if not reason:
            reason = "Original-producer transport/parser not completed in this execution; FRED-route redistribution scope remains unresolved. Not a demonstrated provider outage."
        if provider == "fred" and key != "fred_f007c60ecacde1bf5fb2":
            selected = entry["source"]["selector"]
            unfinished = {
                "EMRATIO": (
                    "technical failure",
                    "BLS CPS employment/population ratio source adapter not completed; no provider outage demonstrated",
                    "Validate BLS LNS12300000, then use the existing bounded BLS transport with a separately reviewed definition.",
                ),
                "PPIFIS": (
                    "ambiguous selector",
                    "Exact producer-native final-demand SA PPI selection is not yet validated",
                    "Validate candidate BLS WPSFD4, native base and adjustment before using the BLS adapter.",
                ),
                "NEWORDER": (
                    "ambiguous selector",
                    "Census M3 nondefense capital-goods excluding-aircraft row/facet not pinned in a producer-native response",
                    "Pin the original Census M3 table selection and distinguish this from total durable-goods orders.",
                ),
                "DGORDER": (
                    "technical failure",
                    "Census M3 total durable-goods order parser not completed; no provider outage demonstrated",
                    "Add exact M3 selection and revision/SA tests using the existing snapshot engine.",
                ),
                "CCSA": (
                    "technical failure",
                    "DOL ETA continued-claims history and Saturday reference calendar parser not completed",
                    "Pin the ETA insured-unemployment total and native weekly convention; do not infer from initial claims.",
                ),
                "HSN1F": (
                    "technical failure",
                    "Census new-home-sales historical workbook parser not completed",
                    "Use original Census residential-sales tables; preserve SAAR thousands and revisions.",
                ),
                "HOUST1F": (
                    "technical failure",
                    "Census one-unit housing starts historical selection/parser not completed",
                    "Validate single-family units, SAAR and history; do not substitute the existing all-unit starts ID.",
                ),
                "RRSFS": (
                    "licensing",
                    "St Louis Fed real-retail-sales derived series is not simply an original federal producer table; route/method/rights need review",
                    "Clear the Bank-created series or register a separately defined original-source alternative; never silently recalculate under this ID.",
                ),
                "CSUSHPINSA": (
                    "licensing",
                    "S&P Cotality Case-Shiller is third-party benchmark data, not federal public-domain statistics",
                    "Obtain source-specific redistribution evidence; FRED availability does not grant onward rights.",
                ),
                "TCU": (
                    "infrastructure capacity",
                    "Original G17 bulk ZIP exceeded the current 8 MiB transport bound; a selected-series streaming route is not yet implemented",
                    "Build a bounded disk-streaming G17 selection and measure it before admitting a larger archive.",
                ),
                "IPMAN": (
                    "infrastructure capacity",
                    "Original G17 bulk ZIP exceeded the current 8 MiB transport bound; manufacturing selection requires the same shared streaming adapter",
                    "Reuse the bounded G17 fix, pin NAICS manufacturing index/base and validate revisions.",
                ),
                "WALCL": (
                    "infrastructure capacity",
                    "Original H41 bulk ZIP exceeded the current 8 MiB transport bound; Wednesday total-assets selection is not yet pinned in the native adapter",
                    "Use bounded original H41 transport and verify exact total-assets/eliminations/Wednesday-level units.",
                ),
                "SOFR": (
                    "technical failure",
                    "Official NY Fed SOFR JSON returned real observations, but the required republication notices have not been integrated/reviewed",
                    "Use the working original API, retain NY Fed required disclaimer and native business dates; business-use grant exists and no paid subscription is assumed.",
                ),
            }
            if selected in unfinished:
                category, reason, action = unfinished[selected]
        exceptions.append(
            {
                "id": key,
                "name": entry["name"],
                "provider": provider,
                "selector": entry["source"]["selector"],
                "planning_refs": entry.get("planning_refs", []),
                "category": category,
                "blocker": reason,
                "recommended_action": action,
                "captured_privately": result.get("state") == "captured",
            }
        )
    REPORT.mkdir(parents=True, exist_ok=True)
    candidate_data = {
        "version": 1,
        "checked_at": "2026-10-30",
        "activation": "Requires separate database grant; no automatic publication",
        "datasets": successes,
    }
    (ROOT / "catalog/release_candidates.json").write_text(
        json.dumps(candidate_data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (REPORT / "exceptions.json").write_text(
        json.dumps({"entries": exceptions}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (REPORT / "rights_evidence.json").write_text(
        json.dumps(
            {
                p: {"url": a, "basis": b, "attribution": c}
                for p, (a, b, c) in RIGHTS.items()
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "release_candidates": len(successes),
                "captured_observations": sum(
                    r["validation"]["observations"] for r in successes
                ),
                "exceptions": len(exceptions),
                "providers": dict(
                    Counter(r["definition"]["provider"] for r in successes)
                ),
            }
        )
    )


if __name__ == "__main__":
    main()
