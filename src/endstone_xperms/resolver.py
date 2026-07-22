from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .domain import Group, PermissionNode, Track, User


@dataclass(frozen=True)
class Resolution:
    value: bool
    node: PermissionNode | None
    trace: tuple[Track, ...]


class Resolver:
    def __init__(self, users: dict[str, User], groups: dict[str, Group], default_group: str | None = None) -> None:
        self.users, self.groups, self.default_group = users, groups, default_group
        self._cache: dict[tuple, Resolution] = {}
        self.revision = 0

    def invalidate(self) -> None:
        self.revision += 1
        self._cache.clear()

    def _groups(self, names: Iterable[str], stack: tuple[str, ...] = (), depth: int = 0) -> list[tuple[Group, int]]:
        result = []
        for name in names:
            key = name.lower()
            if key in stack:
                raise ValueError(f"group inheritance cycle: {' -> '.join(stack + (key,))}")
            group = self.groups.get(key) or next((item for item in self.groups.values() if key in item.aliases), None)
            if group:
                result.append((group, depth))
                result.extend(self._groups(group.parents, stack + (key,), depth + 1))
        return result

    def resolve(self, user_name: str, permission: str, context: dict[str, str] | None = None, now: float | None = None) -> Resolution:
        ctx = tuple(sorted((context or {}).items()))
        key = (self.revision, user_name.lower(), permission.lower(), ctx, now)
        if now is None:
            key += (int(__import__('time').time()),)
        if key in self._cache:
            return self._cache[key]
        user = self.users.get(user_name.lower())
        nodes: list[tuple[PermissionNode, str, int, int]] = []
        if user:
            nodes.extend((node, "user", 0, 0) for node in user.permissions)
            names = user.groups
        else:
            names = []
        if not names and self.default_group:
            names = [self.default_group]
        for group, depth in self._groups(names):
            nodes.extend((node, group.name, depth, group.weight) for node in group.permissions)
        matches = [(node, source, depth, weight) for node, source, depth, weight in nodes if node.matches(permission, dict(ctx), now)]
        matches.sort(key=lambda item: (item[1] != "user", item[0].permission != permission.lower(), -len(item[0].context), -item[0].priority, -item[3], item[2], item[0].permission, item[0].stable_id))
        accepted = [Track(source, node.permission, node.value, True, "selected" if index == 0 else "candidate", depth) for index, (node, source, depth, _) in enumerate(matches)]
        matched_ids = {node.stable_id for node, _, _, _ in matches}
        rejected = [Track(source, node.permission, node.value, False, "not matched", depth) for node, source, depth, _ in nodes if node.stable_id not in matched_ids]
        trace = tuple(accepted + rejected)
        result = Resolution(matches[0][0].value if matches else False, matches[0][0] if matches else None, trace)
        self._cache[key] = result
        return result

    def check(self, user_name: str, permission: str, context: dict[str, str] | None = None) -> bool:
        return self.resolve(user_name, permission, context).value
