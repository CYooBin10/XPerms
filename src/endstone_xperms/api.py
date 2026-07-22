from __future__ import annotations

from typing import Any

from .resolver import Resolution, Resolver

class Simulator:
    """Read-only permission simulation facade."""
    def __init__(self, storage: Any) -> None:
        self.storage = storage

    def resolve(self, user: str, permission: str, context: dict[str, str] | None = None, now: float | None = None) -> Resolution:
        """Resolve permission against current storage snapshot."""
        return Resolver(self.storage.users, self.storage.groups, self.storage.default_group).resolve(user, permission, context, now)

    def check(self, user: str, permission: str, context: dict[str, str] | None = None, now: float | None = None) -> bool:
        """Return simulated permission value."""
        return self.resolve(user, permission, context, now).value
