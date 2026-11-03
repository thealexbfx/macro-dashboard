"""Operator-approved consistent backup, independent download and disposable restore.

Preparation code only. Does nothing without --approve-production-backup.
Uses existing SSH access, never uploads a database, changes settings or deploys.
"""

import argparse
import json
import re
import shlex
import subprocess
import uuid
from pathlib import Path

from backend.app.catalog.rollout import verify_backup

REMOTE = r"""
import hashlib,json,os,shutil,sqlite3,time,uuid
from contextlib import closing
from pathlib import Path
source=Path('/var/data/macrolens-v2.sqlite3')
assert source.is_file(), 'Expected database missing'
size=source.stat().st_size+(Path(str(source)+'-wal').stat().st_size if Path(str(source)+'-wal').exists() else 0)
assert shutil.disk_usage(source.parent).free>size+150*1024**2,'Backup disk reserve insufficient'
target=source.parent/('macrolens-independent-'+uuid.uuid4().hex+'.sqlite3')
partial=Path(str(target)+'.partial')
fd=os.open(partial,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
started=time.monotonic()
def progress(status,remaining,total):
    if time.monotonic()-started>90: raise RuntimeError('Backup deadline exceeded; live data untouched')
with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True,timeout=5)) as live, closing(sqlite3.connect(partial)) as copy:
    live.backup(copy,pages=256,progress=progress,sleep=0.05)
    assert copy.execute('PRAGMA integrity_check').fetchone()[0]=='ok','Backup integrity failed'
assert not target.exists()
partial.rename(target)
hasher=hashlib.sha256()
with target.open('rb') as stream:
    while block:=stream.read(1048576):hasher.update(block)
print(json.dumps({'backup':str(target),'sha256':hasher.hexdigest(),'bytes':target.stat().st_size,'revision':os.getenv('RENDER_GIT_COMMIT')}))
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ssh", required=True)
    parser.add_argument("--identity", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--approve-production-backup", action="store_true")
    args = parser.parse_args()
    if (
        not args.approve_production_backup
        or not re.fullmatch(r"srv-[a-z0-9]+@ssh\.[a-z]+\.render\.com", args.ssh)
        or not re.fullmatch("[0-9a-f]{40}", args.expected_revision)
    ):
        parser.error(
            "Explicit backup approval, exact revision and Render SSH address required"
        )
    if not args.identity.is_file():
        parser.error(
            "Existing SSH identity required; no credentials are requested or printed"
        )
    args.output_directory.mkdir(parents=True, exist_ok=True)
    # Verify the revision before any backup-file write, not just after returning.
    script = (
        "import os; assert os.getenv('RENDER_GIT_COMMIT') == "
        + repr(args.expected_revision)
        + ", 'Unexpected deployed revision'\n"
        + REMOTE
    )
    common = [
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=15",
        "-i",
        str(args.identity),
    ]
    result = subprocess.run(
        ["ssh", *common, args.ssh, "python -c " + shlex.quote(script)],
        text=True,
        capture_output=True,
        timeout=120,
        check=True,
    )
    receipt = json.loads(result.stdout.strip().splitlines()[-1])
    if (
        not re.fullmatch(
            r"/var/data/macrolens-independent-[a-f0-9]{32}\.sqlite3", receipt["backup"]
        )
        or not re.fullmatch("[a-f0-9]{64}", receipt["sha256"])
        or receipt["revision"] != args.expected_revision
    ):
        raise ValueError("Invalid backup receipt; do not use it for release")
    local = args.output_directory / (
        "macrolens-independent-" + uuid.uuid4().hex + ".sqlite3"
    )
    assert not local.exists()
    subprocess.run(
        ["scp", "-s", *common, args.ssh + ":" + receipt["backup"], str(local)],
        check=True,
        timeout=180,
    )
    if local.stat().st_size != receipt["bytes"]:
        raise ValueError("Downloaded backup size differs")
    verified = verify_backup(local, receipt["sha256"])
    report = {
        **receipt,
        **verified,
        "independent_copy": str(local.resolve()),
        "production_database_replaced": False,
    }
    local.with_suffix(".receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
