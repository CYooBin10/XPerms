from __future__ import annotations

from dataclasses import dataclass, field
from time import time
from typing import Any
from uuid import UUID, uuid4


_NODE_KINDS = {"permission", "parent", "prefix", "suffix", "meta"}


def _name(value: str, field_name: str = "name") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip().lower()


def _uuid(value: str | None) -> str:
    if value is None:
        return str(uuid4())
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as error:
        raise ValueError("stable id must be a UUID") from error


@dataclass(frozen=True)
class PermissionNode:
    permission: str
    value: bool = True
    context: dict[str, str] = field(default_factory=dict)
    expires_at: float | None = None
    priority: int = 0
    weight: int = 0
    stable_id: str = field(default_factory=lambda: str(uuid4()), compare=False)
    kind: str = "permission"
    created_at: float = field(default_factory=time, compare=False)
    actor: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "permission", _name(self.permission, "permission"))
        object.__setattr__(self, "stable_id", _uuid(self.stable_id))
        if self.kind not in _NODE_KINDS:
            raise ValueError(f"kind must be one of {sorted(_NODE_KINDS)}")
        if not isinstance(self.value, bool):
            raise ValueError("value must be boolean")
        if not isinstance(self.context, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in self.context.items()):
            raise ValueError("context must contain string keys and values")
        if self.expires_at is not None and not isinstance(self.expires_at, (int, float)):
            raise ValueError("expires_at must be a number or null")
        if not isinstance(self.created_at, (int, float)):
            raise ValueError("created_at must be a number")
        if self.actor is not None and not isinstance(self.actor, str):
            raise ValueError("actor must be a string or null")
        if not isinstance(self.priority, int) or not isinstance(self.weight, int):
            raise ValueError("priority and weight must be integers")

    @property
    def id(self) -> str:
        return self.stable_id

    @property
    def wildcard(self) -> bool:
        return self.permission.endswith(".*")

    def matches(self, permission: str, context: dict[str, str], now: float | None = None) -> bool:
        if self.kind != "permission" or self.expires_at is not None and self.expires_at <= (time() if now is None else now):
            return False
        target = permission.strip().lower()
        if self.wildcard:
            prefix = self.permission[:-2]
            if target != prefix and not target.startswith(prefix + "."):
                return False
        elif target != self.permission:
            return False
        return all(context.get(key) == value for key, value in self.context.items())

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"id": self.stable_id, "permission": self.permission, "value": self.value, "kind": self.kind, "created_at": self.created_at}
        if self.actor is not None:
            data["actor"] = self.actor
        if self.context:
            data["context"] = dict(self.context)
        if self.expires_at is not None:
            data["expires_at"] = self.expires_at
        if self.priority:
            data["priority"] = self.priority
        if self.weight:
            data["weight"] = self.weight
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any] | str) -> PermissionNode:
        if isinstance(data, str):
            return cls(data)
        if not isinstance(data, dict):
            raise ValueError("permission node must be an object or string")
        values = dict(data)
        if "id" in values:
            values["stable_id"] = values.pop("id")
        return cls(**values)


@dataclass
class User:
    name: str
    groups: list[str] = field(default_factory=list)
    primary_group: str | None = None
    permissions: list[PermissionNode] = field(default_factory=list)
    stable_id: str = field(default_factory=lambda: str(uuid4()))
    xuid: str | None = None
    last_known_name: str | None = None

    def __post_init__(self) -> None:
        self.name = _name(self.name)
        self.stable_id = _uuid(self.stable_id)
        self.groups = list(dict.fromkeys(_name(group, "group") for group in self.groups))
        if self.primary_group is not None:
            self.primary_group = _name(self.primary_group, "primary_group")
            if self.primary_group in self.groups:
                self.groups.remove(self.primary_group)
            self.groups.insert(0, self.primary_group)
        self.permissions = [node if isinstance(node, PermissionNode) else PermissionNode.from_dict(node) for node in self.permissions]
        if self.xuid is not None:
            self.xuid = str(self.xuid)
        self.last_known_name = self.last_known_name or self.name

    @property
    def nodes(self) -> list[PermissionNode]:
        return self.permissions

    def to_dict(self) -> dict[str, Any]:
        return {"stable_id": self.stable_id, "xuid": self.xuid, "last_known_name": self.last_known_name, "groups": self.groups, "primary_group": self.primary_group, "nodes": [node.to_dict() for node in self.permissions], "permissions": [node.to_dict() for node in self.permissions]}

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> User:
        if not isinstance(data, dict):
            raise ValueError("user must be an object")
        groups = data.get("groups", [])
        if "group" in data and not groups:
            groups = [data["group"]]
        return cls(name, groups, data.get("primary_group") or (groups[0] if groups else None), data.get("nodes", data.get("permissions", [])), data.get("stable_id") or str(uuid4()), data.get("xuid"), data.get("last_known_name"))


@dataclass
class Group:
    name: str
    permissions: list[PermissionNode] = field(default_factory=list)
    parents: list[str] = field(default_factory=list)
    weight: int = 0
    prefix: str = ""
    suffix: str = ""
    chat_format: str = "{prefix} {name}{suffix}§r: {message}"
    stable_id: str = field(default_factory=lambda: str(uuid4()))
    aliases: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.name = _name(self.name)
        self.stable_id = _uuid(self.stable_id)
        self.permissions = [node if isinstance(node, PermissionNode) else PermissionNode.from_dict(node) for node in self.permissions]
        self.parents = list(dict.fromkeys(_name(parent, "parent") for parent in self.parents))
        self.aliases = list(dict.fromkeys(_name(alias, "alias") for alias in self.aliases))
        if not isinstance(self.weight, int):
            raise ValueError("weight must be an integer")
        if not all(isinstance(value, str) for value in (self.prefix, self.suffix, self.chat_format)):
            raise ValueError("display fields must be strings")

    @property
    def nodes(self) -> list[PermissionNode]:
        return self.permissions

    def to_dict(self) -> dict[str, Any]:
        nodes = [node.to_dict() for node in self.permissions]
        return {"stable_id": self.stable_id, "aliases": self.aliases, "prefix": self.prefix, "suffix": self.suffix, "chat_format": self.chat_format, "nodes": nodes, "permissions": nodes, "parents": self.parents, "weight": self.weight}

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> Group:
        if not isinstance(data, dict):
            raise ValueError("group must be an object")
        values = {key: data[key] for key in ("parents", "weight", "prefix", "suffix", "chat_format", "stable_id", "aliases") if key in data}
        values["permissions"] = data.get("nodes", data.get("permissions", []))
        if "alias" in data and "aliases" not in values:
            values["aliases"] = [data["alias"]] if isinstance(data["alias"], str) else data["alias"]
        return cls(name=name, **values)


@dataclass(frozen=True)
class Track:
    source: str
    permission: str
    value: bool
    matched: bool
    reason: str
    depth: int = 0

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()
