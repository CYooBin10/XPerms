from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any
from uuid import uuid4


class Transaction(AbstractContextManager["Transaction"]):
    """Batch storage mutations into one validated revision."""

    def __init__(self, storage: Any, actor: str | None = None, action: str = "update", dry_run: bool = False) -> None:
        self.storage, self.actor, self.action, self.dry_run = storage, actor, action, dry_run
        self.before: dict[str, Any] = {}
        self.affected_users: set[str] = set()

    def __enter__(self) -> Transaction:
        self.before = self.storage.snapshot()
        return self

    def affect(self, *users: str) -> None:
        """Mark users requiring permission refresh."""
        self.affected_users.update(user.strip().lower() for user in users)

    def __exit__(self, error_type: object, error: object, traceback: object) -> bool:
        changed = self.storage.snapshot() != self.before
        if error_type or self.dry_run:
            self.storage.restore(self.before, self.storage.revision, self.before["revision"])
            return False
        if not changed:
            return False
        from .linter import Linter
        fatal = next((issue for issue in Linter(self.storage).run() if issue.code == "cycle"), None)
        if fatal:
            self.storage.restore(self.before, self.storage.revision, self.before["revision"])
            raise ValueError(fatal.message)
        self.storage.revision = self.before["revision"] + 1
        after = self.storage.snapshot()
        self.storage.audit.record(self.action, self.actor, change_id=str(uuid4()), source=self.action, before=self.before, after=after, revision=self.storage.revision)
        return False
