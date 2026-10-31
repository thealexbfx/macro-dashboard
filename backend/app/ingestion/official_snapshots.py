"""Bounded official downloads and immutable native snapshots for explicit ingestion.

No startup/scheduler hooks. A snapshot freezes one complete source response before
partitioning, so changing latest-only APIs cannot mix vintages between pages.
"""

import json
import math
import ssl
import time
from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from backend.app.ingestion.contracts import ProviderError
from backend.app.ingestion.native import Observation, digest, native_period
from backend.app.ingestion.partition_contracts import Page

HOSTS = frozenset(
    {
        "ec.europa.eu",
        "www.ons.gov.uk",
        "api.ons.gov.uk",
        "data-api.ecb.europa.eu",
        "sdmx.oecd.org",
        "www.bankofengland.co.uk",
        "www.stat-search.boj.or.jp",
        "dashboard.e-stat.go.jp",
        "assets.publishing.service.gov.uk",
        "d9-wret.s3.us-west-2.amazonaws.com",
        "www.eia.gov",
        "api.eia.gov",
        "api.bls.gov",
        "api.census.gov",
        "www.census.gov",
        "www.bea.gov",
        "apps.bea.gov",
        "www.federalreserve.gov",
        "markets.newyorkfed.org",
        "www.stats.gov.cn",
        "www.jodidata.org",
        "comtradeapi.un.org",
        "api.uktradeinfo.com",
        "www.gov.uk",
        "www.usgs.gov",
    }
)
MAX_BYTES = 8 * 1024 * 1024
MAX_POINTS = 50000


def safe_url(url):
    part = urlsplit(url)
    if (
        part.scheme != "https"
        or part.hostname not in HOSTS
        or part.username
        or part.password
        or part.port not in (None, 443)
        or any(
            key.casefold() in {"api_key", "apikey", "token", "access_token", "password"}
            for key, _ in parse_qsl(part.query)
        )
    ):
        raise ProviderError("unapproved_official_host")
    return url


class OfficialRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(url, *, timeout=25, maximum=MAX_BYTES, opener=None, payload=None):
    """TLS verification stays enabled; 401/403 are never bypassed or retried."""
    safe_url(url)
    if not 1 <= maximum <= MAX_BYTES or not 1 <= timeout <= 30:
        raise ValueError("Unsafe download bounds")
    if opener is None:
        import certifi

        opener = build_opener(
            OfficialRedirects(),
            HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where())),
        )
    started = time.monotonic()
    try:
        if payload is not None and (
            urlsplit(url).hostname != "api.bls.gov" or len(payload) > 65536
        ):
            raise ValueError("Only bounded BLS query POST is supported")
        request = Request(
            url,
            data=payload,
            headers={
                "User-Agent": "MacroLensResearch/2.0 official-data-validation",
                "Accept": "application/json,text/csv,application/octet-stream,*/*",
                "Content-Type": "application/json",
            },
        )
        with opener.open(request, timeout=timeout) as response:
            safe_url(response.geturl())
            if int(response.headers.get("Content-Length", 0)) > maximum:
                raise ProviderError("response_size_limit")
            chunks, count = [], 0
            while chunk := response.read(min(65536, maximum + 1 - count)):
                count += len(chunk)
                if count > maximum or time.monotonic() - started > timeout:
                    raise ProviderError("response_budget")
                chunks.append(chunk)
            return b"".join(chunks), {
                "url": response.geturl(),
                "content_type": response.headers.get("Content-Type", ""),
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
            }
    except HTTPError as exc:
        raise ProviderError(f"http_{exc.code}") from None
    except (URLError, TimeoutError, OSError):
        raise ProviderError("network_or_tls_failure") from None


def freeze(path, definition, points, raw, source_url, metadata=None):
    """Content-addressed snapshot; no source observations are committed to git."""
    points = tuple(points)
    if not points or len(points) > MAX_POINTS:
        raise ProviderError("empty_or_oversized_history")
    seen = set()
    checked_at = datetime.now(UTC)
    for point in points:
        period = point.validated(definition, checked_at)
        if period.key in seen or (
            point.value is not None and not math.isfinite(point.value)
        ):
            raise ProviderError("duplicate_or_nonfinite_observation")
        seen.add(period.key)
    raw_hash = sha256(raw).hexdigest()
    body = {
        "definition_hash": definition.fingerprint,
        "source_hash": raw_hash,
        "source_url": safe_url(source_url),
        "checked_at": checked_at.isoformat(),
        "metadata": metadata or {},
        "points": [asdict(p) for p in points],
    }
    payload = json.dumps(body, sort_keys=True, default=str).encode()
    key = sha256(payload).hexdigest()
    target = Path(path) / f"{key}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(payload)
        temporary.replace(target)
    return target, key


class SnapshotAdapter:
    """Each page re-verifies the immutable artifact and returns source records only."""

    def __init__(self, path, expected_hash):
        self.path, self.expected_hash = Path(path), expected_hash

    def fetch(self, definition, window, cursor, bounds):
        if self.path.stat().st_size > 16 * 1024 * 1024:
            raise ProviderError("snapshot_size_limit")
        raw = self.path.read_bytes()
        if sha256(raw).hexdigest() != self.expected_hash:
            raise ProviderError("snapshot_changed")
        data = json.loads(raw)
        if data["definition_hash"] != definition.fingerprint:
            raise ProviderError("definition_changed")
        records = []
        for row in data["points"]:
            row["flags"] = tuple(row["flags"])
            if row.get("release_at"):
                row["release_at"] = datetime.fromisoformat(row["release_at"])
            point = Observation(**row)
            if (
                window.start
                <= native_period(point.period, definition, point.event_id).start
                <= window.end
            ):
                records.append(point)
        records.sort(
            key=lambda p: (
                native_period(p.period, definition, p.event_id).start,
                p.period,
                p.event_id or "",
            )
        )
        offset = int(cursor or 0)
        if offset < 0 or offset > len(records):
            raise ProviderError("invalid_snapshot_cursor")
        selected = tuple(records[offset : offset + bounds.records])
        if (
            len(json.dumps([asdict(p) for p in selected], default=str).encode())
            > bounds.response_bytes
        ):
            raise ProviderError("snapshot_page_limit")
        following = (
            str(offset + len(selected))
            if offset + len(selected) < len(records)
            else None
        )
        return Page(
            selected,
            digest([asdict(p) for p in selected]),
            self.expected_hash,
            data["source_url"],
            datetime.fromisoformat(data["checked_at"]),
            following,
        )
