"""Offline contracts for the test-only Linux resource job."""

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from scripts.linux_cgroup import snapshot

ROOT = Path(__file__).resolve().parents[1]


def cgroup(tmp_path, memory_max="536870912"):
    data = {
        "memory.current": "220000000",
        "memory.peak": "260000000",
        "memory.max": memory_max,
        "memory.swap.current": "0",
        "memory.swap.max": "0",
        "memory.events": "low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\n",
        "memory.stat": "anon 180000000\nfile 40000000\nkernel 1000000\nsock 0\n",
        "cpu.max": "50000 100000",
        "cpu.stat": "usage_usec 1000\nnr_periods 5\nnr_throttled 2\nthrottled_usec 500\n",
    }
    for name, value in data.items():
        (tmp_path / name).write_text(value)
    return tmp_path


def test_linux_cgroup_memory_cpu_and_oom_are_read(tmp_path):
    result = snapshot(cgroup(tmp_path))
    assert result["available"] and result["memory_max"] == 512 * 1024**2
    assert result["memory_events"]["oom_kill"] == 0
    assert result["cpu_stat"]["nr_throttled"] == 2
    assert result["memory_stat"]["anon"] == 180000000


def test_unlimited_cgroup_is_not_misreported_as_capped(tmp_path):
    assert snapshot(cgroup(tmp_path, "max"))["memory_max"] is None


def test_missing_cgroup_never_claims_linux_validation(tmp_path):
    assert snapshot(tmp_path) == {"available": False}


def driver(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    return importlib.import_module("validate_phase4c")


def test_driver_refuses_non_linux(monkeypatch):
    module = driver(monkeypatch)
    monkeypatch.setattr(module, "sys", SimpleNamespace(platform="win32"))
    with pytest.raises(SystemExit, match="requires Linux"):
        module.run("enabled", Path("unused"))


def test_driver_refuses_missing_cgroup(monkeypatch):
    module = driver(monkeypatch)
    monkeypatch.setattr(module, "sys", SimpleNamespace(platform="linux"))
    monkeypatch.setattr(module, "snapshot", lambda: {"available": False})
    with pytest.raises(SystemExit, match="cgroup v2"):
        module.run("enabled", Path("unused"))


def test_ci_is_feature_only_and_has_hard_limits_without_secrets():
    path = ROOT / ".github/workflows/phase4c-linux.yml"
    text = path.read_text(encoding="utf-8-sig")
    workflow = yaml.load(text, Loader=yaml.BaseLoader)
    assert workflow["on"]["push"]["branches"] == ["feature/macrolens-v2"]
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["jobs"]["linux_512mb"]["strategy"]["matrix"]["mode"] == [
        "disabled",
        "enabled",
    ]
    for bound in [
        "--memory=512m",
        "--memory-swap=512m",
        "--cpus=0.5",
        "--network=none",
        "truncate -s 1G",
    ]:
        assert bound in text
    assert "secrets." not in text and "render.com" not in text
    assert "no database or workbook" in text


def test_test_image_does_not_copy_local_databases_or_env_files():
    text = (ROOT / "scripts/phase4c.Dockerfile").read_text(encoding="utf-8-sig")
    assert "COPY . " not in text
    assert "COPY backend/app backend/app" in text
    assert ".env" not in text and "backend/.local" not in text
