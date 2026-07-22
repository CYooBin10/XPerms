from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Any


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    entity: str | None = None


class Linter:
    def __init__(self, storage: Any, tracks: Any | None = None) -> None:
        self.storage, self.tracks = storage, tracks

    def run(self, now: float | None = None) -> list[Issue]:
        current = time() if now is None else now
        issues: list[Issue] = []
        groups = self.storage._groups
        users = self.storage._users
        if self.storage.default_group not in groups:
            issues.append(Issue("invalid_default", "default group does not exist", self.storage.default_group))
        states: dict[str, int] = {}

        def visit(name: str, path: tuple[str, ...]) -> None:
            if states.get(name) == 1:
                cycle = path[path.index(name):] + (name,)
                issues.append(Issue("cycle", f"group inheritance cycle: {' -> '.join(cycle)}", name))
                return
            if states.get(name) == 2:
                return
            states[name] = 1
            for parent in groups[name].get("parents", []):
                if parent not in groups:
                    issues.append(Issue("missing_parent", f"missing parent group: {parent}", name))
                else:
                    visit(parent, path + (name,))
            states[name] = 2

        for name in sorted(groups):
            visit(name, ())
        for name, user in sorted(users.items()):
            memberships = user.get("groups", [])
            for group in memberships:
                if group not in groups:
                    issues.append(Issue("missing_group", f"missing user group: {group}", name))
            primary = user.get("primary_group")
            if primary not in groups or primary not in memberships:
                issues.append(Issue("invalid_primary", "primary group must be an assigned group", name))
        for kind, entities in (("group", groups), ("user", users)):
            for name, entity in sorted(entities.items()):
                seen: set[tuple] = set()
                for node in entity.get("nodes", entity.get("permissions", [])):
                    try:
                        from .domain import PermissionNode
                        parsed = PermissionNode.from_dict(node)
                    except (TypeError, ValueError):
                        issues.append(Issue("invalid_permission", "invalid permission node", f"{kind}:{name}"))
                        continue
                    key = (parsed.permission, tuple(sorted(parsed.context.items())))
                    if key in seen:
                        issues.append(Issue("duplicate_permission", f"duplicate permission: {parsed.permission}", f"{kind}:{name}"))
                    seen.add(key)
                    if parsed.expires_at is not None and parsed.expires_at <= current:
                        issues.append(Issue("expired_permission", f"expired permission: {parsed.permission}", f"{kind}:{name}"))
        if self.tracks is not None:
            for track, names in self.tracks.all().items():
                for name in names:
                    if name not in groups:
                        issues.append(Issue("missing_track_group", f"missing track group: {name}", track))
        return issues

    def cleanup(self, now: float | None = None) -> set[str]:
        return self.storage.cleanup_expired(now)
