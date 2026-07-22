from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

class Tracks:
    """Persist ordered group progression tracks in tracks.json."""
    def __init__(self, folder: str | Path, groups: set[str] | list[str] | None = None) -> None:
        self.path = Path(folder) / "tracks.json"
        self._groups = None if groups is None else {group.strip().lower() for group in groups}
        self._tracks: dict[str, list[str]] = self._load()

    def _valid(self, groups: list[str]) -> bool:
        return bool(groups) and self._groups is not None and all(group in self._groups for group in groups)

    def _load(self) -> dict[str, list[str]]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return {str(k).lower(): [str(v).lower() for v in values] for k, values in data.items() if isinstance(values, list)}
        except (OSError, ValueError):
            return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix="tracks.", suffix=".tmp", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(self._tracks, stream, indent=2, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except BaseException:
            try:
                os.unlink(temporary)
            except OSError:
                pass
            raise

    def all(self) -> dict[str, list[str]]:
        """Return track snapshot."""
        return {name: list(groups) for name, groups in self._tracks.items()}

    def create(self, name: str, groups: list[str]) -> bool:
        """Create track."""
        key = name.strip().lower()
        if not key or key in self._tracks:
            return False
        normalized = list(dict.fromkeys(group.strip().lower() for group in groups if group.strip()))
        if not self._valid(normalized):
            return False
        self._tracks[key] = normalized
        self._save()
        return True

    def delete(self, name: str) -> bool:
        """Delete track."""
        if self._tracks.pop(name.strip().lower(), None) is None:
            return False
        self._save()
        return True

    def add(self, name: str, group: str, index: int | None = None) -> bool:
        """Insert group into track."""
        track = self._tracks.get(name.strip().lower())
        group = group.strip().lower()
        if track is None or not group or group in track or self._groups is None or group not in self._groups:
            return False
        track.insert(len(track) if index is None else max(0, index), group)
        self._save()
        return True

    def remove(self, name: str, group: str) -> bool:
        """Remove group from track."""
        track = self._tracks.get(name.strip().lower())
        if track is None or group.strip().lower() not in track:
            return False
        track.remove(group.strip().lower())
        self._save()
        return True

    def move(self, name: str, group: str, step: int) -> str | None:
        """Calculate promoted or demoted group without mutating user."""
        track = self._tracks.get(name.strip().lower(), [])
        try:
            return track[track.index(group.strip().lower()) + step]
        except (ValueError, IndexError):
            return None

    def promote(self, name: str, group: str) -> str | None:
        """Calculate next group."""
        return self.move(name, group, 1)

    def demote(self, name: str, group: str) -> str | None:
        """Calculate prior group."""
        return self.move(name, group, -1)
