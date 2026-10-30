"""Validated planning metadata, independent of observation loading and runtime grants."""

import json
import re
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[3] / "catalog"
FREQUENCIES = {"daily", "weekly", "monthly", "quarterly", "annual"}
SCOPES = {"public_display", "ai", "discovery"}
MAX_MANIFEST_BYTES = 2 * 1024 * 1024
LEGACY_PUBLIC_SOURCES = {
    "cpi": "CPIAUCSL",
    "core_cpi": "CPILFESL",
    "pce": "PCEPI",
    "core_pce": "PCEPILFE",
    "unemployment": "UNRATE",
    "payrolls": "PAYEMS",
    "real_gdp_growth": "A191RL1Q225SBEA",
    "fed_funds": "FEDFUNDS",
    "sp500": "^GSPC",
    "gold": "GC=F",
    "us10y": "DGS10",
    "dxy": "DX-Y.NYB",
    "wti": "CL=F",
    "cpi_nsa": "CPIAUCNS",
    "core_cpi_nsa": "CPILFENS",
    "initial_claims": "ICSA",
    "job_openings": "JTSJOL",
    "participation": "CIVPART",
    "hourly_earnings": "CES0500000003",
    "breakeven_5y": "T5YIE",
    "retail_sales": "RSAFS",
    "real_consumption": "PCEC96",
    "consumer_sentiment": "UMCSENT",
    "housing_starts": "HOUST",
    "building_permits": "PERMIT",
    "mortgage_30y": "MORTGAGE30US",
    "industrial_production": "INDPRO",
    "yield_curve": "T10Y2Y",
    "high_yield_spread": "BAMLH0A0HYM2",
    "investment_grade_spread": "BAMLC0A0CM",
}


def identity(entry):
    """Provider selection identity; display names and revised units never mint IDs."""
    source = entry["source"]
    return (source["provider"], source["selector"], entry["region"], entry["frequency"])


def canonical_id(entry):
    # Persist assignments in the manifest. This is for initial assignments only.
    provider = entry["source"]["provider"]
    digest = sha256(json.dumps(identity(entry), ensure_ascii=True).encode()).hexdigest()
    return provider + "_" + digest[:20]


def validate(payload):
    if payload.get("schema_version") != 1 or not isinstance(
        payload.get("datasets"), list
    ):
        raise ValueError("Unsupported manifest")
    entries = payload["datasets"]
    if not 1 <= len(entries) <= 2000:
        raise ValueError("Manifest size out of bounds")
    ids, identities, references = set(), set(), set()
    for entry in entries:
        key = entry["id"]
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,95}", key) or key in ids:
            raise ValueError("Invalid or repeated canonical ID")
        ids.add(key)
        selection = identity(entry)
        if selection in identities:
            raise ValueError("Repeated provider selection; use planning_refs aliases")
        identities.add(selection)
        if entry["kind"] not in {"series", "selection"}:
            raise ValueError("Invalid entry kind")
        if entry["frequency"] not in FREQUENCIES and not (
            entry["kind"] == "selection" and entry["frequency"] == "event"
        ):
            raise ValueError("Invalid frequency")
        if any(
            not isinstance(entry[k], str) or not entry[k].strip()
            for k in ("name", "category", "region", "units", "seasonal_adjustment")
        ):
            raise ValueError("Missing dataset definition")
        source = entry["source"]
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", source["provider"]):
            raise ValueError("Invalid provider")
        if not source["selector"] or not entry["source_evidence"]:
            raise ValueError("Missing source evidence")
        for url in (source["endpoint"], *entry["rights"]["evidence"]):
            parsed = urlsplit(url)
            if (
                parsed.scheme != "https"
                or not parsed.hostname
                or parsed.username
                or parsed.password
            ):
                raise ValueError("Unsafe evidence URL")
        for ref in entry["planning_refs"]:
            if not re.fullmatch(r"ML-[0-9]{3}|G[0-9]{2}", ref) or ref in references:
                raise ValueError("Repeated or invalid planning reference")
            references.add(ref)
        if entry["rights"]["status"] != "unreviewed":
            raise ValueError("Planning metadata cannot grant rights")
        publication = entry["publication"]
        if publication["status"] not in {
            "legacy_public",
            "private_ingested",
            "planned",
        }:
            raise ValueError("Invalid publication status")
        if any(type(publication[scope]) is not bool for scope in SCOPES):
            raise ValueError("Permissions must be booleans")
        if publication["status"] != "legacy_public" and any(
            publication[s] for s in SCOPES
        ):
            raise ValueError("New registrations must be denied in every scope")
        if publication["status"] == "legacy_public" and (
            key not in LEGACY_PUBLIC_SOURCES
            or source["selector"] != LEGACY_PUBLIC_SOURCES[key]
            or source["provider"]
            != ("yahoo" if key in {"sp500", "gold", "wti", "dxy"} else "fred")
            or not publication["public_display"]
        ):
            raise ValueError("Legacy exposure is limited to the frozen 30 definitions")
        if publication["ai"]:
            raise ValueError("AI remains denied")
        if entry["kind"] == "selection" and publication["status"] != "planned":
            raise ValueError("Panels must be expanded before registration")
    if {
        e["id"] for e in entries if e["publication"]["status"] == "legacy_public"
    } != set(LEGACY_PUBLIC_SOURCES):
        raise ValueError("Existing public IDs must all be preserved")
    return payload


class Manifest:
    def __init__(self, payload):
        # Own the input; callers cannot change permissions by retaining a dictionary.
        self._payload = validate(json.loads(json.dumps(payload)))
        self._entries = {e["id"]: e for e in self._payload["datasets"]}

    @classmethod
    def load(cls, path=None):
        with (Path(path) if path else ROOT / "datasets.json").open("rb") as stream:
            data = stream.read(MAX_MANIFEST_BYTES + 1)
        if len(data) > MAX_MANIFEST_BYTES:
            raise ValueError("Manifest exceeds metadata budget")
        return cls(json.loads(data))

    def get(self, key):
        return json.loads(json.dumps(self._entries[key]))

    def page(self, *, offset=0, limit=40, audience="public", query="", region=None):
        """Bounded metadata only. No Store, provider, history or job side effects.

        'planning' is for internal tools; this module has no HTTP route. Public
        filtering precedes counts/pagination, so private names/IDs cannot leak.
        """
        if (
            type(offset) is not int
            or not 0 <= offset <= 100000
            or type(limit) is not int
            or not 1 <= limit <= 100
            or audience not in {"public", "planning"}
            or not isinstance(query, str)
            or len(query) > 200
        ):
            raise ValueError("Invalid metadata page")
        rows = [self._entries[k] for k in sorted(self._entries)]
        if audience == "public":
            rows = [e for e in rows if e["publication"]["public_display"]]
        if region is not None:
            rows = [e for e in rows if e["region"] == region]
        needle = query.casefold()
        if needle:
            rows = [e for e in rows if needle in (e["name"] + " " + e["id"]).casefold()]
        selected = rows[offset : offset + limit]
        fields = ("id", "name", "category", "region", "units", "frequency", "kind")
        return {
            "items": [
                {**{k: e[k] for k in fields}, "provider": e["source"]["provider"]}
                for e in selected
            ],
            "total": len(rows),
            "offset": offset,
            "limit": limit,
            "next_offset": offset + limit if offset + limit < len(rows) else None,
        }
