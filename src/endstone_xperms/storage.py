import json
import os
import shutil
import tempfile
from typing import Optional


class Storage:
    _DEFAULT_GROUP = {
        "prefix": "§7[Member]",
        "suffix": "",
        "permissions": [],
        "chat_format": "{prefix} {name}{suffix}§r: {message}",
    }

    def __init__(self, data_folder: str, logger=None) -> None:
        self._file_path = os.path.join(str(data_folder), "data.json")
        self._backup_path = f"{self._file_path}.bak"
        self._logger = logger
        self._groups: dict = {}
        self._users: dict = {}
        self._default_group = "default"
        self._dirty = False
        self.load()

    @property
    def default_group(self) -> str:
        return self._default_group

    @property
    def dirty(self) -> bool:
        return self._dirty

    def _log(self, level: str, message: str) -> None:
        if self._logger:
            getattr(self._logger, level)(message)

    def load(self) -> bool:
        if self._dirty and not self.flush():
            self._log("error", "Reload aborted because dirty storage could not be flushed")
            return False
        if not os.path.exists(self._file_path):
            self._groups = {"default": dict(self._DEFAULT_GROUP)}
            self._users = {}
            self._default_group = "default"
            self._dirty = True
            return self.flush()
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            groups, users, default_group, changed = self._validate(data)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
            self._log("error", f"Cannot load storage '{self._file_path}': {error}")
            if os.path.exists(self._backup_path):
                try:
                    with open(self._backup_path, "r", encoding="utf-8") as f:
                        groups, users, default_group, changed = self._validate(json.load(f))
                    self._groups, self._users, self._default_group = groups, users, default_group
                    self._dirty = True
                    self._log("warning", f"Storage restored from backup '{self._backup_path}'")
                    return True
                except (OSError, json.JSONDecodeError, TypeError, ValueError) as backup_error:
                    self._log("error", f"Cannot load backup '{self._backup_path}': {backup_error}")
            return False
        self._groups, self._users, self._default_group = groups, users, default_group
        self._dirty = changed
        return True

    def _validate(self, data: dict) -> tuple[dict, dict, str, bool]:
        if not isinstance(data, dict):
            raise ValueError("root must be an object")
        raw_groups = data.get("groups", {})
        raw_users = data.get("users", {})
        if not isinstance(raw_groups, dict) or not isinstance(raw_users, dict):
            raise ValueError("groups and users must be objects")
        groups = {}
        changed = False
        for name, raw in raw_groups.items():
            key = str(name).strip().lower()
            if not key or not isinstance(raw, dict):
                changed = True
                continue
            group = dict(self._DEFAULT_GROUP)
            group.update(raw)
            if not all(isinstance(group[field], str) for field in ("prefix", "suffix", "chat_format")):
                changed = True
                continue
            permissions = group["permissions"]
            if not isinstance(permissions, list) or not all(isinstance(p, str) for p in permissions):
                changed = True
                continue
            group["permissions"] = list(dict.fromkeys(permissions))
            groups[key] = group
        if not groups:
            groups["default"] = dict(self._DEFAULT_GROUP)
            changed = True
        default_group = data.get("default_group", "default")
        if not isinstance(default_group, str) or default_group.strip().lower() not in groups:
            self._log("warning", "Configured default group missing; using 'default' or first valid group")
            default_group = "default" if "default" in groups else next(iter(groups))
            changed = True
        else:
            default_group = default_group.strip().lower()
        users = {}
        for name, raw in raw_users.items():
            if not isinstance(raw, dict):
                changed = True
                continue
            group = str(raw.get("group", default_group)).strip().lower()
            if group not in groups:
                group = default_group
                changed = True
            users[str(name).strip().lower()] = {"group": group}
        return groups, users, default_group, changed

    def _mark_dirty(self) -> None:
        self._dirty = True

    def flush(self) -> bool:
        if not self._dirty:
            return True
        os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
        fd, temp_path = tempfile.mkstemp(prefix="data.", suffix=".tmp", dir=os.path.dirname(self._file_path))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump({"default_group": self._default_group, "groups": self._groups, "users": self._users}, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            if os.path.exists(self._file_path):
                shutil.copy2(self._file_path, self._backup_path)
            os.replace(temp_path, self._file_path)
            self._dirty = False
            return True
        except OSError as error:
            self._log("error", f"Cannot save storage '{self._file_path}': {error}")
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            return False

    def save(self) -> bool:
        return self.flush()

    def has_user(self, player_name: str) -> bool:
        return player_name.strip().lower() in self._users

    def create_group(self, name: str) -> bool:
        key = name.strip().lower()
        if not key or key in self._groups:
            return False
        group = dict(self._DEFAULT_GROUP)
        group["prefix"] = f"§f[{name.strip()}]"
        self._groups[key] = group
        self._mark_dirty()
        return True

    def delete_group(self, name: str) -> bool:
        key = name.strip().lower()
        if key == self._default_group or key not in self._groups:
            return False
        del self._groups[key]
        for user_data in self._users.values():
            if user_data["group"] == key:
                user_data["group"] = self._default_group
        self._mark_dirty()
        return True

    def set_default_group(self, name: str) -> bool:
        key = name.strip().lower()
        if key not in self._groups or key == self._default_group:
            return False
        self._default_group = key
        self._mark_dirty()
        return True

    def get_group(self, name: str) -> Optional[dict]:
        return self._groups.get(name.strip().lower())

    def get_all_groups(self) -> dict:
        return self._groups

    def _set_group_value(self, group_name: str, field: str, value: str) -> bool:
        group = self.get_group(group_name)
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
        group = self.get_group(group_name)
        if group is None or permission in group["permissions"]:
            return False
        group["permissions"].append(permission)
        self._mark_dirty()
        return True

    def remove_permission(self, group_name: str, permission: str) -> bool:
        group = self.get_group(group_name)
        if group is None or permission not in group["permissions"]:
            return False
        group["permissions"].remove(permission)
        self._mark_dirty()
        return True

    def set_user_group(self, player_name: str, group_name: str) -> bool:
        group_key = group_name.strip().lower()
        key = player_name.strip().lower()
        if group_key not in self._groups:
            return False
        if key in self._users and self._users[key].get("group") == group_key:
            return False
        self._users.setdefault(key, {})["group"] = group_key
        self._mark_dirty()
        return True

    def get_user_group_name(self, player_name: str) -> str:
        return self._users.get(player_name.strip().lower(), {}).get("group", self._default_group)

    def get_user_group(self, player_name: str) -> dict:
        return self.get_group(self.get_user_group_name(player_name)) or self._groups[self._default_group]
