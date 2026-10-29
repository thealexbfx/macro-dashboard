"""Host-side Docker monitor: retains OOM evidence even if the container dies."""

import argparse
import json
import subprocess
import time
from pathlib import Path


def inspect(name):
    return json.loads(subprocess.check_output(["docker", "inspect", name], text=True))[
        0
    ]


def run(name, target):
    target.mkdir(parents=True, exist_ok=True)
    subprocess.run(["docker", "start", name], check=True)
    with (target / "host-metrics.ndjson").open("w") as output:
        while True:
            info = inspect(name)
            state = info["State"]
            row = {"time": time.time(), "state": state}
            if state["Running"]:
                try:
                    lines = (
                        Path(f"/proc/{state['Pid']}/cgroup").read_text().splitlines()
                    )
                    relative = next(
                        line.split("::", 1)[1]
                        for line in lines
                        if line.startswith("0::")
                    )
                    group = Path("/sys/fs/cgroup") / relative.lstrip("/")
                    row["cgroup"] = {
                        file: (group / file).read_text().strip()
                        for file in [
                            "memory.current",
                            "memory.peak",
                            "memory.max",
                            "memory.swap.max",
                            "memory.events",
                            "cpu.stat",
                            "cpu.max",
                        ]
                    }
                except (OSError, StopIteration):
                    row["cgroup"] = None
            output.write(json.dumps(row) + "\n")
            output.flush()
            if not state["Running"]:
                (target / "host-final.json").write_text(
                    json.dumps({"state": state, "limits": info["HostConfig"]}, indent=2)
                )
                return state["ExitCode"]
            time.sleep(0.5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("container")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    raise SystemExit(run(args.container, args.output))
