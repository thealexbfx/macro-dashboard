"""Resource-limit gate for the disposable Phase 4B Linux harness; no production IO."""

import argparse
import json
import os
import platform
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from linux_cgroup import snapshot

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO.parent / "phase4b-staging"
MIB = 1024 * 1024


def pressure_probe(out):
    assert (
        out.resolve().is_relative_to(ROOT.resolve()) and (out / "DISPOSABLE").exists()
    )
    # Sacrifice only this synthetic pressure process first if the test reaches OOM.
    Path("/proc/self/oom_score_adj").write_text("1000")
    allocation = bytearray(64 * MIB)
    for i in range(0, len(allocation), 4096):
        allocation[i] = 1
    (out / "pressure-ready").write_text("64 MiB synthetic anonymous pressure")
    time.sleep(8)
    assert allocation[-4096] == 1


def run(mode, workbook):
    if sys.platform != "linux":
        raise SystemExit("Linux validation requires Linux; no fallback to Windows")
    before = snapshot()
    if not before.get("available"):
        raise SystemExit("Readable cgroup v2 telemetry is required")
    if before["memory_max"] != 512 * MIB or before["swap_max"] != 0:
        raise SystemExit("Require an enforced 512 MiB limit and disabled swap")
    quota, period = before["cpu_max"].split()
    if quota == "max" or abs(int(quota) / int(period) - 0.5) > 0.001:
        raise SystemExit("Require half a CPU")
    fs = os.statvfs(ROOT)
    filesystem_bytes = fs.f_blocks * fs.f_frsize
    if not 900 * MIB <= filesystem_bytes <= 1024 * MIB:
        raise SystemExit("Require a disposable filesystem of at most 1 GiB")
    out = ROOT / ("linux-" + mode)
    args = [
        sys.executable,
        str(REPO / "scripts/validate_phase4b.py"),
        "--output",
        str(out),
        "--workbook",
        str(workbook),
    ]
    if mode == "disabled":
        args.append("--disabled")
    env = dict(os.environ, MACROLENS_PHASE4C_PRESSURE="1", MACROLENS_AI_ENABLED="false")
    completed = subprocess.run(args, cwd=REPO, env=env, timeout=900, check=False)
    after = snapshot()
    result = {
        "mode": mode,
        "platform": platform.platform(),
        "python": sys.version,
        "sqlite": sqlite3.sqlite_version,
        "filesystem_bytes": filesystem_bytes,
        "cgroup_before": before,
        "cgroup_after": after,
        "harness_exit": completed.returncode,
        "runtime_image": Path("/etc/os-release").read_text(),
    }
    source = out / "results.json"
    if source.exists():
        harness = json.loads(source.read_text())
        samples = harness["samples"]
        observed = [s for s in samples if s.get("cgroup", {}).get("available")]
        normal = [
            s["cgroup"]["memory_current"]
            for s in observed
            if s["phase"] != "memory_pressure"
        ]
        pressure = [
            s["cgroup"]["memory_current"]
            for s in observed
            if s["phase"] == "memory_pressure"
        ]
        result.update(
            checks=harness["checks"],
            max_backend_rss_bytes=max(s["peak_rss"] for s in samples),
            max_normal_cgroup_bytes=max(normal),
            max_pressure_cgroup_bytes=max(pressure) if pressure else None,
            telemetry_samples=len(observed),
            responses=harness["status_counts"],
            sqlite_peak_bytes=max(s["sqlite_bytes"] for s in samples),
            final_disk_bytes=harness["final_disk_bytes"],
        )
        result["resource_gate_passed"] = (
            completed.returncode == 0
            and all(harness["checks"].values())
            and after["memory_events"].get("oom_kill", 0)
            == before["memory_events"].get("oom_kill", 0)
            and max(normal) <= 448 * MIB
            and bool(pressure)
        )
    else:
        result["resource_gate_passed"] = False
    (ROOT / ("phase4c-" + mode + ".json")).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)
    raise SystemExit(0 if result["resource_gate_passed"] else 2)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=["enabled", "disabled"])
    p.add_argument("--workbook", type=Path)
    p.add_argument("--pressure-probe", type=Path)
    a = p.parse_args()
    if a.pressure_probe:
        pressure_probe(a.pressure_probe)
    elif a.mode and a.workbook:
        run(a.mode, a.workbook)
    else:
        p.error("Choose --mode/--workbook or --pressure-probe")
