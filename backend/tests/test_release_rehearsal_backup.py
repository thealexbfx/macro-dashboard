import sqlite3
from contextlib import closing

import pytest

from scripts.validate_release100 import bounded_backup


def test_disposable_backup_copies_saved_research(tmp_path):
    with closing(sqlite3.connect(tmp_path / "source.sqlite3")) as source:
        source.execute("CREATE TABLE research(id TEXT PRIMARY KEY, notes TEXT)")
        source.execute("INSERT INTO research VALUES('saved', 'Keep this')")
        source.commit()
        with closing(sqlite3.connect(tmp_path / "copy.sqlite3")) as target:
            bounded_backup(source, target)
            assert target.execute("SELECT * FROM research").fetchall() == [
                ("saved", "Keep this")
            ]
            assert target.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_disposable_backup_times_out_on_an_open_write_transaction(tmp_path):
    with closing(sqlite3.connect(tmp_path / "source.sqlite3")) as source:
        source.execute("CREATE TABLE research(id TEXT PRIMARY KEY, notes TEXT)")
        source.execute("INSERT INTO research VALUES('saved', 'Pending write')")
        with closing(sqlite3.connect(tmp_path / "copy.sqlite3")) as target:
            with pytest.raises(TimeoutError, match="time budget"):
                bounded_backup(source, target, seconds=0.01)
        assert source.execute("SELECT notes FROM research").fetchone()[0] == "Pending write"
        source.rollback()
