"""
storage.py — Hệ thống lưu trữ dữ liệu cho XPerms.

Lưu trữ thông tin Group (rank) và User (người chơi) bằng file JSON đơn giản.
File dữ liệu nằm tại: plugins/XPerms/data.json
"""

import json
import os
from typing import Optional


class Storage:
    """Đọc/ghi dữ liệu group và user từ file JSON."""

    def __init__(self, data_folder: str) -> None:
        """
        Args:
            data_folder: Đường dẫn đến thư mục data của plugin (plugin.data_folder).
        """
        self._file_path = os.path.join(data_folder, "data.json")
        self._data: dict = {"groups": {}, "users": {}}
        self.load()

    # ------------------------------------------------------------------ #
    #  Đọc / Ghi file
    # ------------------------------------------------------------------ #

    def load(self) -> None:
        """Đọc dữ liệu từ file JSON. Nếu file chưa tồn tại, tạo dữ liệu mặc định."""
        if os.path.exists(self._file_path):
            with open(self._file_path, "r", encoding="utf-8") as f:
                self._data = json.load(f)
        else:
            # Tạo dữ liệu mặc định với group "default"
            self._data = {
                "groups": {
                    "default": {
                        "prefix": "§7[Member]",
                        "suffix": "",
                        "permissions": [],
                    }
                },
                "users": {},
            }
            self.save()

    def save(self) -> None:
        """Ghi dữ liệu hiện tại ra file JSON."""
        # Tạo thư mục nếu chưa có
        os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
        with open(self._file_path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------ #
    #  Quản lý Group / Rank
    # ------------------------------------------------------------------ #

    def create_group(self, name: str) -> bool:
        """Tạo group mới. Trả về False nếu group đã tồn tại."""
        key = name.lower()
        if key in self._data["groups"]:
            return False
        self._data["groups"][key] = {
            "prefix": f"§f[{name}]",
            "suffix": "",
            "permissions": [],
        }
        self.save()
        return True

    def delete_group(self, name: str) -> bool:
        """Xóa group. Trả về False nếu group không tồn tại hoặc là 'default'."""
        key = name.lower()
        if key == "default":
            return False  # Không cho xóa group mặc định
        if key not in self._data["groups"]:
            return False
        del self._data["groups"][key]
        # Chuyển tất cả user đang dùng group này về "default"
        for user_data in self._data["users"].values():
            if user_data.get("group", "").lower() == key:
                user_data["group"] = "default"
        self.save()
        return True

    def get_group(self, name: str) -> Optional[dict]:
        """Lấy thông tin group theo tên. Trả về None nếu không tìm thấy."""
        return self._data["groups"].get(name.lower())

    def get_all_groups(self) -> dict:
        """Trả về dict chứa tất cả các group."""
        return self._data["groups"]

    def set_prefix(self, group_name: str, prefix: str) -> bool:
        """Đặt prefix cho group. Trả về False nếu group không tồn tại."""
        group = self.get_group(group_name)
        if group is None:
            return False
        group["prefix"] = prefix
        self.save()
        return True

    def set_suffix(self, group_name: str, suffix: str) -> bool:
        """Đặt suffix cho group. Trả về False nếu group không tồn tại."""
        group = self.get_group(group_name)
        if group is None:
            return False
        group["suffix"] = suffix
        self.save()
        return True

    def add_permission(self, group_name: str, permission: str) -> bool:
        """Thêm permission vào group. Trả về False nếu group không tồn tại hoặc đã có."""
        group = self.get_group(group_name)
        if group is None:
            return False
        if permission in group["permissions"]:
            return False
        group["permissions"].append(permission)
        self.save()
        return True

    def remove_permission(self, group_name: str, permission: str) -> bool:
        """Xóa permission khỏi group. Trả về False nếu group không tồn tại hoặc chưa có."""
        group = self.get_group(group_name)
        if group is None:
            return False
        if permission not in group["permissions"]:
            return False
        group["permissions"].remove(permission)
        self.save()
        return True

    # ------------------------------------------------------------------ #
    #  Quản lý User / Player
    # ------------------------------------------------------------------ #

    def set_user_group(self, player_name: str, group_name: str) -> bool:
        """Gán group cho player. Trả về False nếu group không tồn tại."""
        if self.get_group(group_name) is None:
            return False
        key = player_name.lower()
        if key not in self._data["users"]:
            self._data["users"][key] = {}
        self._data["users"][key]["group"] = group_name.lower()
        self.save()
        return True

    def get_user_group_name(self, player_name: str) -> str:
        """Lấy tên group của player. Mặc định trả về 'default'."""
        key = player_name.lower()
        user = self._data["users"].get(key)
        if user is None:
            return "default"
        return user.get("group", "default")

    def get_user_group(self, player_name: str) -> dict:
        """Lấy thông tin group của player (trả về dict group)."""
        group_name = self.get_user_group_name(player_name)
        group = self.get_group(group_name)
        # Fallback về default nếu group bị xóa
        if group is None:
            return self.get_group("default") or {"prefix": "", "suffix": "", "permissions": []}
        return group
