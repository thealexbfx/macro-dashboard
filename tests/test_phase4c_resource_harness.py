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


def test_driver_refuses_client_inside_backend_cap(monkeypatch):
    module = driver(monkeypatch)
    monkeypatch.setattr(module, "sys", SimpleNamespace(platform="linux"))
    with pytest.raises(SystemExit, match="Docker backend isolation"):
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
    launcher = (ROOT / "scripts/validate_phase4b.py").read_text(encoding="utf8")
    for bound in ["--memory=512m", "--memory-swap=512m", "--cpus=0.5"]:
        assert bound in launcher
    assert "--network=none" in launcher and "truncate -s 1G" in text
    assert "--docker-image macrolens-phase4c" in text
    assert "secrets." not in text and "render.com" not in text
    assert "no database or workbook" in text


def test_test_image_does_not_copy_local_databases_or_env_files():
    text = (ROOT / "scripts/phase4c.Dockerfile").read_text(encoding="utf-8-sig")
    assert "COPY . " not in text
    assert "COPY backend/app backend/app" in text
    assert ".env" not in text and "backend/.local" not in text


def test_synthetic_workbook_is_labelled_and_at_least_captured_size():
    from backend.app.ingestion.world_bank import parse_workbook
    from scripts.build_resource_workbook import build

    data, manifest = build()
    batch = parse_workbook(data)
    assert len(batch.points) == 2403
    assert "not_economic_data" in manifest["kind"]
    assert manifest["compressed_bytes"] >= 586099
    assert manifest["monthly_sheet_bytes"] >= 2375828
    assert manifest["shared_strings_bytes"] >= 50756
    assert sum(p.value is None for p in batch.points) == 1


def test_container_lookup_does_not_accidentally_resolve_an_image(monkeypatch):
    from unittest.mock import Mock

    from scripts.validate_phase4b import inspect_disposable_container

    mock = Mock(return_value=SimpleNamespace(returncode=1, stdout=""))
    monkeypatch.setattr("scripts.validate_phase4b.subprocess.run", mock)
    assert inspect_disposable_container("macrolens-phase4c") is None
    assert mock.call_args.args[0][:3] == ["docker", "container", "inspect"]


def test_container_lookup_refuses_unlabelled_resources(monkeypatch):
    from unittest.mock import Mock

    from scripts.validate_phase4b import inspect_disposable_container

    mock = Mock(
        return_value=SimpleNamespace(
            returncode=0, stdout='[{"Config":{"Labels":null}}]'
        )
    )
    monkeypatch.setattr("scripts.validate_phase4b.subprocess.run", mock)
    with pytest.raises(RuntimeError, match="unrelated container"):
        inspect_disposable_container("macrolens-phase4c")
