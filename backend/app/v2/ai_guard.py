"""Optional backend-only candidate generation with an atomic UTC-month budget gate.
No scan, page load or normal research action calls this module's generate method.
"""

from __future__ import annotations

import json
import math
import os
import re
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256

import requests

from backend.app.v2.definitions import SPECS
from backend.app.v2.runtime import ai_cache_key
from backend.app.v2.state import dumps

MODEL = "gpt-6-luna"
PRICE_URL = "https://developers.openai.com/api/docs/models/gpt-6-luna.md"
INPUT_BOUND = 24000
OUTPUT_BOUND = 800
NANO = 1_000_000_000


class BudgetBlocked(RuntimeError):
    pass


def verify_pricing():
    r = requests.get(PRICE_URL, timeout=15)
    r.raise_for_status()
    text = r.text
    if "Use `gpt-6-luna`" not in text or "### Text tokens" not in text:
        raise BudgetBlocked("Model pricing document could not be verified.")
    rates = {}
    for label in ["Input", "Cache writes", "Output"]:
        match = re.search(
            r"\| " + re.escape(label) + r" \| \$(\d+(?:\.\d+)?) \| 1M tokens \|", text
        )
        if not match:
            raise BudgetBlocked(
                "Pricing format changed; generation is paused until reviewed."
            )
        rates[label] = float(match[1])
    if not all(0 < v < 100 for v in rates.values()):
        raise BudgetBlocked("Unverifiable price range.")
    return {
        "input": max(rates["Input"], rates["Cache writes"]),
        "output": rates["Output"],
        "source": PRICE_URL,
        "document_hash": sha256(text.encode()).hexdigest(),
        "model": MODEL,
        "safety_multiplier": 2,
    }


def send(body, key):
    # requests performs no automatic retry; fixed origin, no configurable proxy endpoint.
    r = requests.post(
        "https://api.openai.com/v1/responses",
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        json=body,
        timeout=(10, 45),
    )
    r.raise_for_status()
    return r.json()


class AIGuard:
    def __init__(self, store, pricing_fn=verify_pricing, send_fn=send, now_fn=None):
        self.store, self.pricing_fn, self.send_fn = store, pricing_fn, send_fn
        self.now_fn = now_fn or (lambda: datetime.now(UTC))

    @property
    def limit(self):
        try:
            value = Decimal(os.getenv("MACROLENS_AI_MONTHLY_BUDGET_USD", "2.00"))
        except Exception as exc:
            raise BudgetBlocked("Invalid application budget configuration.") from exc
        if not value.is_finite() or value < 0 or value > 100:
            raise BudgetBlocked("Budget must be between 0 and 100 USD.")
        return int(value * NANO)

    def pricing(self):
        now = self.now_fn()
        with self.store.connection() as db:
            row = db.execute("SELECT * FROM pricing WHERE model=?", (MODEL,)).fetchone()
        if row and datetime.fromisoformat(row["verified_at"]) > now - timedelta(
            hours=24
        ):
            return json.loads(row["payload"])
        try:
            p = self.pricing_fn()
        except Exception as exc:
            raise BudgetBlocked(
                "Official pricing is unavailable or unverified. Deterministic research remains available."
            ) from exc
        if p.get("model") != MODEL or min(p.get("input", 0), p.get("output", 0)) <= 0:
            raise BudgetBlocked("Unverified pricing.")
        with self.store.connection(True) as db:
            db.execute(
                "INSERT OR REPLACE INTO pricing VALUES (?,?,?)",
                (MODEL, dumps(p), now.isoformat()),
            )
        return p

    @staticmethod
    def cost(p, input_tokens, output_tokens):
        return math.ceil(
            (input_tokens * p["input"] + output_tokens * p["output"]) * 1000 * 2
        )

    def usage(self):
        month = self.now_fn().strftime("%Y-%m")
        with self.store.connection() as db:
            rows = db.execute(
                "SELECT * FROM ai_requests WHERE month=?", (month,)
            ).fetchall()
            hits = db.execute(
                "SELECT value FROM counters WHERE name='ai_cache_hits'"
            ).fetchone()
            last = db.execute(
                "SELECT MAX(finished_at) FROM ai_requests WHERE state='complete' AND error IS NULL"
            ).fetchone()[0]
            uncertain = db.execute(
                "SELECT COUNT(*) FROM ai_requests WHERE state='uncertain'"
            ).fetchone()[0]
        used = sum(
            max(r["reserved_nano"], r["accounted_nano"])
            if r["state"] in {"pending", "uncertain"}
            else r["accounted_nano"]
            for r in rows
        )
        return {
            "month_utc": month,
            "budget_usd": self.limit / NANO,
            "accounted_spend_usd": used / NANO,
            "remaining_usd": max(0, self.limit - used) / NANO,
            "request_count": len(rows),
            "cache_hits_lifetime": hits[0] if hits else 0,
            "model": MODEL,
            "last_successful_generation": last,
            "enabled": os.getenv("MACROLENS_AI_ENABLED", "false").lower() == "true"
            and bool(os.getenv("OPENAI_API_KEY")),
            "paused_for_uncertain_usage": bool(uncertain),
            "note": "Conservative application accounting includes pending reservations and a 2× pricing safety margin. This does not cover other applications using the account.",
        }

    def reserve(self, key, p):
        now = self.now_fn()
        month = now.strftime("%Y-%m")
        amount = self.cost(p, INPUT_BOUND, OUTPUT_BOUND)
        identity = uuid.uuid4().hex
        with self.store.connection(True) as db:
            if db.execute(
                "SELECT 1 FROM ai_requests WHERE state='uncertain' LIMIT 1"
            ).fetchone():
                raise BudgetBlocked(
                    "AI usage is uncertain; an administrator must reconcile the ledger before more calls."
                )
            if db.execute(
                "SELECT 1 FROM ai_requests WHERE cache_key=?", (key,)
            ).fetchone():
                raise BudgetBlocked(
                    "This evidence batch is already reserved or processed; no duplicate request sent."
                )
            used = db.execute(
                "SELECT COALESCE(SUM(CASE WHEN state IN ('pending','uncertain') THEN MAX(reserved_nano,accounted_nano) ELSE accounted_nano END),0) FROM ai_requests WHERE month=?",
                (month,),
            ).fetchone()[0]
            if used + amount > self.limit:
                raise BudgetBlocked(
                    "The remaining monthly budget cannot cover the conservative maximum request cost."
                )
            db.execute(
                "INSERT INTO ai_requests(id,cache_key,month,state,reserved_nano,model,created_at) VALUES (?,?,?,?,?,?,?)",
                (identity, key, month, "pending", amount, MODEL, now.isoformat()),
            )
        return identity, amount

    def generate(self, findings):
        if os.getenv(
            "MACROLENS_AI_ENABLED", "false"
        ).lower() != "true" or not os.getenv("OPENAI_API_KEY"):
            return {
                "generated": 0,
                "fallback": True,
                "reason": "Optional AI is disabled or no backend key is configured.",
            }
        selected = []
        for f in findings[:5]:
            with self.store.connection() as db:
                cached = db.execute(
                    "SELECT 1 FROM ai_cache WHERE cache_key=?", (ai_cache_key(f),)
                ).fetchone()
            if cached:
                self.store.counter("ai_cache_hits")
            elif f.get("lifecycle", {}).get("status") in {"New", "Updated"}:
                selected.append(f)
        if not selected:
            return {
                "generated": 0,
                "fallback": True,
                "reason": "No uncached new or materially updated evidence.",
            }
        evidence = [
            {
                "story_id": f["id"],
                "headline": f["headline"],
                "datasets": f["datasets"],
                "horizon": f["horizon_observations"],
                "key_number": f["key_number"],
            }
            for f in selected
        ]
        content = dumps(
            {
                "task": "Propose up to two relevant same-frequency dataset IDs per story for follow-up research. These are hypotheses, never causal or factual findings. Do not generate values, dates or prose. Choose only allowed IDs.",
                "stories": evidence,
                "catalogue": [
                    {
                        "id": s.id,
                        "frequency": s.frequency,
                        "definition": s.definition[:200],
                    }
                    for s in SPECS.values()
                ],
            }
        )
        if len(content.encode()) > 14000:
            raise BudgetBlocked("Evidence exceeds the conservative input bound.")
        schema = {
            "type": "object",
            "properties": {
                "suggestions": {
                    "type": "array",
                    "maxItems": 10,
                    "items": {
                        "type": "object",
                        "properties": {
                            "story_id": {
                                "type": "string",
                                "enum": [f["id"] for f in selected],
                            },
                            "dataset_id": {"type": "string", "enum": list(SPECS)},
                        },
                        "required": ["story_id", "dataset_id"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["suggestions"],
            "additionalProperties": False,
        }
        body = {
            "model": MODEL,
            "input": content,
            "max_output_tokens": OUTPUT_BOUND,
            "reasoning": {"effort": "none"},
            "service_tier": "default",
            "store": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "research_candidates",
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        # Bound the entire serialized request (including schema) well below INPUT_BOUND bytes.
        if len(dumps(body).encode()) > 20000:
            raise BudgetBlocked(
                "Serialized request exceeds the verified input allowance."
            )
        p = self.pricing()
        batch = sha256(
            dumps(sorted(ai_cache_key(f) for f in selected)).encode()
        ).hexdigest()
        identity, reserved = self.reserve(batch, p)
        try:
            response = self.send_fn(body, os.environ["OPENAI_API_KEY"])
            usage = response.get("usage") or {}
            inp, out = usage.get("input_tokens"), usage.get("output_tokens")
            if (
                type(inp) is not int
                or type(out) is not int
                or not 0 <= inp <= INPUT_BOUND
                or not 0 <= out <= OUTPUT_BOUND
            ):
                raise BudgetBlocked(
                    "Reported usage missing or outside reserved bounds."
                )
            actual = self.cost(p, inp, out)
            if actual > reserved:
                raise BudgetBlocked("Reported cost exceeded reservation.")
        except Exception as exc:
            with self.store.connection(True) as db:
                db.execute(
                    "UPDATE ai_requests SET state='uncertain',accounted_nano=reserved_nano,error=?,finished_at=? WHERE id=?",
                    (
                        "Provider failure or usage could not be verified; full reservation retained.",
                        self.now_fn().isoformat(),
                        identity,
                    ),
                )
            raise BudgetBlocked(
                "AI request failed or usage could not be verified. Full reservation retained; optional AI paused. Deterministic suggestions remain available."
            ) from exc
        payload = {}
        valid = False
        try:
            texts = [
                c["text"]
                for item in response.get("output", [])
                for c in item.get("content", [])
                if c.get("type") == "output_text"
            ]
            parsed = json.loads("".join(texts))
            items = parsed["suggestions"]
            if not isinstance(items, list) or len(items) > 10:
                raise ValueError("Invalid output")
            for f in selected:
                candidates = [
                    i["dataset_id"]
                    for i in items
                    if i.get("story_id") == f["id"] and i.get("dataset_id") in SPECS
                ][:2]
                payload[ai_cache_key(f)] = {
                    "candidates": candidates,
                    "origin": "AI-suggested hypothesis; Python validates comparisons before display.",
                }
            valid = True
        except (ValueError, KeyError, TypeError):
            pass
        with self.store.connection(True) as db:
            db.execute(
                "UPDATE ai_requests SET state='complete',accounted_nano=?,input_tokens=?,output_tokens=?,finished_at=?,error=? WHERE id=?",
                (
                    actual,
                    inp,
                    out,
                    self.now_fn().isoformat(),
                    None if valid else "Output invalid; deterministic fallback.",
                    identity,
                ),
            )
            for key, value in payload.items():
                db.execute(
                    "INSERT OR IGNORE INTO ai_cache VALUES (?,?,?,?)",
                    (key, dumps(value), self.now_fn().isoformat(), MODEL),
                )
        return {
            "generated": len(payload),
            "fallback": not valid,
            "reason": "Candidate hypotheses cached; only Python-validated compatible observations can be displayed.",
            "usage": self.usage(),
        }
