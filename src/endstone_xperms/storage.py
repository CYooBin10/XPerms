import json
import os
from typing import Optional


class Storage:
    def __init__(self, data_folder: str) -> None:
        self._file_path = os.path.join(str(data_folder), "data.json")
        self._data: dict = {"groups": {}, "users": {}}
        self.load()

    def load(self) -> None:
        if os.path.exists(self._file_path):
            with open(self._file_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            self._data = {
                "default_group": "default",
                "groups": {
                    "default": {
                        "prefix": "§7[Member]",
                        "suffix": "",
                        "permissions": [],
                        "chat_format": "{prefix} {name}{suffix}§r: {message}"
                    }
                },
                "users": {},
            }
            self.save()

    def save(self) -> None:
        os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    def create_group(self, name: str) -> bool:
        key = name.lower()
        if key in self._data["groups"]:
            return False
        self._data["groups"][key] = {
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
        if key not in self._data["groups"]:
            return False
        del self._data["groups"][key]
        for user_data in self._data["users"].values():
            if user_data.get("group", "").lower() == key:
                user_data["group"] = "default"
        self.save()
        return True

    def get_group(self, name: str) -> Optional[dict]:
        return self._data["groups"].get(name.lower())

    def get_all_groups(self) -> dict:
        return self._data["groups"]
    
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
        if key not in self._data["users"]:
            self._data["users"][key] = {}
        self._data["users"][key]["group"] = group_name.lower()
        self.save()
        return True

    def get_user_group_name(self, player_name: str) -> str:
        key = player_name.lower()
        user = self._data["users"].get(key)
        if user is None:
            return "default"
        return user.get("group", "default")

    def get_user_group(self, player_name: str) -> dict:
        group_name = self.get_user_group_name(player_name)
        group = self.get_group(group_name)
        if group is None:
            return self.get_group("default") or {"prefix": "", "suffix": "", "permissions": []}
        return group
