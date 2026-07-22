from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Audit:
    """Append structured audit records to bounded JSONL files."""

    def __init__(self, folder: str | Path, name: str = "audit.jsonl", max_bytes: int = 2 * 1024 * 1024, files: int = 3) -> None:
        self.path = Path(folder) / name
        self.max_bytes, self.files = max_bytes, files

    def record(self, action: str, actor: str | None = None, **data: Any) -> dict[str, Any]:
        """Write record and return immutable payload copy."""
        record = {"time": datetime.now(timezone.utc).isoformat(), "action": action, "actor": actor, **data}
        line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists() and self.path.stat().st_size + len(line.encode()) > self.max_bytes:
            self._rotate()
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(line)
        return record

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for path in reversed([self.path] + [self.path.with_name(f"{self.path.name}.{index}") for index in range(1, self.files)]):
            if not path.exists():
                continue
            try:
                records.extend(json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
            except (OSError, json.JSONDecodeError):
                continue
        return records[-limit:][::-1]

    def get(self, change_id: str) -> dict[str, Any] | None:
        return next((record for record in self.recent(100000) if record.get("change_id") == change_id), None)

    def _rotate(self) -> None:
        for index in range(self.files - 1, 0, -1):
            source = self.path.with_name(f"{self.path.name}.{index}")
            target = self.path.with_name(f"{self.path.name}.{index + 1}")
            if source.exists():
                if index + 1 >= self.files:
                    source.unlink()
                else:
                    source.replace(target)
        if self.path.exists():
            self.path.replace(self.path.with_name(f"{self.path.name}.1"))
