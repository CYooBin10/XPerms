import json
import os
from typing import Optional


class Storage:
    def __init__(self, data_folder: str) -> None:
        self._file_path = os.path.join(str(data_folder), "data.json")
        self._groups: dict = {}
        self._default_group = "default"
        self.load()

    def load(self) -> None:
        if os.path.exists(self._file_path):
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._groups = data.get("groups", {})
                self._default_group = data.get("default_group", "default")
        else:
            self._groups = {
                "default": {
                    "prefix": "§7[Member]",
                    "suffix": "",
                    "permissions": [],
                    "chat_format": "{prefix} {name}{suffix}§r: {message}"
                }
            }
            self._default_group = "default"
            self.save()

    def save(self) -> None:
        os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
        data_to_save = {
            "default_group": self._default_group,
            "groups": self._groups,
            "users": self._load_all_users()
        }
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=2, ensure_ascii=False)

    def _load_all_users(self) -> dict:
        if not os.path.exists(self._file_path):
            return {}
        with open(self._file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("users", {})

    def _load_user(self, player_name: str) -> dict:
        users = self._load_all_users()
        return users.get(player_name.lower(), {})

    def _save_users(self, users: dict) -> None:
        os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
        data = {
            "default_group": self._default_group,
            "groups": self._groups,
            "users": users
        }
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def create_group(self, name: str) -> bool:
        key = name.lower()
        if key in self._groups:
            return False
        self._groups[key] = {
            "prefix": f"§f[{name}]",
            "suffix": "",
            "permissions": [],
            "chat_format": "{prefix} {name}{suffix}§r: {message}"
        }
        self.save()
        return True

    def delete_group(self, name: str) -> bool:
        key = name.lower()
        if key == "default":
            return False
        if key not in self._groups:
            return False
        del self._groups[key]
        users = self._load_all_users()
        for user_data in users.values():
            if user_data.get("group", "").lower() == key:
                user_data["group"] = "default"
        self._save_users(users)
        return True

    def get_group(self, name: str) -> Optional[dict]:
        return self._groups.get(name.lower())

    def get_all_groups(self) -> dict:
        return self._groups
    
    def set_format(self, group_name: str, format: str) -> bool:
        group = self.get_group(group_name)
        if group is None:
            return False
        group["chat_format"] = format
        self.save()
        return True

    def set_prefix(self, group_name: str, prefix: str) -> bool:
        group = self.get_group(group_name)
        if group is None:
            return False
        group["prefix"] = prefix
        self.save()
        return True

    def set_suffix(self, group_name: str, suffix: str) -> bool:
        group = self.get_group(group_name)
        if group is None:
            return False
        group["suffix"] = suffix
        self.save()
        return True

    def add_permission(self, group_name: str, permission: str) -> bool:
        group = self.get_group(group_name)
        if group is None:
            return False
        if permission in group["permissions"]:
            return False
        group["permissions"].append(permission)
        self.save()
        return True

    def remove_permission(self, group_name: str, permission: str) -> bool:
        group = self.get_group(group_name)
        if group is None:
            return False
        if permission not in group["permissions"]:
            return False
        group["permissions"].remove(permission)
        self.save()
        return True

    def set_user_group(self, player_name: str, group_name: str) -> bool:
        if self.get_group(group_name) is None:
            return False
        key = player_name.lower()
        users = self._load_all_users()
        if key not in users:
            users[key] = {}
        users[key]["group"] = group_name.lower()
        self._save_users(users)
        return True

    def get_user_group_name(self, player_name: str) -> str:
        user = self._load_user(player_name)
        if not user:
            return "default"
        return user.get("group", "default")

    def get_user_group(self, player_name: str) -> dict:
        group_name = self.get_user_group_name(player_name)
        group = self.get_group(group_name)
        if group is None:
            return self.get_group("default") or {"prefix": "", "suffix": "", "permissions": []}
        return group
