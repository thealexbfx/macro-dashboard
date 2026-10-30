"""Reconcile preserved research locally. No network, SQLite or runtime registration.

The checked-in manifest is the canonical assignment record. IDs are based on
source identities, never display names or ML/G numbering. Multi-series selections
stay selections; this script does not invent countries, flows or missing sources.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from backend.app.catalog.manifest import canonical_id, identity, validate

PLANNING = REPO / "research/planning/batch0"
WB_URL = "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx"
WB_LICENSE = "https://www.worldbank.org/ext/en/legal/terms-conditions/datasets"
JODI_LICENSE = "https://www.jodidata.org/terms-of-use.aspx"


def provider_name(text):
    for prefix, name in (
        ("FRED", "fred"),
        ("Eurostat", "eurostat"),
        ("ONS", "ons"),
        ("OECD", "oecd"),
        ("ECB", "ecb"),
        ("Bank of England", "boe"),
        ("Bank of Japan", "boj"),
        ("Statistics Bureau", "japan_dashboard"),
        ("DBT", "uk_building_materials"),
        ("Mineral Products", "mpa"),
        ("DESNZ", "desnz"),
        ("USGS", "usgs"),
        ("US Energy", "eia"),
        ("National Bureau", "nbs_china"),
    ):
        if text.startswith(prefix):
            return name
    raise ValueError("Unmapped source provider")


def frequency(text):
    for prefix, result in (
        ("Daily", "daily"),
        ("Weekly", "weekly"),
        ("Monthly", "monthly"),
        ("Quarterly", "quarterly"),
        ("Annual", "annual"),
    ):
        if text.startswith(prefix):
            return result
    raise ValueError("Unmapped frequency")


def entry(
    *,
    name,
    category,
    region,
    provider,
    selector,
    endpoint,
    units,
    freq,
    refs,
    evidence,
    license_url,
    kind="series",
    adjustment="Unverified",
    history=None,
    source_status="researched_not_implemented",
):
    result = {
        "id": "",
        "name": name,
        "kind": kind,
        "planning_refs": refs,
        "category": category,
        "region": region,
        "units": units,
        "frequency": freq,
        "seasonal_adjustment": adjustment,
        "source": {
            "provider": provider,
            "selector": selector,
            "endpoint": endpoint,
            "status": source_status,
        },
        "history": history or {"start": None, "end": None},
        "rights": {"status": "unreviewed", "evidence": [license_url]},
        "publication": {
            "status": "planned",
            "public_display": False,
            "ai": False,
            "discovery": False,
        },
        "source_evidence": evidence,
    }
    result["id"] = canonical_id(result)
    return result


def gap_entries():
    # Exact original wording remains in originals/. These are transparent normalized
    # selections, with actual pilot evidence overriding G15's old unit assumption.
    data = []

    def add(
        n,
        name,
        provider,
        selector,
        endpoint,
        units,
        freq="monthly",
        region="Global",
        kind="series",
        license_url=WB_LICENSE,
        status="documentation_only",
        category="Commodities",
    ):
        data.append(
            entry(
                name=name,
                category=category,
                region=region,
                provider=provider,
                selector=selector,
                endpoint=endpoint,
                units=units,
                freq=freq,
                refs=[f"G{n:02d}"],
                license_url=license_url,
                kind=kind,
                evidence=[
                    {
                        "path": "research/planning/batch0/originals/MACROLENS_INCREMENTAL_RESOURCE_GAPS.md",
                        "reference": f"G{n:02d}",
                        "validation": status,
                    }
                ],
                source_status=status,
            )
        )

    for n, name, selector, units in (
        (1, "Brent crude, monthly nominal price", "Crude oil, Brent", "USD / barrel"),
        (2, "European natural gas benchmark", "Natural gas, Europe", "USD / MMBtu"),
        (3, "Australian thermal coal benchmark", "Coal, Australia", "USD / tonne"),
        (13, "Copper, monthly nominal price", "Copper", "USD / metric tonne"),
        (14, "Aluminium benchmark", "Aluminum", "USD / metric tonne"),
        (
            15,
            "Iron ore CFR spot, source-native monthly price",
            "Iron ore, cfr spot",
            "Source-labelled USD / dmtu; definition conflict requires review",
        ),
        (16, "Nickel benchmark", "Nickel", "USD / metric tonne"),
        (17, "Zinc benchmark", "Zinc", "USD / metric tonne"),
    ):
        add(n, name, "world_bank", selector, WB_URL, units)
    for n, name, selector, units, gas in (
        (
            4,
            "Crude-production country panel",
            "CRUDEOIL/INDPROD/KBD",
            "thousand barrels/day",
            False,
        ),
        (
            5,
            "Refinery-intake country panel",
            "CRUDEOIL/REFINOBS/KBD",
            "thousand barrels/day",
            False,
        ),
        (
            6,
            "Petroleum-products demand panel",
            "TOTPRODS/TOTDEMO/KBD",
            "thousand barrels/day",
            False,
        ),
        (
            7,
            "Non-US crude-inventory panel",
            "CRUDEOIL/CLOSTLV/KBBL",
            "thousand barrels",
            False,
        ),
        (
            8,
            "Crude imports and exports panel",
            "CRUDEOIL/TOTIMPSB,TOTEXPSB/KBD",
            "thousand barrels/day",
            False,
        ),
        (
            9,
            "Gas production and demand panel",
            "NATGAS/INDPROD,TOTDEMO/M3",
            "Native M3 scaling requires validation",
            True,
        ),
        (
            10,
            "LNG imports and exports panel",
            "NATGAS/IMPLNG,EXPLNG/M3",
            "Native gas-volume M3 scaling requires validation",
            True,
        ),
    ):
        add(
            n,
            name,
            "jodi",
            selector,
            "https://www.jodidata.org/api/" + ("gasdata" if gas else "oildata"),
            units,
            kind="selection",
            license_url=JODI_LICENSE,
        )
    for n, name, selector in (
        (11, "US gasoline inventories", "PET.WGTSTUS1.W"),
        (12, "US distillate inventories", "PET.WDISTUS1.W"),
    ):
        add(
            n,
            name,
            "eia",
            selector,
            f"https://api.eia.gov/v2/seriesid/{selector}",
            "Thousand barrels; validate response",
            freq="weekly",
            region="US",
            license_url="https://www.eia.gov/about/copyrights_reuse.php",
            status="table_checked",
        )
    copper = "https://www.usgs.gov/centers/national-minerals-information-center/copper-statistics-and-information"
    usgs_license = "https://www.usgs.gov/data-management/access-controls-and-copyrights"
    add(
        18,
        "US copper mine production",
        "usgs",
        "Copper MIS/Table 2/US mine production",
        copper,
        "Physical quantity; scaling requires validation",
        region="US",
        license_url=usgs_license,
        status="table_checked",
    )
    add(
        19,
        "US refined-copper stock components",
        "usgs",
        "Copper MIS/Table 10/producer,fabricator,exchange stocks",
        copper,
        "Physical quantity; scaling requires validation",
        region="US",
        kind="selection",
        license_url=usgs_license,
        status="table_checked",
    )
    add(
        20,
        "LME copper and aluminium warehouse stocks",
        "lme",
        "Stocks breakdown/components unresolved",
        "https://www.lme.com/en/Market-data/Reports-and-data/Warehouse-and-stocks-reports",
        "Tonnes/components require validation",
        freq="daily",
        kind="selection",
        license_url="https://www.lme.com/en/market-data/market-data-licensing/data-distribution",
        status="selection_pending",
    )
    for n, name, code in (
        (21, "China iron-ore import net weight", "2601"),
        (22, "China copper-cathode import net weight", "740311"),
    ):
        add(
            n,
            name,
            "comtrade",
            f"C/M/HS/156/0/{code}/M/netWgt",
            f"https://comtradeapi.un.org/public/v1/preview/C/M/HS?reporterCode=156&partnerCode=0&cmdCode={code}&flowCode=M",
            "kg net weight; validate response",
            region="China",
            license_url="https://uncomtrade.org/docs/policy-on-comtrade-data-use/",
        )
    add(
        23,
        "World copper mine and refinery production",
        "usgs",
        "MCS2026/Copper/World Mine and Refinery Production and Reserves",
        "https://pubs.usgs.gov/publication/mcs2026",
        "Quantity scaling requires validation",
        freq="annual",
        kind="selection",
        license_url=usgs_license,
        status="selection_pending",
    )
    add(
        24,
        "Country crude-steel production panel",
        "worldsteel",
        "country/month/crude steel",
        "https://worldsteel.org/data/",
        "Tonnes; scaling requires validation",
        kind="selection",
        license_url="https://worldsteel.org/data/about-our-data/",
    )
    add(
        25,
        "Missouri residential permits by structure",
        "census",
        "BPS/state monthly/FIPS29/structure types",
        "https://www.census.gov/construction/bps/statemonthly.html",
        "Housing units",
        region="US-MO",
        kind="selection",
        category="Construction",
        license_url="https://www.census.gov/about/policies/quality/data_stewardship.html",
    )
    add(
        26,
        "Missouri construction employment",
        "bls",
        "SMS29000002000000001",
        "https://api.bls.gov/publicAPI/v2/timeseries/data/",
        "Thousands of persons",
        region="US-MO",
        category="Construction",
        license_url="https://www.bls.gov/bls/linksite.htm",
    )
    for n, name in (
        (27, "Missouri crushed-stone quantity"),
        (28, "Missouri construction sand-and-gravel quantity"),
    ):
        add(
            n,
            name,
            "usgs",
            name + "/exact file and row unresolved",
            "https://www.usgs.gov/centers/national-minerals-information-center/mineral-industry-missouri",
            "Quantity/unit requires validation",
            freq="annual",
            region="US-MO",
            category="Construction",
            license_url=usgs_license,
            status="selection_pending",
        )
    for n, name, units in (
        (29, "Missouri awarded highway contracts", "USD"),
        (
            30,
            "Missouri awarded material quantities and unit prices",
            "Mixed units; atomic selections required",
        ),
    ):
        add(
            n,
            name,
            "modot",
            name + "/project,letting,item mapping unresolved",
            "https://epg.modot.org/index.php/Category:102_Bidding_Requirements_and_Conditions",
            units,
            freq="event",
            region="US-MO",
            kind="selection",
            category="Construction",
            license_url="https://www.modot.org/",
            status="selection_pending",
        )
    for n, name in (
        (31, "GB total construction new orders"),
        (32, "GB infrastructure new orders"),
    ):
        add(
            n,
            name,
            "ons",
            f"bulletindataset7/{name}/exact sheet,CDID,adjustment unresolved",
            "https://www.ons.gov.uk/file?uri=/businessindustryandtrade/constructionindustry/datasets/newordersintheconstructionindustry/current/bulletindataset7.xlsx",
            "CVM unit/base requires validation",
            freq="quarterly",
            region="UK (Great Britain)",
            category="Construction",
            license_url="https://www.ons.gov.uk/help/terms-conditions",
            status="selection_pending",
        )
    for n, name, selector in (
        (
            33,
            "UK cement/clinker import-export quantities",
            "HS2523/subheadings/import,export/net mass",
        ),
        (
            34,
            "UK aggregate import-export quantities",
            "HS251710/import,export/net mass",
        ),
    ):
        add(
            n,
            name,
            "hmrc",
            selector,
            "https://api.uktradeinfo.com/OTS",
            "Net mass; scaling requires validation",
            region="UK",
            kind="selection",
            category="Construction",
            license_url="https://www.uktradeinfo.com/terms-and-conditions",
        )
    assert len(data) == 34
    return sorted(data, key=lambda e: e["planning_refs"])


def build():
    original_path = (
        "research/planning/batch0/originals/MACROLENS_PROPOSED_SERIES_CATALOG.json"
    )
    originals = json.loads((REPO / original_path).read_text(encoding="utf-8"))
    legacy = json.loads(
        (PLANNING / "legacy_public_e70.json").read_text(encoding="utf-8")
    )
    rows = []
    for old in originals:
        rows.append(
            entry(
                name=old["name"],
                category=old["topic"],
                region=old["country"],
                provider=provider_name(old["provider"]),
                selector=old["series_identifier"],
                endpoint=old["endpoint"],
                units=old["units"],
                freq=frequency(old["frequency"]),
                refs=[old["catalog_id"]],
                adjustment=old["seasonal_adjustment"],
                license_url=old["license_url"],
                history={"start": old["coverage_start"], "end": old["coverage_end"]},
                evidence=[
                    {
                        "path": original_path,
                        "reference": old["catalog_id"],
                        "validation": old["verification"],
                    }
                ],
            )
        )
    rows.extend(gap_entries())
    for spec in legacy:
        matches = [
            e
            for e in rows
            if e["source"]["provider"] == spec["provider"]
            and e["source"]["selector"] == spec["provider_id"]
        ]
        if len(matches) > 1:
            raise ValueError("Ambiguous legacy alias")
        if matches:
            current = matches[0]
        else:
            current = entry(
                name=spec["name"],
                category=spec["category"],
                region=spec["region"],
                provider=spec["provider"],
                selector=spec["provider_id"],
                endpoint=spec["source_url"],
                units=spec["units"],
                freq=spec["frequency"],
                refs=[],
                adjustment=spec["seasonal_adjustment"] or "Not applicable",
                license_url="https://fred.stlouisfed.org/legal/terms/"
                if spec["provider"] == "fred"
                else "https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html",
                evidence=[
                    {
                        "path": "research/planning/batch0/legacy_public_e70.json",
                        "reference": spec["id"],
                        "validation": "Existing release definition; not a rights approval",
                    }
                ],
            )
            rows.append(current)
        current["id"] = spec["id"]
        for field in ("name", "category", "region", "units", "frequency"):
            current[field] = spec[field]
        current["seasonal_adjustment"] = spec["seasonal_adjustment"] or "Not applicable"
        current["publication"].update(
            status="legacy_public", public_display=True, discovery=spec["id"] != "wti"
        )
        current["source_evidence"].append(
            {
                "path": "research/planning/batch0/legacy_public_e70.json",
                "reference": spec["id"],
                "validation": "Preserved canonical public ID",
            }
        )
    for ref, key in (
        ("G01", "wb_brent_monthly"),
        ("G13", "wb_copper_monthly"),
        ("G15", "wb_iron_ore_monthly"),
    ):
        current = next(e for e in rows if ref in e["planning_refs"])
        current["id"] = key
        current["publication"]["status"] = "private_ingested"
        current["history"] = {
            "start": "1960-01",
            "end": "2026-09",
            "count": 801,
            "evidence_basis": "operator_reported_production; not queried by generator",
        }
        current["source_evidence"].append(
            {
                "path": "WORLD_BANK_INGESTION_READINESS.md",
                "reference": key,
                "validation": "Pilot extraction and benchmark review; iron ore remains unit_review",
            }
        )
    result = {
        "schema_version": 1,
        "base_release": "e70e338a546afb64bf1e427f12bd63532f7ec9b4",
        "planning_selection_count": 298,
        "datasets": sorted(rows, key=lambda e: e["id"]),
    }
    assert len(originals) == 264 and len(rows) == 309
    assert len({identity(e) for e in rows}) == 309
    return validate(result)


if __name__ == "__main__":
    output = REPO / "catalog/datasets.json"
    output.parent.mkdir(exist_ok=True)
    payload = build()
    if output.exists():
        previous = {
            identity(e): e["id"] for e in json.loads(output.read_text())["datasets"]
        }
        if any(
            previous.get(identity(e), e["id"]) != e["id"] for e in payload["datasets"]
        ):
            raise SystemExit("Canonical reassignment requires explicit review")
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    print("309 manifest entries; 298 planning references; no runtime registration")
