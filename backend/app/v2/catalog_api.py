"""Bounded public metadata/range reads. No registration, ingestion or rights writes."""

import json
from dataclasses import asdict
from datetime import date

from backend.app.catalog.manifest import Manifest
from backend.app.v2.definitions import SPECS
from backend.app.v2.integrity import assess_freshness


class PublicCatalog:
    def __init__(self, legacy, stored, native):
        self.legacy, self.stored, self.native = legacy, stored, native
        self.manifest = Manifest.load()

    def metadata(self, key):
        if key in SPECS:
            return {
                "catalog_evidence": self.manifest.get(key)["rights"],
                **asdict(SPECS[key]),
                "observations": [],
                "status": "unavailable",
                "message": "Load observations on demand",
                "latest_value": None,
                "latest_observation_date": None,
                "change": None,
                "change_units": None,
                "previous_observation_date": None,
                "coverage_start": None,
                "coverage_end": None,
                "retrieved_at": None,
                "publication_date": None,
            }
        if key in self.native.publications:
            return self.native.metadata(key)
        # The separately reviewed legacy commodity bridge retains its existing gates.
        d = self.stored.get(key)
        return d.model_dump(exclude={"observations"}) | {"observations": []}

    def page(
        self,
        *,
        query="",
        region="",
        category="",
        provider="",
        frequency="",
        offset=0,
        limit=20,
        ids=None,
    ):
        if (
            not 1 <= limit <= 100
            or not 0 <= offset <= 100000
            or len(query) > 200
            or ids is not None
            and len(ids) > 400
        ):
            raise ValueError("Invalid catalog page")
        rows = [self.metadata(k) for k in SPECS]
        rows.extend(self.native.catalogue())
        # No private/planning manifest rows enter counts, facets or search results.
        facets = {
            field: sorted({r.get(field) or "" for r in rows})
            for field in ("region", "category", "provider", "frequency")
        }
        rows = [
            r
            for r in rows
            if (ids is None or r["id"] in ids)
            and all(
                not value or r.get(field) == value
                for field, value in (
                    ("region", region),
                    ("category", category),
                    ("provider", provider),
                    ("frequency", frequency),
                )
            )
            and query.casefold()
            in " ".join(
                str(r.get(f, ""))
                for f in ("id", "name", "provider_id", "source", "region", "category")
            ).casefold()
        ]
        rows.sort(key=lambda r: (r["name"].casefold(), r["id"]))
        return {
            "items": rows[offset : offset + limit],
            "total": len(rows),
            "offset": offset,
            "limit": limit,
            "next_offset": offset + limit if offset + limit < len(rows) else None,
            "facets": facets,
        }

    def observations(self, key, start, end, *, limit=1000, offset=0, preview=False):
        if (
            start > end
            or end >= self.legacy.today_fn()
            or not 1 <= limit <= 2000
            or not 0 <= offset <= 100000
            or preview
            and offset
        ):
            raise ValueError("Choose a completed bounded date range")
        if key in self.native.publications:
            return self.native.observations(
                key, start, end, limit=limit, offset=offset, preview=preview
            )
        if key not in SPECS:
            d = self.stored.get(key).model_dump()
            points = [
                o for o in d.pop("observations") if str(start) <= o["date"] <= str(end)
            ]
            more = len(points) > offset + limit
            points = points[-limit:] if preview else points[offset : offset + limit]
        else:
            # Only one requested legacy source may refresh. Metadata listing never fetches providers.
            with self.legacy.store.connection() as db:
                cached = db.execute(
                    "SELECT next_due FROM source_cache WHERE id=?", (key,)
                ).fetchone()
            if cached is None or cached["next_due"] <= self.legacy.now_fn().isoformat():
                self.legacy.get(key)
            order = "DESC" if preview else "ASC"
            with self.legacy.store.connection() as db:
                meta = db.execute(
                    "SELECT json_remove(payload,'$.observations') FROM source_cache WHERE id=?",
                    (key,),
                ).fetchone()
                if not meta:
                    raise RuntimeError("Source unavailable; retry shortly")
                d = json.loads(meta[0])
                points = [
                    json.loads(r[0])
                    for r in db.execute(
                        f"SELECT j.value FROM source_cache c,json_each(c.payload,'$.observations') j WHERE c.id=? AND json_extract(j.value,'$.date') BETWEEN ? AND ? ORDER BY json_extract(j.value,'$.date') {order} LIMIT ? OFFSET ?",
                        (key, str(start), str(end), limit + 1, offset),
                    )
                ]
            more, points = len(points) > limit, points[:limit]
            if preview:
                points.reverse()
            if d.get("latest_observation_date") and d["status"] == "ok":
                stale, reason, _ = assess_freshness(
                    SPECS[key],
                    date.fromisoformat(d["latest_observation_date"]),
                    self.legacy.today_fn(),
                )
                if stale:
                    d.update(status="stale", message=reason)
        d["observations"] = points
        return {
            "dataset": d,
            "offset": offset,
            "limit": limit,
            "has_more": more,
            "next_offset": offset + limit if more and not preview else None,
            "scope": "Native source reference dates; no filling",
        }
