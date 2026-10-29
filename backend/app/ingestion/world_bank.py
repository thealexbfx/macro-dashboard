"""Strict, size-bounded XLSX reader for the three approved Pink Sheet columns.

No Excel engine, macros, formula evaluation, price conversion or missing-data filling.
The publication URL is pinned deliberately; a changed link needs review, not guessing.
"""

import math
import posixpath
import re
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from time import monotonic
from zipfile import BadZipFile, ZipFile

import requests

from backend.app.ingestion.contracts import Batch, Point, ProviderError, Series

URL = "https://thedocs.worldbank.org/en/doc/74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx"
PILOT = (
    Series(
        "wb_brent_monthly",
        "world_bank",
        "Crude oil, Brent",
        "Brent crude, monthly nominal price",
        "($/bbl)",
        "USD / barrel",
    ),
    Series(
        "wb_copper_monthly",
        "world_bank",
        "Copper",
        "Copper, monthly nominal price",
        "($/mt)",
        "USD / metric tonne",
    ),
    Series(
        "wb_iron_ore_monthly",
        "world_bank",
        "Iron ore, cfr spot",
        "Iron ore CFR spot, source-native monthly price",
        "($/dmtu)",
        "Source-labelled USD / dmtu; definition conflict requires review",
    ),
)
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
MAX_BYTES = 4 * 1024 * 1024
MAX_EXPANDED = 16 * 1024 * 1024
MISSING = {"", "...", "..", "\u2026", "na", "n/a"}


def xml(data):
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ProviderError("unsafe_xml")
    return ET.fromstring(data)


def rows(z, path, strings):
    data = z.read(path)
    xml_start = data.upper()
    if b"<!DOCTYPE" in xml_start or b"<!ENTITY" in xml_start:
        raise ProviderError("unsafe_xml")
    count = 0
    for _, elem in ET.iterparse(BytesIO(data), events=("end",)):
        if elem.tag != NS + "row":
            continue
        row = {}
        for c in elem.findall(NS + "c"):
            count += 1
            if count > 150000:
                raise ProviderError("too_many_cells")
            ref = c.get("r", "")
            col = re.sub(r"[0-9]", "", ref)
            value = c.find(NS + "v")
            if c.find(NS + "f") is not None:
                row[col] = (None, "formula")
            elif c.get("t") == "s" and value is not None:
                row[col] = (strings[int(value.text)], "text")
            elif c.get("t") == "inlineStr":
                row[col] = ("".join(c.find(NS + "is").itertext()), "text")
            else:
                row[col] = (value.text if value is not None else "", c.get("t", "n"))
        yield row
        elem.clear()


def parse_workbook(data, now=None):
    now = now or datetime.now(UTC)
    try:
        if len(data) > MAX_BYTES:
            raise ProviderError("download_too_large")
        with ZipFile(BytesIO(data)) as z:
            files = z.infolist()
            if len(files) > 100 or len({f.filename for f in files}) != len(files):
                raise ProviderError("invalid_archive")
            if sum(f.file_size for f in files) > MAX_EXPANDED:
                raise ProviderError("expanded_file_too_large")
            if any(f.file_size > 8 * 1024 * 1024 for f in files):
                raise ProviderError("archive_member_too_large")
            if any(f.flag_bits & 1 for f in files):
                raise ProviderError("encrypted_archive")
            strings = []
            if "xl/sharedStrings.xml" in z.namelist():
                strings = [
                    "".join(e.itertext())
                    for e in xml(z.read("xl/sharedStrings.xml")).findall(NS + "si")
                ]
                if len(strings) > 20000:
                    raise ProviderError("too_many_strings")
            sheets = xml(z.read("xl/workbook.xml")).find(NS + "sheets")
            matches = [s for s in sheets if s.get("name") == "Monthly Prices"]
            if len(matches) != 1:
                raise ProviderError("missing_monthly_sheet")
            relations = xml(z.read("xl/_rels/workbook.xml.rels"))
            targets = [
                r for r in relations if r.get("Id") == matches[0].get(REL + "id")
            ]
            if len(targets) != 1 or targets[0].get("TargetMode") == "External":
                raise ProviderError("invalid_sheet_target")
            path = posixpath.normpath(
                posixpath.join("xl", targets[0].get("Target", ""))
            )
            if not path.startswith("xl/worksheets/") or not path.endswith(".xml"):
                raise ProviderError("invalid_sheet_target")
            columns, points, dates, metadata, unit_checked = {}, [], [], {}, False
            for row in rows(z, path, strings):
                if not columns:
                    for spec in PILOT:
                        found = [
                            c
                            for c, (v, _) in row.items()
                            if str(v).strip() == spec.selector
                        ]
                        if len(found) > 1:
                            raise ProviderError("duplicate_header")
                        if found:
                            columns[spec.id] = found[0]
                    if columns and len(columns) != len(PILOT):
                        raise ProviderError("missing_pilot_header")
                    continue
                if not unit_checked:
                    for spec in PILOT:
                        raw = str(row.get(columns[spec.id], ("", ""))[0]).strip()
                        if raw != spec.source_unit:
                            raise ProviderError("unit_changed")
                    unit_checked = True
                    continue
                period, _ = row.get("A", ("", ""))
                if not re.fullmatch(r"[0-9]{4}M[0-9]{2}", str(period)):
                    # Footnotes are permitted, malformed dated rows are not.
                    if re.match(r"[0-9]{4}", str(period)):
                        raise ProviderError("invalid_period")
                    continue
                year, month = int(period[:4]), int(period[5:])
                if not 1960 <= year <= now.year or not 1 <= month <= 12:
                    raise ProviderError("invalid_period")
                native = f"{year:04d}-{month:02d}"
                if native > now.strftime("%Y-%m") or (dates and native <= dates[-1]):
                    raise ProviderError("duplicate_or_unordered_period")
                dates.append(native)
                if len(dates) > 1200:
                    raise ProviderError("history_limit")
                for spec in PILOT:
                    raw, kind = row.get(columns[spec.id], ("", ""))
                    if kind in {"formula", "e", "b"}:
                        raise ProviderError("invalid_cell")
                    if str(raw).strip().lower() in MISSING:
                        value, quality = None, "missing"
                    else:
                        value = float(raw)
                        if not math.isfinite(value) or value <= 0:
                            raise ProviderError("invalid_price")
                        quality = (
                            "unit_review"
                            if spec.id == "wb_iron_ore_monthly"
                            else "observed"
                        )
                    points.append(Point(spec.id, native, value, quality))
            if not unit_checked or len(dates) < 12:
                raise ProviderError("incomplete_history")
            for spec in PILOT:
                observed = [
                    p for p in points if p.dataset_id == spec.id and p.value is not None
                ]
                if not observed:
                    raise ProviderError("empty_series")
                metadata[spec.id] = {
                    "source_unit": spec.source_unit,
                    "first_period": dates[0],
                    "last_period": dates[-1],
                    "first_observed": observed[0].period,
                    "last_observed": observed[-1].period,
                    "non_missing": len(observed),
                    "missing": len(dates) - len(observed),
                    "source_column": columns[spec.id],
                    "sheet": "Monthly Prices",
                    "coverage_gaps": len(dates)
                    != (
                        (int(dates[-1][:4]) - int(dates[0][:4])) * 12
                        + int(dates[-1][5:])
                        - int(dates[0][5:])
                        + 1
                    ),
                    "stale": (
                        now.year * 12
                        + now.month
                        - int(observed[-1].period[:4]) * 12
                        - int(observed[-1].period[5:])
                    )
                    > 3,
                    "warnings": [
                        "Source column says $/dmtu; Description defines recent spot in USD/dry ton. No conversion applied; units require review."
                    ]
                    if spec.id == "wb_iron_ore_monthly"
                    else [],
                    "rights": "Unreviewed redistribution and AI use; source supplier exceptions may apply.",
                }
        return Batch(
            tuple(points), metadata, sha256(data).hexdigest(), URL, now, len(data)
        )
    except ProviderError:
        raise
    except (
        BadZipFile,
        ET.ParseError,
        KeyError,
        ValueError,
        IndexError,
        TypeError,
        AttributeError,
        OSError,
    ) as exc:
        raise ProviderError("malformed_workbook") from exc


class WorldBank:
    id = "world_bank"
    series = PILOT

    def __init__(self, session=None, now_fn=None, cancel_event=None):
        self.cancel_event = cancel_event
        self.session = session or requests.Session()
        self.now_fn = now_fn or (lambda: datetime.now(UTC))
        self._cached = None
        self._expires = 0

    def _check_cancelled(self):
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise ProviderError("cancelled")

    def fetch(self):
        self._check_cancelled()
        # Share one small download across bounded backfill slices; never serve stale on outage.
        if self._cached and monotonic() < self._expires:
            return self._cached
        start = monotonic()
        try:
            with self.session.get(
                URL, stream=True, timeout=(5, 10), allow_redirects=False
            ) as response:
                if response.status_code != 200:
                    retry = response.headers.get("Retry-After", "0")
                    raise ProviderError(
                        f"http_{response.status_code}",
                        int(retry) if retry.isdigit() else 0,
                    )
                data = bytearray()
                for chunk in response.iter_content(65536):
                    self._check_cancelled()
                    if len(data) + len(chunk) > MAX_BYTES:
                        raise ProviderError("download_too_large")
                    if monotonic() - start > 25:
                        raise ProviderError("download_deadline")
                    data.extend(chunk)
            self._check_cancelled()
            batch = parse_workbook(bytes(data), self.now_fn())
        except requests.RequestException as exc:
            raise ProviderError("provider_unavailable") from exc
        self._cached, self._expires = batch, monotonic() + 300
        return batch
