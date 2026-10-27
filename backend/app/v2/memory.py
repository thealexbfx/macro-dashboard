"""Persistent identities and material changes. Scan times never create new events."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256

from backend.app.v2.state import dumps

ARRAYS = {
    "reference_movements",
    "paired_observations",
    "historical_divergences",
    "latest_standardized_changes",
}


def evidence_hash(f):
    return sha256(
        dumps(
            {
                "type": f["type"],
                "evidence": f["evidence"],
                "configuration": f["configuration"],
            }
        ).encode()
    ).hexdigest()


def material_change(previous, current, was_archived=False):
    if previous.get("methodology_version") != current.get("methodology_version"):
        return "The documented discovery methodology changed"
    if previous["definition_hash"] != current["definition_hash"]:
        return "Dataset definition changed"
    if previous["type"] != current["type"]:
        return "A different relationship pattern now qualifies"
    if set(current.get("related_signals", [])) - set(
        previous.get("related_signals", [])
    ):
        return "A new related relationship is worth examining"
    if current["horizon_observations"] != previous["horizon_observations"] and current[
        "horizon_observations"
    ] not in {
        a["horizon_observations"] for a in previous.get("alternative_timeframes", [])
    }:
        return "A different timeframe now stands out"
    a, b = previous["evidence"], current["evidence"]
    if current["type"] == "unusual":
        if abs(b["standardized_magnitude"]) >= abs(a["standardized_magnitude"]) + 0.75:
            return "The movement became substantially more unusual"
        threshold = max(
            abs(a["movement"]) * 0.25, abs(a["reference_std"]) * 0.75, 1e-10
        )
        if abs(b["movement"] - a["movement"]) >= threshold:
            return "New observations materially changed the size of the move"
    else:
        if (
            a["recent_correlation"] * b["recent_correlation"] < 0
            and abs(a["recent_correlation"] - b["recent_correlation"]) >= 0.15
        ):
            return "The recent relationship reversed direction"
        if (
            abs(a["recent_correlation"] - b["recent_correlation"]) >= 0.2
            or abs(a["correlation_difference"] - b["correlation_difference"]) >= 0.2
        ):
            return "The measured relationship changed materially"
        if abs(b.get("divergence_z", 0) - a.get("divergence_z", 0)) >= 0.75:
            return "The divergence changed materially"
    if was_archived and current["observation_date"] != previous["observation_date"]:
        return "The pattern qualifies again after an inactive interval"
    return None


def priority(f, status):
    old = f["ranking"]["components"]
    sources = f["sources"]
    quality = (
        0.65
        if any(s["source"] == "Yahoo Finance" for s in sources)
        else 0.85
        if any(
            s.get("verification", {}).get("raw_status", "Unverified") == "Unverified"
            for s in sources
        )
        else 1
    )
    relevance = (
        1
        if any(
            k in {"us10y", "cpi", "cpi_nsa", "unemployment", "payrolls", "sp500"}
            for k in f["datasets"]
        )
        else 0.6
    )
    parts = {
        "magnitude": old.get("magnitude", 0) / 25 * 20,
        "historical_rarity": old.get("historical_rarity", 0),
        "sample_size": old.get("sample_size", 0),
        "completeness": old.get("completeness", 0),
        "stability": old.get("window_stability", 0) / 15 * 10,
        "freshness": 5
        if all(v == "ok" for v in f.get("current_source_status", {}).values())
        else 0,
        "data_quality": quality * 5,
        "predeclared_relevance": relevance * 5,
        "new_information": 5 if status == "New" else 4 if status == "Updated" else 0,
    }
    return {
        "score": round(sum(parts.values()), 2),
        "components": {k: round(v, 2) for k, v in parts.items()},
        "meaning": "A deterministic research priority, not confidence or economic importance. Relevance is a predeclared benchmark weight, not an estimated economic impact.",
    }


class DiscoveryMemory:
    def __init__(self, store):
        self.store = store

    def apply(self, findings, data, now=None):
        now = now or datetime.now(UTC)
        stamp = now.isoformat()
        active = set()
        by_id = {d.id: d for d in data}
        changed = []
        with self.store.connection(True) as db:
            for finding in findings:
                f = deepcopy(finding)
                key = f["event_key"]
                active.add(key)
                previous = db.execute(
                    "SELECT * FROM stories WHERE event_key=? ORDER BY first_detected DESC LIMIT 1",
                    (key,),
                ).fetchone()
                episode_days = {
                    "daily": 45,
                    "weekly": 120,
                    "monthly": 365,
                    "quarterly": 730,
                }[f["frequency"]]
                new_episode = (
                    previous
                    and previous["status"] == "Archived"
                    and (
                        datetime.fromisoformat(f["observation_date"]).date()
                        - datetime.fromisoformat(previous["last_observation"]).date()
                    ).days
                    >= episode_days
                )
                if not previous or new_episode:
                    identity = sha256(
                        f"story:{key}:{f['observation_date']}".encode()
                    ).hexdigest()[:24]
                    f["id"] = identity
                    related = [previous["id"]] if previous else []
                    reason = (
                        "A previously observed pattern returned after a distinct interval"
                        if previous
                        else "First detected in the monitored observations"
                    )
                    db.execute(
                        "INSERT INTO stories VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            identity,
                            key,
                            stamp,
                            stamp,
                            stamp,
                            f["observation_date"],
                            "New",
                            1,
                            dumps(f),
                            evidence_hash(f),
                            reason,
                            dumps(related),
                        ),
                    )
                    db.execute(
                        "INSERT INTO story_versions VALUES (?,?,?,?,?)",
                        (identity, 1, stamp, reason, dumps(f)),
                    )
                    changed.append(identity)
                    continue
                anchor = db.execute(
                    "SELECT snapshot FROM story_versions WHERE story_id=? AND version=?",
                    (previous["id"], previous["version"]),
                ).fetchone()
                old = json.loads(anchor["snapshot"] if anchor else previous["snapshot"])
                f["id"] = previous["id"]
                reason = material_change(old, f, previous["status"] == "Archived")
                version = previous["version"] + 1 if reason else previous["version"]
                status = (
                    "Updated"
                    if reason
                    else previous["status"]
                    if previous["status"] != "Archived"
                    else "Ongoing"
                )
                meaningful = stamp if reason else previous["last_meaningful"]
                db.execute(
                    "UPDATE stories SET last_meaningful=?,last_seen=?,last_observation=?,status=?,version=?,snapshot=?,evidence_hash=?,reason=? WHERE id=?",
                    (
                        meaningful,
                        stamp,
                        f["observation_date"],
                        status,
                        version,
                        dumps(f),
                        evidence_hash(f) if reason else previous["evidence_hash"],
                        reason or previous["reason"],
                        previous["id"],
                    ),
                )
                if reason:
                    db.execute(
                        "INSERT INTO story_versions VALUES (?,?,?,?,?)",
                        (previous["id"], version, stamp, reason, dumps(f)),
                    )
                    changed.append(previous["id"])
            # Missing or stale sources never falsely resolve a story.
            for row in db.execute(
                "SELECT * FROM stories WHERE status!='Archived'"
            ).fetchall():
                if row["event_key"] in active:
                    continue
                f = json.loads(row["snapshot"])
                sources = [by_id.get(i) for i in f["datasets"]]
                if not all(
                    d and d.status == "ok" and d.latest_observation_date
                    for d in sources
                ):
                    continue
                latest = min(
                    datetime.fromisoformat(d.latest_observation_date).date()
                    for d in sources
                )
                grace = {"daily": 10, "weekly": 28, "monthly": 90, "quarterly": 180}[
                    f["frequency"]
                ]
                if (
                    latest - datetime.fromisoformat(row["last_observation"]).date()
                ).days >= grace:
                    db.execute(
                        "UPDATE stories SET status='Archived',reason='No longer qualifies after newer healthy source observations' WHERE id=?",
                        (row["id"],),
                    )
            db.execute(
                "UPDATE stories SET status='Ongoing' WHERE status IN ('New','Updated') AND substr(last_meaningful,1,10)<?",
                (now.date().isoformat(),),
            )
        return changed

    def counts(self):
        with self.store.connection() as db:
            counts = {
                r["status"]: r["n"]
                for r in db.execute(
                    "SELECT status,COUNT(*) n FROM stories GROUP BY status"
                )
            }
            historical = db.execute("SELECT COUNT(*) FROM library").fetchone()[0]
        return {
            "active": sum(n for k, n in counts.items() if k != "Archived"),
            "archived": counts.get("Archived", 0),
            "historical": historical,
        }

    @staticmethod
    def selection(archived=None, identity=None, event_keys=None, exclude=()):
        clauses = []
        params = []
        if archived is not None:
            clauses.append(
                "status='Archived'"
                if archived
                else "status IN ('New','Updated','Ongoing')"
            )
        if identity is not None:
            clauses.append("id=?")
            params.append(identity)
        if event_keys is not None:
            keys = sorted(event_keys)
            clauses.append(
                "event_key IN (" + ",".join("?" for _ in keys) + ")" if keys else "0"
            )
            params.extend(keys)
        if exclude:
            clauses.append("id NOT IN (" + ",".join("?" for _ in exclude) + ")")
            params.extend(exclude)
        return (" WHERE " + " AND ".join(clauses) if clauses else ""), params

    def summaries(self, archived=True, limit=20, offset=0, exclude=(), kind="all"):
        where, params = self.selection(archived=archived, exclude=exclude)
        if kind != "all":
            where += " AND json_extract(snapshot,'$.type')=?"
            params.append(kind)
        with self.store.connection() as db:
            total = db.execute(
                "SELECT COUNT(*) FROM stories" + where, params
            ).fetchone()[0]
            rows = db.execute(
                "SELECT id,status,version evidence_version,last_meaningful,last_observation observation_date,json_extract(snapshot,'$.headline') headline,json_extract(snapshot,'$.frequency') frequency,json_extract(snapshot,'$.type') type FROM stories"
                + where
                + " ORDER BY last_meaningful DESC,id LIMIT ? OFFSET ?",
                [*params, limit, offset],
            ).fetchall()
        return {
            "items": [dict(r) for r in rows],
            "total": total,
            "offset": offset,
            "next_offset": offset + limit if offset + limit < total else None,
        }

    def list(
        self,
        active_keys=None,
        data=None,
        now=None,
        *,
        archived=None,
        limit=None,
        offset=0,
        identity=None,
        event_keys=None,
        exclude=(),
    ):
        now = now or datetime.now(UTC)
        active_keys = set(active_keys or [])
        sources = {d.id: d for d in data or []}
        # Commit the tiny lifecycle write before reading/parsing evidence.
        with self.store.connection(True) as db:
            db.execute(
                "UPDATE stories SET status='Ongoing' WHERE status IN ('New','Updated') AND substr(last_meaningful,1,10)<?",
                (now.date().isoformat(),),
            )
        where, params = self.selection(archived, identity, event_keys, exclude)
        sql = "SELECT * FROM stories" + where + " ORDER BY last_meaningful DESC,id"
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        with self.store.connection() as db:
            records = db.execute(sql, params).fetchall()
            version_rows = {
                r["id"]: db.execute(
                    "SELECT * FROM story_versions WHERE story_id=? ORDER BY version DESC LIMIT 3",
                    (r["id"],),
                ).fetchall()
                for r in records
            }
        result = []
        for row in records:
            f = json.loads(row["snapshot"])
            versions = []
            for v in reversed(version_rows[row["id"]]):
                previous = json.loads(v["snapshot"])
                versions.append(
                    {
                        "version": v["version"],
                        "detected_at": v["detected_at"],
                        "reason": v["reason"],
                        "headline": previous["headline"],
                        "evidence": {
                            k: value
                            for k, value in previous["evidence"].items()
                            if k not in ARRAYS
                        },
                        "configuration": previous["configuration"],
                    }
                )
            related = json.loads(row["related"])
            keys = f.get("related_signals", [])
            if keys:
                with self.store.connection() as db:
                    related.extend(
                        r["id"]
                        for r in db.execute(
                            "SELECT id FROM stories WHERE event_key IN ("
                            + ",".join("?" for _ in keys)
                            + ") LIMIT 50",
                            keys,
                        )
                    )
            f.update(
                id=row["id"],
                evidence_version=row["version"],
                evidence_fingerprint=row["evidence_hash"],
                lifecycle={
                    "status": row["status"],
                    "first_detected": row["first_detected"],
                    "last_meaningful_update": row["last_meaningful"],
                    "last_seen_qualifying": row["last_seen"],
                    "qualifies_now": row["event_key"] in active_keys,
                    "what_changed": row["reason"],
                    "related_discoveries": list(dict.fromkeys(related)),
                },
                history=versions,
            )
            f["current_source_status"] = {
                i: sources[i].status if i in sources else "not checked"
                for i in f["datasets"]
            }
            f["ranking"] = priority(f, row["status"])
            result.append(f)
        return result
