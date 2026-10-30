"""Read-only cgroup-v2 telemetry for the disposable Linux validation job."""

from pathlib import Path


def snapshot(root=Path("/sys/fs/cgroup")):
    def text(name):
        return (root / name).read_text().strip()

    def number(name):
        value = text(name)
        return None if value == "max" else int(value)

    def pairs(name):
        return {
            key: int(value)
            for key, value in (line.split() for line in text(name).splitlines())
        }

    try:
        return {
            "available": True,
            "memory_current": number("memory.current"),
            "memory_peak": number("memory.peak"),
            "memory_max": number("memory.max"),
            "swap_current": number("memory.swap.current"),
            "swap_max": number("memory.swap.max"),
            "memory_events": pairs("memory.events"),
            "memory_stat": {
                k: v
                for k, v in pairs("memory.stat").items()
                if k in {"anon", "file", "kernel", "sock"}
            },
            "cpu_max": text("cpu.max"),
            "cpu_stat": pairs("cpu.stat"),
        }
    except (FileNotFoundError, PermissionError, ValueError):
        return {"available": False}
