"""Bounded offline format adapters. No HTTP client, credentials or live registration.

Transport must enforce byte/time limits AND pin a genuine source snapshot before
using these contracts. Latest-only APIs without a stable snapshot need a reviewed
reconciliation method; an arbitrary client token is not evidence of consistency.
"""

import csv
import io
import json
import re
from dataclasses import dataclass
from datetime import datetime

from backend.app.ingestion.native import Observation


@dataclass(frozen=True)
class AccessProfile:
    format: str
    endpoint: str
    credentials: str
    restrictions: str


PROFILES = {
    "fred": AccessProfile(
        "fred_json",
        "https://api.stlouisfed.org/fred/series/observations",
        "Free registered API key",
        "FRED service/API caching, redistribution and AI terms require review; per-series third-party rights differ. Pin realtime vintage and explicit native frequency.",
    ),
    "eurostat": AccessProfile(
        "eurostat_jsonstat",
        "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/",
        "No key",
        "Pin every non-time dimension. EU/source exceptions and attribution apply. Latest data are revised, not automatically a frozen snapshot.",
    ),
    "ons": AccessProfile(
        "ons_json",
        "https://www.ons.gov.uk/",
        "Public downloads; no key",
        "Pinned CDID/dataset and native array; OGL exceptions, overlapping labour periods, reference bases and release versions require review.",
    ),
    "eia": AccessProfile(
        "eia_json",
        "https://api.eia.gov/v2/",
        "Free EIA key; no key is stored here",
        "Use v2 facets/units/pagination, not retired v1. Respect third-party exceptions; latest-only pages require consistency verification.",
    ),
    "oecd": AccessProfile(
        "sdmx_csv",
        "https://sdmx.oecd.org/public/rest/v1/data/",
        "No required key",
        "Pin agency/flow/version/dimensions, UNIT_MULT and OBS_STATUS. OECD data terms retain third-party restrictions.",
    ),
    "ecb": AccessProfile(
        "sdmx_csv",
        "https://data-api.ecb.europa.eu/service/data/",
        "No key",
        "Pin flow/key and reference calendar; updatedAfter is a delta, not a complete historical snapshot. ESCB terms exclude third-party content.",
    ),
}


def source_key(label, frequency, provider):
    """Interpret only documented native formats, preserving label separately."""
    if frequency in {"event", "irregular"}:
        return label
    if provider in {"fred", "eia"} and re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}", label
    ):
        if frequency == "monthly" and label.endswith("-01"):
            return label[:7]
        if frequency == "quarterly" and label[5:] in {
            "01-01",
            "04-01",
            "07-01",
            "10-01",
        }:
            return label[:4] + "-Q" + str((int(label[5:7]) - 1) // 3 + 1)
        if frequency == "annual" and label.endswith("-01-01"):
            return label[:4]
    if provider == "ons":
        if frequency == "monthly":
            match = re.fullmatch(r"([0-9]{4}) ([A-Z]{3})", label)
            if match:
                months = (
                    "JAN",
                    "FEB",
                    "MAR",
                    "APR",
                    "MAY",
                    "JUN",
                    "JUL",
                    "AUG",
                    "SEP",
                    "OCT",
                    "NOV",
                    "DEC",
                )
                return f"{match[1]}-{months.index(match[2]) + 1:02d}"
        if frequency == "quarterly" and re.fullmatch(r"[0-9]{4} ?Q[1-4]", label):
            return label[:4] + "-Q" + label[-1]
    return label


def number(value, missing):
    if value is None or isinstance(value, str) and value.strip() in missing:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise TypeError("Invalid observation value")
    return float(value)


def flags(row):
    return tuple(
        f"{key}={row[key]}"
        for key in (
            "status",
            "OBS_STATUS",
            "UNIT_MULT",
            "realtime_start",
            "realtime_end",
        )
        if key in row and row[key] not in (None, "")
    )


def observation(row, label, definition, missing):
    if "value" not in row:
        raise ValueError("Missing source value field is not a source null")
    release = row.get("release_at")
    return Observation(
        source_key(label, definition.frequency, definition.provider),
        label,
        number(row.get("value"), missing),
        flags(row),
        datetime.fromisoformat(release) if release else None,
        row.get("source_revision"),
        row.get("event_id"),
    )


def parse_payload(definition, payload, *, max_rows=250, max_bytes=524288):
    """Return only actual source-labelled records; no inferred dates or filling."""
    if (
        not isinstance(payload, bytes)
        or len(payload) > max_bytes
        or not 1 <= max_rows <= 1000
        or not 1 <= max_bytes <= 524288
    ):
        raise ValueError("Provider response exceeds bound")
    profile = PROFILES.get(definition.provider)
    if profile is None:
        raise ValueError("No reviewed format contract")
    pinned = dict(definition.dimensions)
    text = payload.decode("utf-8-sig")
    if profile.format == "sdmx_csv":
        rows = []
        reader = csv.DictReader(io.StringIO(text))
        headers = reader.fieldnames or []
        if (
            len(headers) != len(set(headers))
            or not {"TIME_PERIOD", "OBS_VALUE"} <= set(headers)
            or definition.unit_multiplier != 0
            and "UNIT_MULT" not in headers
        ):
            raise ValueError("Invalid SDMX header or missing unit multiplier")
        for row in reader:
            if len(rows) >= max_rows:
                raise ValueError("Provider page exceeds row bound")
            if any(row.get(k) != v for k, v in pinned.items()):
                raise ValueError("SDMX selection changed")
            if "UNIT_MULT" in row and row["UNIT_MULT"] != str(
                definition.unit_multiplier
            ):
                raise ValueError("SDMX unit multiplier changed")
            rows.append(
                observation(
                    {**row, "value": row["OBS_VALUE"]},
                    row["TIME_PERIOD"],
                    definition,
                    {"", ":", "NA"},
                )
            )
        return tuple(rows)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise TypeError("Expected provider object")
    if profile.format == "fred_json":
        records = data["observations"]
        if not isinstance(records, list) or len(records) > max_rows:
            raise ValueError("Provider page exceeds row bound")
        return tuple(observation(r, r["date"], definition, {"."}) for r in records)
    if profile.format == "ons_json":
        cdid = data.get("description", {}).get("cdid")
        if (
            cdid is not None
            and cdid.casefold() != definition.selector.split("/")[0].casefold()
        ):
            raise ValueError("ONS CDID changed")
        array = {"monthly": "months", "quarterly": "quarters", "annual": "years"}.get(
            definition.frequency
        )
        if array is None:
            raise ValueError("ONS format needs an explicit supported native array")
        records = data[array]
        if not isinstance(records, list) or len(records) > max_rows:
            raise ValueError("Provider page exceeds row bound")
        return tuple(
            observation(r, r["date"], definition, {"", ":", ".."}) for r in records
        )
    if profile.format == "eia_json":
        response = data["response"]
        records = response["data"]
        if (
            response.get("frequency", definition.frequency) != definition.frequency
            or not isinstance(records, list)
            or len(records) > max_rows
        ):
            raise ValueError("EIA frequency/page changed")
        rows = []
        for row in records:
            if row.get("value-units") != definition.units or any(
                row.get(k) != v for k, v in pinned.items()
            ):
                raise ValueError("EIA units/facets changed")
            rows.append(observation(row, row["period"], definition, {"", "NA", "--"}))
        return tuple(rows)
    # JSON-stat's sparse values are explicit source missing cells only when the
    # time dimension contains that label. Never construct additional time labels.
    ids, sizes, dims = data["id"], data["size"], data["dimension"]
    if len(ids) != len(sizes) or len(set(ids)) != len(ids) or "time" not in ids:
        raise ValueError("Invalid JSON-stat dimensions")
    if set(pinned) != set(ids) - {"time"}:
        raise ValueError("Every non-time dimension must be pinned")
    for axis, size in zip(ids, sizes, strict=True):
        if axis != "time":
            index = dims[axis]["category"]["index"]
            selected = list(index) if isinstance(index, dict) else index
            if size != 1 or selected != [pinned[axis]]:
                raise ValueError("Unpinned JSON-stat cube")
    index = dims["time"]["category"]["index"]
    index = (
        dict(enumerate(index))
        if isinstance(index, list)
        else {v: k for k, v in index.items()}
    )
    if len(index) > max_rows or set(index) != set(range(sizes[ids.index("time")])):
        raise ValueError("Invalid JSON-stat time index")
    values, statuses = data["value"], data.get("status", {})
    if isinstance(values, list):
        if len(values) != len(index):
            raise ValueError("JSON-stat values size mismatch")
        values = {str(i): value for i, value in enumerate(values)}
    if not isinstance(values, dict) or set(values) - {str(i) for i in index}:
        raise ValueError("Invalid JSON-stat value index")
    if isinstance(statuses, list):
        if len(statuses) != len(index):
            raise ValueError("Invalid JSON-stat flags")
        statuses = {str(i): value for i, value in enumerate(statuses)}
    if not isinstance(statuses, dict) or set(statuses) - {str(i) for i in index}:
        raise ValueError("Invalid JSON-stat flags")
    return tuple(
        observation(
            {"value": values.get(str(i)), "status": statuses.get(str(i))},
            index[i],
            definition,
            {":"},
        )
        for i in sorted(index)
    )
