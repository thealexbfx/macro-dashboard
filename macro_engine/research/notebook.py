"""Small local investigation store. IDs never come from filesystem paths."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import UUID, uuid4

DEFAULT_ROOT = (
    Path(__file__).resolve().parents[2] / "research_outputs" / "investigations"
)


def save_investigation(record, root=DEFAULT_ROOT, investigation_id=None):
    key = str(UUID(investigation_id)) if investigation_id else str(uuid4())
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    payload = {**record, "id": key, "schema_version": 1}
    encoded = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)
    if len(encoded.encode("utf-8")) > 2_000_000:
        raise ValueError("Investigation exceeds the 2 MB local record limit.")
    with NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=root, suffix=".tmp", delete=False
    ) as handle:
        handle.write(encoded)
        temporary = handle.name
    try:
        os.replace(temporary, root / f"{key}.json")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return payload


def load_investigations(root=DEFAULT_ROOT):
    result = []
    for path in sorted(
        Path(root).glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    ):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            UUID(record["id"])
            if record.get("schema_version") == 1:
                result.append(record)
        except (ValueError, KeyError, TypeError):
            continue
    return result
