"""Capture original BLS headline CPI and U-3 histories for private development."""
import argparse
import csv
import io
import json
import math
import re
import ssl
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from urllib.request import HTTPSHandler, Request, build_opener

import certifi

from backend.app.ingestion.bls_history import capture as capture_windows
from backend.app.ingestion.official_snapshots import OfficialRedirects, safe_url

SERIES = {
    "G7-US-07": {
        "id": "CUUR0000SA0",
        "metadata_url": "https://download.bls.gov/pub/time.series/cu/cu.series",
        "fields": {"area_code": "0000", "item_code": "SA0", "seasonal": "U",
                   "periodicity_code": "R", "base_period": "1982-84=100",
                   "series_title": "All items in U.S. city average, all urban consumers, not seasonally adjusted",
                   "begin_year": "1913", "begin_period": "M01"},
        "unit": "1982-1984=100",
    },
    "G7-US-11": {
        "id": "LNS14000000",
        "metadata_url": "https://download.bls.gov/pub/time.series/ln/ln.series",
        "fields": {"lfst_code": "40", "periodicity_code": "M", "seasonal": "S",
                   "series_title": "(Seas) Unemployment Rate",
                   "begin_year": "1948", "begin_period": "M01"},
        "unit": "Percent",
    },
}
ENDPOINT = "https://api.bls.gov/publicAPI/v2/timeseries/data/"


def metadata_row(raw, spec):
    rows = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), delimiter="\t")
    if rows.fieldnames is None:
        raise ValueError("BLS metadata header missing")
    names = [name.strip() for name in rows.fieldnames]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate BLS metadata columns")
    matches = []
    for row in rows:
        entry = {name.strip(): value.strip() if isinstance(value, str) else value
                 for name, value in row.items() if name is not None}
        if entry.get("series_id") == spec["id"]:
            matches.append(entry)
    if len(matches) != 1 or any(matches[0].get(k) != v for k, v in spec["fields"].items()):
        raise ValueError("BLS metadata identity, definition or start period differs")
    row = matches[0]
    if (not re.fullmatch(r"[0-9]{4}", row.get("end_year", ""))
        or not re.fullmatch(r"M(0[1-9]|1[0-2])", row.get("end_period", ""))):
        raise ValueError("BLS metadata lacks a valid last reference month")
    return row


def fetch_metadata(spec):
    """Retain a labelled header/record excerpt, without downloading the whole panel."""
    url = safe_url(spec["metadata_url"])
    opener = build_opener(
        OfficialRedirects(),
        HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where())),
    )
    with opener.open(Request(url, headers={"User-Agent": "MacroLens private source verification"}), timeout=25) as response:
        safe_url(response.geturl())
        header = response.readline(65537)
        if len(header) > 65536:
            raise ValueError("BLS metadata header exceeds budget")
        consumed = len(header)
        while consumed < 1024 * 1024:
            line = response.readline(65537)
            if not line:
                break
            consumed += len(line)
            if consumed > 1024 * 1024 or len(line) > 65536:
                raise ValueError("BLS metadata selection exceeds budget")
            if line.split(b"\t", 1)[0].strip().decode("ascii") == spec["id"]:
                excerpt = header + line
                return metadata_row(excerpt, spec), excerpt
    raise ValueError("BLS metadata series missing from bounded selection")


def parse_history(raw, metadata):
    payload = json.loads(raw)
    rows = payload.get("Results", {}).get("series", [])
    last_year = max(int(meta["end_year"]) for meta in metadata.values())
    if (payload.get("status") != "REQUEST_SUCCEEDED"
        or len(rows) != len(SERIES)
        or {row["seriesID"] for row in rows} != {s["id"] for s in SERIES.values()}
        or len(payload.get("source_windows", [])) != len(range(1913, last_year + 1, 10))):
        raise ValueError("BLS history response or request proof set differs")
    for index, window in enumerate(payload["source_windows"]):
        if (window.get("start") != 1913 + index * 10
            or window.get("end") != min(last_year, 1922 + index * 10)
            or not re.fullmatch(r"[0-9a-f]{64}", window.get("source_hash", ""))
            or type(window.get("bytes")) is not int
            or not 0 < window["bytes"] <= 8 * 1024**2):
            raise ValueError("BLS request window proof differs")
    by_id = {row["seriesID"]: row for row in rows}
    results = {}
    for mapping, spec in SERIES.items():
        points = {}
        excluded_averages = 0
        for row in by_id[spec["id"]]["data"]:
            if row["period"] == "M13":
                excluded_averages += 1
                continue
            if not re.fullmatch(r"M(0[1-9]|1[0-2])", row["period"]):
                raise ValueError("Unexpected BLS source period")
            period = row["year"] + "-" + row["period"][1:]
            if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", period) or period in points:
                raise ValueError("Invalid or duplicate BLS reference period")
            if not isinstance(row["value"], str):
                raise ValueError("BLS value must retain its publisher representation")
            value = None if row["value"] == "-" else float(row["value"])
            if value is not None and (not math.isfinite(value) or (value <= 0 if mapping == "G7-US-07" else not 0 <= value <= 100)):
                raise ValueError("BLS observation outside its valid domain")
            flags = [item.get("code") for item in row.get("footnotes", []) if item.get("code")]
            points[period] = {"period": period, "value": value,
                              "publisher_flag": " ".join(flags) or None}
        meta = metadata[mapping]
        first = int(meta["begin_year"]) * 12 + int(meta["begin_period"][1:]) - 1
        last = int(meta["end_year"]) * 12 + int(meta["end_period"][1:]) - 1
        expected = [f"{m // 12:04d}-{m % 12 + 1:02d}" for m in range(first, last + 1)]
        periods = sorted(points)
        if not periods or periods != expected:
            raise ValueError(f"BLS history does not cover the publisher metadata window: {mapping}")
        observations = [points[period] for period in periods]
        results[mapping] = {
            "mapping": mapping, "publisher_series": spec["id"], "source_url": ENDPOINT,
            "source_sha256": sha256(raw).hexdigest(), "source_windows": payload["source_windows"],
            "metadata_source_url": spec["metadata_url"], "metadata": meta,
            "unit": spec["unit"], "first": periods[0], "last": periods[-1],
            "valid_observations": sum(p["value"] is not None for p in observations),
            "publisher_nulls": sum(p["value"] is None for p in observations),
            "excluded_annual_averages": excluded_averages,
            "rights_status": "PENDING", "production_approval": "NOT_APPROVED",
            "observations": observations,
        }
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipt_directory", type=Path)
    parser.add_argument("new_evidence_directory", type=Path)
    args = parser.parse_args()
    args.new_evidence_directory.mkdir()
    metadata = {}
    excerpt_hashes = {}
    for mapping, spec in SERIES.items():
        metadata[mapping], excerpt = fetch_metadata(spec)
        (args.new_evidence_directory / f"{mapping}-metadata.tsv").write_bytes(excerpt)
        excerpt_hashes[mapping] = sha256(excerpt).hexdigest()
    raw, _ = capture_windows(
        [spec["id"] for spec in SERIES.values()], start=1913,
        end=max(int(row["end_year"]) for row in metadata.values()),
    )
    (args.new_evidence_directory / "bls-history.json").write_bytes(raw)
    results = parse_history(raw, metadata)
    for mapping, record in results.items():
        record.update(metadata_excerpt_sha256=excerpt_hashes[mapping],
                      metadata_evidence_scope="Publisher metadata header and selected record excerpt",
                      captured_at=datetime.now(UTC).isoformat())
        with (args.receipt_directory / f"{mapping}.json").open("x", encoding="utf-8") as output:
            json.dump(record, output, indent=2, allow_nan=False)
            output.write("\n")
        print(json.dumps({key: value for key, value in record.items() if key not in {"observations", "metadata", "source_windows"}}), flush=True)


if __name__ == "__main__":
    main()
