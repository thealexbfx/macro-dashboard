"""Read-only native publication boundary. No real registrations or rights grants."""

import json
import math
import re
import sqlite3
from contextlib import closing, contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from types import MappingProxyType

from backend.app.catalog.manifest import LEGACY_PUBLIC_SOURCES
from backend.app.ingestion.native import Definition, digest, instant, native_period


@dataclass(frozen=True)
class NativePublication:
    definition: Definition
    name: str
    category: str
    region: str
    source_url: str
    license_url: str
    attribution: tuple[str, ...]
    rights_evidence: str

    def __post_init__(self):
        if (
            not self.name
            or not self.attribution
            or not self.rights_evidence
            or any(
                not u.startswith("https://")
                for u in (self.source_url, self.license_url)
            )
        ):
            raise ValueError("Reviewed source and redistribution evidence required")


# Real datasets remain unreviewed/private. Only disposable tests inject approvals.
NATIVE_PUBLICATIONS = MappingProxyType({})


class RangeLimit(ValueError):
    pass


class NativeReader:
    def __init__(self, path, publications=None, now_fn=None):
        self.path = path
        self.publications = dict(
            NATIVE_PUBLICATIONS if publications is None else publications
        )
        self.now = now_fn or (lambda: datetime.now(UTC))
        if set(self.publications) & (
            set(LEGACY_PUBLIC_SOURCES)
            | {"wb_brent_monthly", "wb_copper_monthly", "wb_iron_ore_monthly"}
        ):
            raise ValueError("Protected dataset cannot be shadowed")
        if len(self.publications) > 400 or any(
            k != p.definition.id for k, p in self.publications.items()
        ):
            raise ValueError("Invalid presentation registry")

    @contextmanager
    def connection(self):
        try:
            with closing(
                sqlite3.connect(
                    self.path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2
                )
            ) as db:
                db.row_factory = sqlite3.Row
                db.execute("PRAGMA query_only=ON")
                db.execute("BEGIN")
                # A query budget, not a cross-request permissions cache.
                steps = [0]

                def progress():
                    steps[0] += 1000
                    return int(steps[0] > 4000000)

                db.set_progress_handler(progress, 1000)
                yield db
        except (
            sqlite3.Error,
            OSError,
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
        ) as exc:
            if isinstance(exc, RangeLimit):
                raise
            raise ValueError("Unknown dataset ID") from exc

    def _permission(self, db, key):
        publication = self.publications.get(key)
        if publication is None:
            raise ValueError("Unknown dataset ID")
        definition = publication.definition
        row = db.execute(
            "SELECT * FROM norm_datasets WHERE id=? AND public_display=1 AND rights_state='permitted'",
            (key,),
        ).fetchone()
        review = db.execute(
            "SELECT * FROM catalog_scope_reviews WHERE dataset_id=? AND scope='public_display' AND approved=1 AND rights_state='permitted'",
            (key,),
        ).fetchone()
        if (
            not row
            or not review
            or review["evidence"] != publication.rights_evidence
            or not review["reviewed_at"]
            or review["definition_hash"] != definition.fingerprint
            or row["definition_hash"] != definition.fingerprint
            or row["provider"] != definition.provider
            or len(row["definition"]) > 131072
        ):
            raise ValueError("Unknown dataset ID")
        stored = json.loads(row["definition"])
        for field in ("releases", "holidays", "evidence"):
            stored["calendar"].pop(field)
        if digest(stored) != definition.fingerprint:
            raise ValueError("Unknown dataset ID")
        active = db.execute(
            "SELECT g.* FROM norm_dataset_state s JOIN norm_generations g ON g.id=s.active_generation AND g.dataset_id=s.dataset_id WHERE s.dataset_id=?",
            (key,),
        ).fetchone()
        self._receipt(db, definition, active, verify_hash=False)
        return publication, active

    def _receipt(self, db, definition, generation, *, verify_hash=True):
        if (
            not generation
            or generation["state"] != "complete"
            or generation["definition_hash"] != definition.fingerprint
            or not re.fullmatch(r"[0-9a-f]{64}", generation["snapshot_hash"] or "")
        ):
            raise ValueError("Unknown dataset ID")
        receipt = db.execute(
            "SELECT * FROM catalog_dataset_completeness WHERE dataset_id=? AND batch_id=?",
            (definition.id, generation["id"]),
        ).fetchone()
        if (
            not receipt
            or receipt["state"] != "complete"
            or receipt["cursor"] is not None
            or receipt["quality_passed"] != 1
            or receipt["definition_hash"] != definition.fingerprint
            or not re.fullmatch(r"[0-9a-f]{64}", receipt["source_hash"])
        ):
            raise ValueError("Unknown dataset ID")
        if db.execute(
            "SELECT 1 FROM norm_partitions WHERE generation_id=? AND (state!='complete' OR cursor IS NOT NULL) LIMIT 1",
            (generation["id"],),
        ).fetchone():
            raise ValueError("Unknown dataset ID")
        if verify_hash:
            pages = db.execute(
                "SELECT p.start_date,p.end_date,x.request_hash,x.content_hash,x.next_hash FROM norm_pages x JOIN norm_partitions p ON p.id=x.partition_id WHERE p.generation_id=? ORDER BY p.start_date,x.request_hash LIMIT 2049",
                (generation["id"],),
            ).fetchall()
            count = db.execute(
                "SELECT sum(page_count) FROM norm_partitions WHERE generation_id=?",
                (generation["id"],),
            ).fetchone()[0]
            if (
                not pages
                or len(pages) > 2048
                or count != len(pages)
                or digest(
                    {
                        "snapshot": generation["snapshot_hash"],
                        "definition": definition.fingerprint,
                        "pages": [tuple(r) for r in pages],
                    }
                )
                != receipt["source_hash"]
            ):
                raise ValueError("Unknown dataset ID")

    def _metadata(self, publication):
        d = publication.definition
        allowed = ["level", "indexed", "standardized"]
        if d.frequency not in {"event", "irregular"}:
            allowed += ["percent", "yoy"]
        if d.frequency == "monthly":
            allowed.append("mom")
        if d.units.lower().startswith("percent"):
            allowed.append("pp")
        return {
            "id": d.id,
            "name": publication.name,
            "provider_id": d.selector,
            "provider": d.provider,
            "source": d.provider,
            "category": publication.category,
            "region": publication.region,
            "frequency": d.frequency,
            "units": d.units,
            "seasonal_adjustment": d.adjustment,
            "representation": "native",
            "original_transformation": "Native source values",
            "source_url": publication.source_url,
            "allowed_transformations": allowed,
            "status": "unavailable",
            "latest_value": None,
            "latest_observation_date": None,
            "coverage_start": None,
            "coverage_end": None,
            "retrieved_at": None,
            "publication_date": None,
            "message": "Load observations on demand",
            "observations": [],
            "change": None,
            "change_units": None,
            "previous_observation_date": None,
            "native_storage": True,
            "native_calendar": {
                k: v
                for k, v in asdict(d.calendar).items()
                if k not in {"releases", "holidays", "evidence"}
            },
            "stored_provenance": {
                "attribution": list(publication.attribution),
                "license_url": publication.license_url,
                "benchmark": d.selector,
                "source_unit": d.units,
                "stored_start": "",
                "stored_end": "",
                "reference_convention": "Native reference periods; dates are not release dates",
                "ai_allowed": False,
            },
        }

    def metadata(self, key):
        if key not in self.publications:
            raise ValueError("Unknown dataset ID")
        with self.connection() as db:
            publication, _active = self._permission(db, key)
            return self._metadata(publication)

    def catalogue(self):
        if not self.publications:
            return []
        rows = []
        with self.connection() as db:
            for key in self.publications:
                try:
                    publication, _ = self._permission(db, key)
                    rows.append(self._metadata(publication))
                except (ValueError, TypeError, KeyError):
                    continue
        return rows

    def observations(self, key, start, end, *, limit=1000, offset=0, preview=False):
        if key not in self.publications:
            raise ValueError("Unknown dataset ID")
        if (
            start > end
            or not 1 <= limit <= 2000
            or not 0 <= offset <= 100000
            or preview
            and offset
        ):
            raise ValueError("Invalid observation range")
        with self.connection() as db:
            publication, _active = self._permission(db, key)
            d = publication.definition
            event = d.frequency in {"event", "irregular"}
            low = start - timedelta(days=1) if event and start > date.min else start
            high = end + timedelta(days=1) if event else end
            clause = ""
            args = [key, low.isoformat(), high.isoformat()]
            if event:
                clause = " AND json_extract(payload,'$.event_at')>=? AND json_extract(payload,'$.event_at')<?"
                args += [
                    start.isoformat() + "T00:00:00+00:00",
                    (end + timedelta(days=1)).isoformat() + "T00:00:00+00:00",
                ]
            order = "DESC" if preview else "ASC"
            rows = db.execute(
                f"SELECT * FROM norm_observations WHERE dataset_id=? AND reference_start BETWEEN ? AND ?{clause} ORDER BY reference_start {order},period_key {order} LIMIT ? OFFSET ?",
                (*args, limit + 1, offset),
            ).fetchall()
            more, rows = len(rows) > limit, rows[:limit]
            if preview:
                rows.reverse()
            proofs, observations = {}, []
            for row in rows:
                generation_id = row["generation_id"]
                if generation_id not in proofs:
                    generation = db.execute(
                        "SELECT * FROM norm_generations WHERE id=? AND dataset_id=?",
                        (generation_id, key),
                    ).fetchone()
                    self._receipt(db, d, generation)
                    proofs[generation_id] = generation
                stage = db.execute(
                    "SELECT s.*,p.start_date,p.end_date FROM norm_staged s JOIN norm_partitions p ON p.id=s.partition_id WHERE s.generation_id=? AND s.period_key=? AND p.generation_id=s.generation_id",
                    (generation_id, row["period_key"]),
                ).fetchone()
                if (
                    not stage
                    or any(
                        stage[k] != row[k]
                        for k in (
                            "payload",
                            "value",
                            "artifact_hash",
                            "checked_at",
                            "reference_start",
                            "reference_end",
                        )
                    )
                    or not stage["start_date"]
                    <= row["reference_start"]
                    <= stage["end_date"]
                ):
                    raise ValueError("Unknown dataset ID")
                if not db.execute(
                    "SELECT 1 FROM norm_pages WHERE partition_id=? AND content_hash=?",
                    (stage["partition_id"], row["artifact_hash"]),
                ).fetchone():
                    raise ValueError("Unknown dataset ID")
                if len(row["payload"]) > 16384:
                    raise ValueError("Unknown dataset ID")
                payload = json.loads(row["payload"])
                value = row["value"]
                flags = payload["flags"]
                checked = instant(datetime.fromisoformat(row["checked_at"]))
                period = native_period(
                    payload["event_at"] if event else row["period_key"],
                    d,
                    payload.get("event_id"),
                )
                if (
                    checked > instant(self.now())
                    or period.key != row["period_key"]
                    or str(period.start) != row["reference_start"]
                    or str(period.end) != row["reference_end"]
                    or payload["reference_start"] != row["reference_start"]
                    or payload["reference_end"] != row["reference_end"]
                    or payload["source_url"] != publication.source_url
                    or payload["definition_hash"] != d.fingerprint
                    or payload["units"] != d.units
                    or payload["frequency"] != d.frequency
                    or payload["adjustment"] != d.adjustment
                    or payload["calendar_id"] != d.calendar.id
                    or payload["value"] != value
                    or payload["missing"] is not (value is None)
                    or value is not None
                    and (isinstance(payload["value"], bool) or not math.isfinite(value))
                    or not isinstance(flags, list)
                    or len(flags) > 32
                    or any(
                        not isinstance(f, str)
                        or len(f) > 200
                        or f.casefold().split("=", 1)[-1]
                        in {"unit_review", "partial_period", "quarantined"}
                        for f in flags
                    )
                ):
                    raise ValueError("Unknown dataset ID")
                observations.append(
                    {
                        "date": period.event_at if event else str(period.start),
                        "value": value,
                        "key": period.key,
                        "native_label": payload["period_label"],
                        "period_start": str(period.start),
                        "period_end": str(period.end),
                        "event_id": payload.get("event_id"),
                        "source_flags": flags,
                        "release_at": payload.get("release_at"),
                        "revision": row["revision"],
                    }
                )
            metadata = self._metadata(publication)
            valid = [r for r in observations if r["value"] is not None]
            checked_at = max((r["checked_at"] for r in rows), default=None)
            pending = db.execute(
                "SELECT 1 FROM norm_generations WHERE dataset_id=? AND state='staging' LIMIT 1",
                (key,),
            ).fetchone()
            # Conservative fallback when a reviewed source release calendar is absent.
            days = {
                "daily": 7,
                "weekly": 21,
                "monthly": 120,
                "quarterly": 240,
                "annual": 800,
            }.get(d.frequency)
            stale = (
                bool(pending)
                or not checked_at
                or (
                    instant(self.now()) - instant(datetime.fromisoformat(checked_at))
                ).days
                > 7
            )
            if valid and days is not None:
                stale |= (
                    self.now().date() - date.fromisoformat(valid[-1]["period_end"])
                ).days > days
            metadata.update(
                observations=observations,
                status="stale" if stale else "ok",
                retrieved_at=checked_at,
                latest_value=valid[-1]["value"] if valid else None,
                latest_observation_date=valid[-1]["date"] if valid else None,
                latest_native_label=valid[-1]["native_label"] if valid else None,
                coverage_start=observations[0]["date"] if observations else None,
                coverage_end=observations[-1]["date"] if observations else None,
                quality_warnings=[
                    "Last-good captured observations; source/retrieval freshness requires attention."
                ]
                if stale
                else [],
                message="Native source records; no interpolation or frequency conversion.",
            )
            return {
                "dataset": metadata,
                "offset": offset,
                "limit": limit,
                "next_offset": offset + limit if more and not preview else None,
                "has_more": more,
                "scope": "UTC event instants"
                if event
                else "Native reference-period start dates",
            }
