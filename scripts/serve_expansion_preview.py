"""Loopback-only actual-history preview of the explicitly marked disposable DB."""

import argparse
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--database-name", default="disposable-release-v7.sqlite3")
    parser.add_argument("--port", type=int, default=8140)
    args = parser.parse_args()
    w = args.workspace.resolve()
    if (
        not (w / "DISPOSABLE_EXPANSION_ONLY").exists()
        or Path(args.database_name).name != args.database_name
        or not args.database_name.startswith("disposable-")
    ):
        parser.error("Marked disposable workspace required")
    database = w / args.database_name
    if not database.exists() or not 1024 <= args.port <= 65535:
        parser.error("Existing development database and local port required")
    os.environ.update(
        MACROLENS_V2_STATE_DB=str(database),
        MACROLENS_AI_ENABLED="false",
        MACROLENS_INGESTION_ENABLED="0",
    )
    import uvicorn

    from backend.app.v2 import main as v

    def unavailable(*_args, **_kwargs):
        raise ValueError(
            "Existing public history not copied into this disposable preview"
        )

    for service in (v.service, v.legacy_service):
        service.provider.fred_series = unavailable
        service.provider.market_series = unavailable
    # This actual-history preview must not start any external source refresh.
    v.refresh_scheduler.start = lambda: None
    uvicorn.run(v.app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
