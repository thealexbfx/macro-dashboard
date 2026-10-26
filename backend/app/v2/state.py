"""Local SQLite state; no user-research migration and no paid infrastructure."""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Lock

SCHEMA = """
CREATE TABLE IF NOT EXISTS source_cache (id TEXT PRIMARY KEY,payload TEXT NOT NULL,checked_at TEXT NOT NULL,next_due TEXT NOT NULL,failures INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS leases (name TEXT PRIMARY KEY,owner TEXT NOT NULL,expires_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS stories (id TEXT PRIMARY KEY,event_key TEXT NOT NULL,first_detected TEXT NOT NULL,last_meaningful TEXT NOT NULL,last_seen TEXT NOT NULL,last_observation TEXT NOT NULL,status TEXT NOT NULL,version INTEGER NOT NULL,snapshot TEXT NOT NULL,evidence_hash TEXT NOT NULL,reason TEXT NOT NULL,related TEXT NOT NULL DEFAULT '[]');
CREATE INDEX IF NOT EXISTS story_key ON stories(event_key,last_meaningful);
CREATE TABLE IF NOT EXISTS story_versions (story_id TEXT NOT NULL,version INTEGER NOT NULL,detected_at TEXT NOT NULL,reason TEXT NOT NULL,snapshot TEXT NOT NULL,PRIMARY KEY(story_id,version));
CREATE TABLE IF NOT EXISTS library (id TEXT PRIMARY KEY,label TEXT NOT NULL,created_at TEXT NOT NULL,snapshot TEXT NOT NULL,notes TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY,fingerprint TEXT NOT NULL,payload TEXT NOT NULL,calculated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ai_requests (id TEXT PRIMARY KEY,cache_key TEXT UNIQUE NOT NULL,month TEXT NOT NULL,state TEXT NOT NULL,reserved_nano INTEGER NOT NULL,accounted_nano INTEGER NOT NULL DEFAULT 0,input_tokens INTEGER,output_tokens INTEGER,model TEXT NOT NULL,created_at TEXT NOT NULL,finished_at TEXT,error TEXT);
CREATE TABLE IF NOT EXISTS ai_cache (cache_key TEXT PRIMARY KEY,payload TEXT NOT NULL,generated_at TEXT NOT NULL,model TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY,value INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS pricing (model TEXT PRIMARY KEY,payload TEXT NOT NULL,verified_at TEXT NOT NULL);
"""


def dumps(value):
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False, default=str
    )


class Store:
    def __init__(self, path=None):
        self.path = Path(
            path
            or os.getenv("MACROLENS_V2_STATE_DB")
            or Path(__file__).resolve().parents[2] / ".local" / "macrolens-v2.sqlite3"
        )

        self._initialized = False
        self._init_lock = Lock()

    @contextmanager
    def connection(self, write=False):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA busy_timeout=30000")
            with self._init_lock:
                if not self._initialized:
                    if db.execute("PRAGMA journal_mode").fetchone()[0] != "wal":
                        db.execute("PRAGMA journal_mode=WAL")
                    db.executescript(SCHEMA)
                    self._initialized = True
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            if write:
                db.commit()
        except BaseException:
            if write:
                db.rollback()
            raise
        finally:
            db.close()

    def counter(self, key):
        with self.connection(True) as db:
            db.execute(
                "INSERT INTO counters(name,value) VALUES (?,1) ON CONFLICT(name) DO UPDATE SET value=value+1",
                (key,),
            )

    def acquire(self, name, owner, now, seconds=120):
        with self.connection(True) as db:
            row = db.execute("SELECT * FROM leases WHERE name=?", (name,)).fetchone()
            if row and row["expires_at"] > now:
                return False
            db.execute(
                "INSERT OR REPLACE INTO leases VALUES (?,?,?)",
                (name, owner, now + seconds),
            )
            return True

    def release(self, name, owner):
        with self.connection(True) as db:
            db.execute("DELETE FROM leases WHERE name=? AND owner=?", (name, owner))
