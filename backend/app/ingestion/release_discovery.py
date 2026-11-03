"""Official GOV.UK Content API discovery, not HTML scraping or filename guessing.

Adapter contract only: dated DESNZ/DBT definitions remain publication/refresh-held
until moving-issue provenance and full-history reconciliation are reviewed.
"""

import json
import re
from urllib.parse import urlsplit

from backend.app.ingestion.contracts import ProviderError
from backend.app.ingestion.official_snapshots import download, safe_url

BASE = "https://www.gov.uk/api/content"
COLLECTION = (
    "/government/collections/building-materials-and-components-monthly-statistics-2012"
)


def attachment(document, *, table=None, materials=False):
    selected = []
    for row in document.get("details", {}).get("attachments", []):
        url, title = row.get("url", ""), row.get("title", "")
        if not urlsplit(url).path.casefold().endswith(".xlsx"):
            continue
        if (
            materials
            and "construction building materials: tables" in title.casefold()
            or table
            and re.search(r"\bET\s+" + re.escape(table) + r"\s*-", title)
        ):
            if urlsplit(url).hostname != "assets.publishing.service.gov.uk":
                raise ProviderError("discovery_unapproved_attachment")
            selected.append(safe_url(url))
    if len(set(selected)) != 1:
        raise ProviderError("discovery_missing_or_ambiguous_attachment")
    return selected[0]


def discover(entry, *, fetch=download):
    provider = entry["source"]["provider"]
    if provider == "desnz":
        table = entry["source"]["selector"].split()[1]
        section = {
            "3": "oil-and-oil-products-section-3-energy-trends",
            "4": "gas-section-4-energy-trends",
            "5": "electricity-section-5-energy-trends",
        }.get(table.split(".")[0])
        if not section:
            raise ProviderError("unreviewed_discovery_table")
        path = "/government/statistics/" + section
        body, _ = fetch(BASE + path)
        data = json.loads(body)
        return attachment(data, table=table), {
            "discovery_url": BASE + path,
            "updated_at": data.get("public_updated_at"),
        }
    if provider != "uk_building_materials":
        raise ProviderError("unreviewed_release_discovery")
    raw, _ = fetch(BASE + COLLECTION)
    data = json.loads(raw)
    linked = data.get("links", {}).get("documents", [])
    if not 0 < len(linked) <= 1000:
        raise ProviderError("discovery_collection_budget")
    releases = [
        r
        for r in linked
        if re.fullmatch(
            r"/government/statistics/building-materials-and-components-statistics-[a-z]+-[0-9]{4}",
            r.get("base_path", ""),
        )
    ]
    if not releases or any(not r.get("public_updated_at") for r in releases):
        raise ProviderError("discovery_release_date_missing")
    latest = max(releases, key=lambda r: r["public_updated_at"])
    raw, _ = fetch(BASE + latest["base_path"])
    return attachment(json.loads(raw), materials=True), {
        "discovery_url": BASE + latest["base_path"],
        "updated_at": latest["public_updated_at"],
    }
