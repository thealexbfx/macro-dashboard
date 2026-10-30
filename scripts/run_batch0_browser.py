"""Start isolated synthetic backend and built frontend for browser validation."""

import os
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    artifacts = Path(
        os.environ.get(
            "BATCH0_BROWSER_ARTIFACTS",
            str(Path(tempfile.gettempdir()) / "batch0-browser"),
        )
    )
    artifacts.mkdir(parents=True, exist_ok=True)
    env = dict(
        os.environ,
        MACROLENS_V2_API_URL="http://127.0.0.1:8139",
        BATCH0_BROWSER_ARTIFACTS=str(artifacts),
    )
    with (
        (artifacts / "backend.log").open("w") as backend_log,
        (artifacts / "frontend.log").open("w") as frontend_log,
    ):
        backend = subprocess.Popen(
            [
                sys.executable,
                "-B",
                str(root / "scripts/validate_batch0_catalog.py"),
                "--serve",
            ],
            cwd=root,
            env=env,
            stdout=backend_log,
            stderr=backend_log,
        )
        frontend = subprocess.Popen(
            ["node", "node_modules/next/dist/bin/next", "start", "-p", "3039"],
            cwd=root / "frontend-v2",
            env=env,
            stdout=frontend_log,
            stderr=frontend_log,
        )
        try:
            for _ in range(120):
                if backend.poll() is not None or frontend.poll() is not None:
                    raise RuntimeError(
                        "Fixture server failed; inspect browser artifacts"
                    )
                try:
                    for url in (
                        "http://127.0.0.1:8139/health",
                        "http://127.0.0.1:3039",
                    ):
                        with urllib.request.urlopen(url, timeout=5) as response:
                            assert response.status == 200
                    break
                except OSError:
                    time.sleep(1)
            else:
                raise RuntimeError("Browser fixture startup timed out")
            subprocess.run(
                [sys.executable, "-B", str(root / "scripts/test_batch0_browser.py")],
                cwd=root,
                env=env,
                check=True,
            )
        finally:
            for process in (backend, frontend):
                if process.poll() is None:
                    process.terminate()
            for process in (backend, frontend):
                try:
                    process.wait(timeout=25)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)


if __name__ == "__main__":
    main()
