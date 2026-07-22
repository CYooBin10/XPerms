from __future__ import annotations

import json
import os
import shutil
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional

from .audit import Audit
from .domain import Group, PermissionNode, User
from .transaction import Transaction


class Storage:
    SCHEMA_VERSION = 2
    _DEFAULT_GROUP = {"prefix": "§7[Member]", "suffix": "", "permissions": [], "chat_format": "{prefix} {name}{suffix}§r: {message}"}

    def __init__(self, data_folder: str, logger=None) -> None:
        self._file_path = os.path.join(str(data_folder), "data.json")
        self._backup_path = f"{self._file_path}.bak"
        self._logger = logger
        self._groups: dict[str, dict] = {}
        self._users: dict[str, dict] = {}
        self._default_group = "default"
        self._dirty = False
        self.revision = 0
        self._identity_maps = {"name_index": {}, "xuid": {}}
        self.audit = Audit(data_folder)
        self.load()

    def transaction(self, actor: str | None = None, action: str = "update", dry_run: bool = False) -> Transaction:
        return Transaction(self, actor, action, dry_run)

    @property
    def default_group(self) -> str:
        return self._default_group

    @property
    def dirty(self) -> bool:
        return self._dirty

    @property
    def groups(self) -> dict[str, Group]:
        return {name: Group.from_dict(name, data) for name, data in self._groups.items()}

    @property
    def users(self) -> dict[str, User]:
        return {name: User.from_dict(name, data) for name, data in self._users.items()}

    def _log(self, level: str, message: str) -> None:
        if self._logger:
            getattr(self._logger, level)(message)

    def _decode(self, data: Any) -> tuple[dict, dict, str, dict[str, dict[str, str]], bool]:
        if not isinstance(data, dict):
            raise ValueError("root must be an object")
        version = data.get("schema_version")
        if version is not None and version not in (1, self.SCHEMA_VERSION):
            raise ValueError("unsupported schema version")
        changed = version != self.SCHEMA_VERSION
        raw_groups, raw_users = data.get("groups", {}), data.get("users", {})
        if not isinstance(raw_groups, dict) or not isinstance(raw_users, dict):
            raise ValueError("groups and users must be objects")
        groups: dict[str, dict] = {}
        for name, raw in raw_groups.items():
            try:
                group = Group.from_dict(name, raw)
                groups[group.name] = group.to_dict()
            except (TypeError, ValueError):
                changed = True
        if not groups:
            groups["default"] = Group.from_dict("default", self._DEFAULT_GROUP).to_dict()
            changed = True
        default = str(data.get("default_group", "default")).strip().lower()
        if default not in groups:
            default = "default" if "default" in groups else next(iter(groups))
            changed = True
        users: dict[str, dict] = {}
        for name, raw in raw_users.items():
            try:
                user = User.from_dict(name, raw)
                valid = [group for group in user.groups if group in groups]
                if not valid:
                    valid = [default]
                primary = user.primary_group if user.primary_group in valid else valid[0]
                if valid != user.groups or primary != user.primary_group:
                    changed = True
                users[user.name] = User(user.name, valid, primary, user.permissions).to_dict()
                users[user.name]["group"] = primary
            except (TypeError, ValueError):
                changed = True
        raw_maps = data.get("identity_maps", {})
        if not isinstance(raw_maps, dict):
            raise ValueError("identity_maps must be an object")
        maps = {"name_index": {}, "xuid": {}}
        for map_name in maps:
            raw_map = raw_maps.get(map_name, {})
            if not isinstance(raw_map, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in raw_map.items()):
                raise ValueError(f"identity_maps.{map_name} must contain string keys and values")
            maps[map_name].update({key.lower(): value.lower() for key, value in raw_map.items() if value.lower() in users})
        for key, user in users.items():
            maps["name_index"][user["last_known_name"].lower()] = key
            if user.get("xuid"):
                maps["xuid"][user["xuid"].lower()] = key
        if maps != raw_maps:
            changed = True
        return groups, users, default, maps, changed

    def load(self) -> bool:
        if self._dirty and not self.flush():
            return False
        path = Path(self._file_path)
        if not path.exists():
            self._groups = {"default": Group.from_dict("default", self._DEFAULT_GROUP).to_dict()}
            self._users, self._default_group, self._dirty = {}, "default", True
            return self.flush()
        for candidate in (path, Path(self._backup_path)):
            try:
                groups, users, default, maps, changed = self._decode(json.loads(candidate.read_text(encoding="utf-8")))
                self._groups, self._users, self._default_group, self._identity_maps, self._dirty = groups, users, default, maps, changed or candidate != path
                self.revision += 1
                return True
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
                self._log("error", f"Cannot load storage '{candidate}': {error}")
        return False

    def _mark_dirty(self) -> None:
        self._dirty = True
        self.revision += 1

    def flush(self) -> bool:
        if not self._dirty:
            return True
        folder = os.path.dirname(self._file_path)
        os.makedirs(folder, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix="data.", suffix=".tmp", dir=folder)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump({"schema_version": self.SCHEMA_VERSION, "default_group": self._default_group, "identity_maps": self._identity_maps, "groups": self._groups, "users": self._users}, stream, indent=2, ensure_ascii=False)
                stream.flush()
                os.fsync(stream.fileno())
            if os.path.exists(self._file_path):
                shutil.copy2(self._file_path, self._backup_path)
            os.replace(temporary, self._file_path)
            self._dirty = False
            return True
        except OSError as error:
            self._log("error", f"Cannot save storage '{self._file_path}': {error}")
            try:
                os.unlink(temporary)
            except OSError:
                pass
            return False

    save = flush

    def has_user(self, user_id: str) -> bool:
        return str(user_id).strip().lower() in self._users

    def resolve_identity(self, identifier: str) -> str:
        key = str(identifier).strip().lower()
        return self._identity_maps["name_index"].get(key, key)

    def cleanup_expired(self, now: float | None = None) -> set[str]:
        import time
        current = time.time() if now is None else now
        affected: set[str] = set()
        for key, user in self._users.items():
            nodes = user.get("nodes", user.get("permissions", []))
            kept = [node for node in nodes if node.get("expires_at") is None or node["expires_at"] > current]
            if len(kept) != len(nodes):
                user["nodes"] = user["permissions"] = kept
                affected.add(key)
        for key, group in self._groups.items():
            nodes = group.get("nodes", group.get("permissions", []))
            kept = [node for node in nodes if node.get("expires_at") is None or node["expires_at"] > current]
            if len(kept) != len(nodes):
                group["nodes"] = group["permissions"] = kept
                affected.update(user_key for user_key, user in self._users.items() if key in user.get("groups", []))
        if affected:
            self._mark_dirty()
        return affected

    def group_descendants(self, group_name: str) -> set[str]:
        root = group_name.strip().lower()
        result = {root}
        changed = True
        while changed:
            changed = False
            for name, group in self._groups.items():
                if name not in result and any(parent in result for parent in group.get("parents", [])):
                    result.add(name)
                    changed = True
        return result

    def claim_identity(self, user_id: str, legacy_name: str, xuid: str = "") -> str:
        key, legacy, xuid = str(user_id).strip().lower(), legacy_name.strip().lower(), str(xuid).strip()
        if not key:
            raise ValueError("user_id must be non-empty")
        existing = self._identity_maps["xuid"].get(xuid.lower()) if xuid else None
        key = existing or self._identity_maps["name_index"].get(legacy) or key
        user = self._users.pop(legacy, None) if key not in self._users else self._users[key]
        if user is None:
            user = User(key, [self._default_group], self._default_group, last_known_name=legacy_name).to_dict()
        changed = key not in self._users or user.get("xuid") != (xuid or None) or user.get("last_known_name") != legacy_name
        user["xuid"], user["last_known_name"] = xuid or None, legacy_name
        self._users[key] = user
        self._identity_maps["name_index"][legacy] = key
        if xuid:
            self._identity_maps["xuid"][xuid.lower()] = key
        if changed:
            self._mark_dirty()
        return key

    def user_groups(self, user_id: str) -> tuple[str, ...]:
        user = self._users.get(str(user_id).strip().lower())
        return tuple(user["groups"]) if user else (self._default_group,)

    def user(self, user_id: str) -> User:
        key = str(user_id).strip().lower()
        raw = self._users.get(key)
        return User.from_dict(key, raw) if raw else User(key, [self._default_group], self._default_group)

    def set_user_permission(self, user_id: str, permission: str, value: bool, *args, **kwargs) -> bool:
        key, node = str(user_id).strip().lower(), PermissionNode(permission, value, context=kwargs.get("context", {}), expires_at=kwargs.get("expires_at")).to_dict()
        user = self._users.setdefault(key, User(key, [self._default_group], self._default_group).to_dict())
        current = user.get("nodes", user.get("permissions", []))
        exact = next((item for item in current if item.get("permission") == node["permission"]), None)
        if exact is not None and exact.get("value", True) is value and not kwargs:
            return False
        user["nodes"] = [item for item in current if item.get("permission") != node["permission"]] + [node]
        user["permissions"] = user["nodes"]
        self._mark_dirty()
        return True

    def unset_user_permission(self, user_id: str, permission: str) -> bool:
        user = self._users.get(str(user_id).strip().lower())
        if user is None:
            return False
        old = len(user["permissions"])
        user["permissions"] = [item for item in user["permissions"] if item["permission"] != permission.strip().lower()]
        if len(user["permissions"]) == old:
            return False
        self._mark_dirty()
        return True

    def add_user_group(self, user_id: str, group_name: str) -> bool:
        user, group = self._users.get(str(user_id).strip().lower()), group_name.strip().lower()
        if user is None or group not in self._groups or group in user["groups"]:
            return False
        user["groups"].append(group)
        self._mark_dirty()
        return True

    def remove_user_group(self, user_id: str, group_name: str) -> bool:
        user, group = self._users.get(str(user_id).strip().lower()), group_name.strip().lower()
        if user is None or group not in user["groups"] or len(user["groups"]) == 1:
            return False
        user["groups"].remove(group)
        if user["primary_group"] == group:
            user["primary_group"] = user["groups"][0]
        self._mark_dirty()
        return True

    def set_user_primary(self, user_id: str, group_name: str) -> bool:
        user, group = self._users.get(str(user_id).strip().lower()), group_name.strip().lower()
        if user is None or group not in user["groups"] or user["primary_group"] == group:
            return False
        user["primary_group"] = group
        user["groups"].remove(group)
        user["groups"].insert(0, group)
        self._mark_dirty()
        return True

    def add_group_parent(self, group_name: str, parent_name: str) -> bool:
        group, parent = self._group(group_name), parent_name.strip().lower()
        if group is None or parent not in self._groups or parent in group["parents"] or group_name.strip().lower() == parent:
            return False
        pending = {group_name.strip().lower(): set(group["parents"]) | {parent}}
        seen = set()
        def visit(name: str) -> bool:
            if name in seen:
                return False
            seen.add(name)
            for child in pending.get(name, set(self._groups.get(name, {}).get("parents", []))):
                if child == group_name.strip().lower() or visit(child):
                    return True
            return False
        if visit(parent):
            return False
        group["parents"].append(parent)
        self._mark_dirty()
        return True

    def remove_group_parent(self, group_name: str, parent_name: str) -> bool:
        group, parent = self._group(group_name), parent_name.strip().lower()
        if group is None or parent not in group["parents"]:
            return False
        group["parents"].remove(parent)
        self._mark_dirty()
        return True

    def create_group(self, name: str) -> bool:
        key = name.strip().lower()
        if not key or key in self._groups:
            return False
        raw = dict(self._DEFAULT_GROUP)
        raw["prefix"] = f"§f[{name.strip()}]"
        self._groups[key] = Group.from_dict(key, raw).to_dict()
        self._mark_dirty()
        return True

    def delete_group(self, name: str) -> bool:
        key = name.strip().lower()
        if key == self._default_group or key not in self._groups:
            return False
        del self._groups[key]
        for group in self._groups.values():
            group["parents"] = [parent for parent in group["parents"] if parent != key]
        for user in self._users.values():
            user["groups"] = [group for group in user["groups"] if group != key] or [self._default_group]
            if user["primary_group"] == key:
                user["primary_group"] = user["groups"][0]
        self._mark_dirty()
        return True

    def set_default_group(self, name: str) -> bool:
        key = name.strip().lower()
        if key not in self._groups or key == self._default_group:
            return False
        self._default_group = key
        self._mark_dirty()
        return True

    def _group(self, name: str) -> Optional[dict]:
        return self._groups.get(name.strip().lower())

    def get_group(self, name: str) -> Optional[dict]:
        return deepcopy(self._group(name))

    def get_all_groups(self) -> dict:
        return deepcopy(self._groups)

    def snapshot(self) -> dict[str, Any]:
        return {"revision": self.revision, "groups": deepcopy(self._groups), "users": deepcopy(self._users), "default_group": self._default_group, "identity_maps": deepcopy(self._identity_maps)}

    def restore(self, snapshot: dict[str, Any], expected_revision: int | None = None, revision: int | None = None) -> None:
        if expected_revision is not None and self.revision != expected_revision:
            raise RuntimeError("storage revision conflict")
        self._groups = deepcopy(snapshot["groups"])
        self._users = deepcopy(snapshot["users"])
        self._default_group = snapshot["default_group"]
        self._identity_maps = deepcopy(snapshot["identity_maps"])
        self._dirty = True
        if revision is not None:
            self.revision = revision

    def rollback(self, change_id: str, actor: str | None = None) -> bool:
        record = self.audit.get(change_id)
        if record is None or "before" not in record or "after" not in record:
            raise ValueError("unknown change_id")
        if self.snapshot() != record["after"]:
            raise RuntimeError("storage revision conflict")
        before = record["before"]
        self.restore(before, self.revision, before["revision"] + 1)
        self.audit.record("rollback", actor, change_id=str(__import__("uuid").uuid4()), source=change_id, before=record["after"], after=self.snapshot(), revision=self.revision)
        return True

    def _set_group_value(self, group_name: str, field: str, value: str) -> bool:
        group = self._group(group_name)
        if group is None or group[field] == value:
            return False
        group[field] = value
        self._mark_dirty()
        return True

    def set_format(self, group_name: str, format: str) -> bool:
        return self._set_group_value(group_name, "chat_format", format)

    def set_prefix(self, group_name: str, prefix: str) -> bool:
        return self._set_group_value(group_name, "prefix", prefix)

    def set_suffix(self, group_name: str, suffix: str) -> bool:
        return self._set_group_value(group_name, "suffix", suffix)

    def add_permission(self, group_name: str, permission: str) -> bool:
        group = self._group(group_name)
        node = PermissionNode(permission).to_dict()
        if group is None or node in group["permissions"]:
            return False
        group["permissions"].append(node)
        group["nodes"] = group["permissions"]
        self._mark_dirty()
        return True

    def remove_permission(self, group_name: str, permission: str) -> bool:
        group = self._group(group_name)
        if group is None:
            return False
        for node in group["permissions"]:
            if node["permission"] == permission.lower():
                group["permissions"].remove(node)
                group["nodes"] = group["permissions"]
                self._mark_dirty()
                return True
        return False

    def set_user_group(self, player_name: str, group_name: str) -> bool:
        group = group_name.strip().lower()
        key = self._identity_maps["name_index"].get(player_name.strip().lower(), player_name.strip().lower())
        if group not in self._groups:
            return False
        current = self._users.get(key)
        if current and current["primary_group"] == group and current["groups"] == [group]:
            return False
        self._users[key] = User(key, [group], group).to_dict()
        self._users[key]["group"] = group
        self._mark_dirty()
        return True

    def get_user_group_name(self, player_name: str) -> str:
        key = self.resolve_identity(player_name)
        return self._users.get(key, {}).get("primary_group", self._default_group)

    def get_user_group(self, player_name: str) -> dict:
        return self._group(self.get_user_group_name(player_name)) or self._groups[self._default_group]
