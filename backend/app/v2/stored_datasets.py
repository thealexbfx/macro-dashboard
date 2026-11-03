"""Read-only, deny-by-default bridge from normalized storage to website research.

Presentation registration is a separate code review from ingestion registration.
No pilot is registered here; this module cannot grant or change database rights.
Discovery and AI deliberately retain the existing legacy-only registry.
"""

import json
import math
import re
import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import date, datetime
from types import MappingProxyType

from backend.app.v2.definitions import Spec

HISTORY_FLOOR = date(1990, 1, 1)


@dataclass(frozen=True)
class PublicStoredDefinition:
    spec: Spec
    attribution: tuple[str, ...]
    license_url: str
    benchmark: str
    source_unit: str

    def __post_init__(self):
        if (
            self.spec.frequency != "monthly"
            or not self.attribution
            or not self.benchmark
            or not self.source_unit
            or not self.license_url.startswith("https://")
            or not self.spec.source_url.startswith("https://")
            or self.spec.category != "Commodities"
        ):
            raise ValueError("Reviewed monthly commodity definition required")


# Intentionally empty: no real commodity has public/AI approval.
PUBLIC_STORED_DEFINITIONS = MappingProxyType({})


class StoredDatasetReader:
    def __init__(self, path, dataset_class, definitions=None, today_fn=date.today):
        self.path = path
        self.dataset_class = dataset_class
        self.definitions = dict(
            PUBLIC_STORED_DEFINITIONS if definitions is None else definitions
        )
        if len(self.definitions) > 32 or any(
            k != d.spec.id for k, d in self.definitions.items()
        ):
            raise ValueError("Invalid bounded presentation registry")
        self.today_fn = today_fn

    def get(self, key, preview=False):
        definition = self.definitions.get(key)
        if definition is None:
            raise ValueError("Unknown dataset ID")
        try:
            # No Store.connection(): reads must not create a DB or migrate a schema.
            with closing(
                sqlite3.connect(
                    self.path.resolve().as_uri() + "?mode=ro", uri=True, timeout=2
                )
            ) as db:
                db.row_factory = sqlite3.Row
                db.execute("PRAGMA query_only=ON")
                db.execute("BEGIN")
                row = db.execute(
                    "SELECT * FROM ingest_datasets WHERE id=? AND public_display=1 AND rights_state='approved'",
                    (key,),
                ).fetchone()
                if row is None:
                    raise ValueError("Unknown dataset ID")
                job = db.execute(
                    "SELECT * FROM ingest_jobs WHERE provider=?", (row["provider"],)
                ).fetchone()
                if (
                    job is None
                    or job["cursor"] is not None
                    or not job["last_success"]
                    or len(row["metadata"]) > 65536
                ):
                    raise ValueError("Unknown dataset ID")
                meta = json.loads(row["metadata"])
                spec = definition.spec
                if not isinstance(meta, dict):
                    raise TypeError("Unknown dataset ID")
                validation = meta.get("validation", {})
                if not isinstance(validation, dict):
                    raise TypeError("Unknown dataset ID")
                if (
                    row["provider"] != spec.provider
                    or meta.get("provider") != spec.provider
                    or meta.get("selector") != spec.provider_id
                    or meta.get("frequency") != "monthly"
                    or meta.get("units") != spec.units
                    or meta.get("source_unit") != definition.source_unit
                    or validation.get("source_unit") != definition.source_unit
                    or meta.get("source_url") != spec.source_url
                    or validation.get("coverage_gaps") is not False
                    or not re.fullmatch("[0-9a-f]{64}", meta.get("source_hash", ""))
                    or meta["source_hash"] != job["source_hash"]
                ):
                    raise ValueError("Unknown dataset ID")
                checked = datetime.fromisoformat(meta["source_checked_at"])
                if checked.tzinfo is None or checked.date() > self.today_fn():
                    raise ValueError("Unknown dataset ID")
                rows = db.execute(
                    "SELECT period,value,quality,revision FROM ingest_observations WHERE dataset_id=? ORDER BY period LIMIT 1201",
                    (key,),
                ).fetchall()
            if not rows or len(rows) > 1200:
                raise ValueError("Unknown dataset ID")
            if rows[0]["period"] != validation.get("first_period") or rows[-1][
                "period"
            ] != validation.get("last_period"):
                raise ValueError("Unknown dataset ID")
            first, last = rows[0]["period"], rows[-1]["period"]
            expected = (
                (int(last[:4]) - int(first[:4])) * 12
                + int(last[5:])
                - int(first[5:])
                + 1
            )
            if len(rows) != expected:
                raise ValueError("Unknown dataset ID")
            observations = []
            for point in rows:
                period = point["period"]
                if not re.fullmatch(r"[0-9]{4}-[0-9]{2}", period):
                    raise ValueError("Unknown dataset ID")
                reference = date.fromisoformat(period + "-01")
                value = point["value"]
                if (
                    reference > self.today_fn()
                    or point["quality"] not in {"observed", "missing"}
                    or (value is None) != (point["quality"] == "missing")
                    or value is not None
                    and (not math.isfinite(value) or value <= 0)
                ):
                    raise ValueError("Unknown dataset ID")
                if reference >= HISTORY_FLOOR:
                    observations.append({"date": reference.isoformat(), "value": value})
            valid = [o for o in observations if o["value"] is not None]
            if not valid:
                raise ValueError("Unknown dataset ID")
            latest = valid[-1]
            months = (
                (self.today_fn().year - int(latest["date"][:4])) * 12
                + self.today_fn().month
                - int(latest["date"][5:7])
            )
            stale = months > 3 or bool(job["error_code"])
            warnings = []
            if stale:
                warnings.append(
                    "Stored reference is stale or the last ingestion check failed; inspect source timestamps."
                )
            if any(o["value"] is None for o in observations):
                warnings.append(
                    "Missing source observations retained as null; no filling applied."
                )
            # Copy only reviewed definition and explicit safe provenance, never arbitrary metadata.
            return self.dataset_class(
                **asdict(spec),
                status="stale" if stale else "ok",
                observations=observations[-40:] if preview else observations,
                latest_value=latest["value"],
                latest_observation_date=latest["date"],
                coverage_start=observations[0]["date"],
                coverage_end=observations[-1]["date"],
                retrieved_at=checked.isoformat(),
                quality_warnings=warnings,
                revision_count=sum(max(0, r["revision"] - 1) for r in rows),
                verification={
                    "status": "Source validated",
                    "limitation": "Structural source validation; no independent price or publication-vintage verification.",
                },
                release_metadata={
                    "freshness_assessment": "Monthly reference age and last ingestion outcome; reference months are not release dates."
                },
                provider_metadata={"source_hash": meta["source_hash"]},
                stored_provenance={
                    "attribution": list(definition.attribution),
                    "license_url": definition.license_url,
                    "benchmark": definition.benchmark,
                    "source_unit": definition.source_unit,
                    "stored_start": rows[0]["period"],
                    "stored_end": rows[-1]["period"],
                    "reference_convention": "First day labels the economic month, not publication/trading time.",
                    "ai_allowed": False,
                },
                message="Stored monthly benchmark observations; latest captured revisions. Website history begins in 1990.",
            )
        except (
            sqlite3.Error,
            OSError,
            KeyError,
            TypeError,
            ValueError,
            OverflowError,
        ) as exc:
            raise ValueError("Unknown dataset ID") from exc

    def catalogue(self):
        data = []
        for key in self.definitions:
            try:
                data.append(self.get(key, preview=True))
            except ValueError:
                continue
        return data


class PermissionedDataService:
    def __init__(self, legacy, reader, legacy_specs):
        self.legacy, self.reader, self.legacy_specs = legacy, reader, legacy_specs
        if set(reader.definitions) & set(legacy_specs()):
            raise ValueError("Stored IDs must not shadow existing datasets")

    def __getattr__(self, name):
        return getattr(self.legacy, name)

    def resolve_spec(self, key):
        if key in self.legacy_specs():
            return self.legacy_specs()[key]
        self.reader.get(
            key, preview=True
        )  # Permission and quality check on every request.
        return self.reader.definitions[key].spec

    def get(self, key):
        if key in self.legacy_specs():
            return self.legacy.get(key)
        return self.reader.get(key)

    def catalogue(self):
        return self.legacy.catalogue() + self.reader.catalogue()
