"""Linux-only capture RSS/cgroup measurement; forwards the collector's arguments."""

import json
import os
import re
import resource
import sys
import time
from pathlib import Path

from scripts.collect_expansion import main
from scripts.linux_cgroup import snapshot

if __name__ == "__main__":
    label = os.environ.get("EXPANSION_CAPTURE_LABEL", "official")
    if not re.fullmatch(r"[a-z-]{1,32}", label):
        raise ValueError("Invalid measurement label")
    started, cpu = time.perf_counter(), time.process_time()
    main()  # Own workspace validation, bounded official requests; no DB operations.
    workspace = Path(sys.argv[sys.argv.index("--workspace") + 1])
    result = {
        "label": label,
        "seconds": time.perf_counter() - started,
        "cpu_seconds": time.process_time() - cpu,
        "peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "cgroup": snapshot(),
        "production_access": False,
    }
    (workspace / f"capture-{label}-metrics.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result), flush=True)
