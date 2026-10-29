"""Host-side resource gate; only the backend and pressure probe enter the capped cgroup."""

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO.parent / "phase4b-staging"
MIB = 1024 * 1024


def pressure_probe(out):
    assert (
        out.resolve().is_relative_to(ROOT.resolve()) and (out / "DISPOSABLE").exists()
    )
    Path("/proc/self/oom_score_adj").write_text("1000")
    allocation = bytearray(64 * MIB)
    for i in range(0, len(allocation), 4096):
        allocation[i] = 1
    (out / "pressure-ready").write_text("64 MiB synthetic anonymous pressure")
    time.sleep(8)
    assert allocation[-4096] == 1


def valid_limits(group):
    if not group.get("available"):
        return False
    quota, period = group["cpu_max"].split()
    return (
        group["memory_max"] == 512 * MIB
        and group["swap_max"] == 0
        and quota != "max"
        and abs(int(quota) / int(period) - 0.5) < 0.001
    )


def run(mode, workbook, docker_image=None):
    if sys.platform != "linux":
        raise SystemExit("Linux validation requires Linux; no fallback to Windows")
    if not docker_image:
        raise SystemExit(
            "Docker backend isolation is required; clients must remain outside the cap"
        )
    network = json.loads(
        subprocess.check_output(
            ["docker", "network", "inspect", "macrolens-phase4c-internal"], text=True
        )
    )[0]
    if not network["Internal"]:
        raise SystemExit("Require an internal test network")
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
    env = dict(
        os.environ,
        MACROLENS_PHASE4C_PRESSURE="1",
        MACROLENS_AI_ENABLED="false",
        MACROLENS_RESOURCE_FIXTURE="synthetic_sized_workbook",
        MACROLENS_PHASE4C_DOCKER_IMAGE=docker_image,
    )
    completed = subprocess.run(args, cwd=REPO, env=env, timeout=900, check=False)
    result = {
        "mode": mode,
        "host_platform": platform.platform(),
        "host_python": sys.version,
        "fixture": json.loads(workbook.with_suffix(".json").read_text()),
        "filesystem_bytes": filesystem_bytes,
        "harness_exit": completed.returncode,
        "clients_outside_memory_cgroup": True,
        "resource_gate_passed": False,
    }
    states_path = out / "docker-states.json"
    states = json.loads(states_path.read_text()) if states_path.exists() else []
    result["container_states"] = states
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
            max_normal_cgroup_bytes=max(normal) if normal else None,
            max_pressure_cgroup_bytes=max(pressure) if pressure else None,
            cgroup_peak_bytes=max(s["cgroup"]["memory_peak"] for s in observed)
            if observed
            else None,
            max_oom_kills=max(
                s["cgroup"]["memory_events"].get("oom_kill", 0) for s in observed
            )
            if observed
            else None,
            telemetry_samples=len(observed),
            responses=harness["status_counts"],
            sqlite_peak_bytes=max(s["sqlite_bytes"] for s in samples),
            final_disk_bytes=harness["final_disk_bytes"],
            backend_runtime=harness["runtime"],
            sampled_limits=observed[0]["cgroup"] if observed else None,
        )
        result["resource_gate_passed"] = (
            completed.returncode == 0
            and bool(observed)
            and all(valid_limits(s["cgroup"]) for s in observed)
            and all(harness["checks"].values())
            and result["max_oom_kills"] == 0
            and bool(states)
            and not any(x["state"]["OOMKilled"] for x in states)
            and bool(normal)
            and max(normal) <= 448 * MIB
            and bool(pressure)
        )
    (ROOT / ("phase4c-" + mode + ".json")).write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)
    raise SystemExit(0 if result["resource_gate_passed"] else 2)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode", choices=["enabled", "disabled"])
    p.add_argument("--workbook", type=Path)
    p.add_argument("--docker-image")
    p.add_argument("--pressure-probe", type=Path)
    a = p.parse_args()
    if a.pressure_probe:
        pressure_probe(a.pressure_probe)
    elif a.mode and a.workbook:
        run(a.mode, a.workbook, a.docker_image)
    else:
        p.error("Choose --mode/--workbook/--docker-image or --pressure-probe")
