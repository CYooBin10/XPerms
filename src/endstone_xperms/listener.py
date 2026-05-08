"""
listener.py — Xử lý sự kiện (Events) cho XPerms.

Lắng nghe các sự kiện PlayerChatEvent và PlayerJoinEvent để:
- Chèn Prefix/Suffix vào tin nhắn chat.
- Cập nhật name tag (tên hiển thị trên đầu) khi người chơi vào server.
"""

from typing import TYPE_CHECKING

from endstone import ColorFormat, Player
from endstone.event import (
    EventPriority,
    PlayerChatEvent,
    PlayerJoinEvent,
    event_handler,
)

if TYPE_CHECKING:
    from .plugin import XPermsPlugin


class XPermsListener:
    """Listener xử lý chat format và name tag cho XPerms."""

    def __init__(self, plugin: "XPermsPlugin") -> None:
        self._plugin = plugin

    # ------------------------------------------------------------------ #
    #  Chat — Chèn prefix/suffix vào tin nhắn
    # ------------------------------------------------------------------ #

    @event_handler(priority=EventPriority.HIGH)
    def on_player_chat(self, event: PlayerChatEvent) -> None:
        player = event.player
        storage = self._plugin.storage

        # Lấy thông tin group của người chơi
        group = storage.get_user_group(player.name)
        prefix = group.get("prefix", "")
        suffix = group.get("suffix", "")

        # Lấy chat format từ config
        chat_format = group.get("chat_format", "{prefix} {name}{suffix}§r: {message}")

        # Thay thế placeholder bằng giá trị thực
        formatted = chat_format.replace("{prefix}", prefix)
        formatted = formatted.replace("{name}", player.name)
        formatted = formatted.replace("{suffix}", suffix)
        formatted = formatted.replace("{message}", event.message)

        # Ghi đè format — Endstone sẽ broadcast chuỗi này thay vì format mặc định
        # Format mặc định của Endstone dùng {0} = tên, {1} = tin nhắn
        # Ta ghi đè hoàn toàn bằng chuỗi đã format sẵn (không còn placeholder)
        event.message = ""
        event.format = formatted

    # ------------------------------------------------------------------ #
    #  Join — Cập nhật name tag và gán group mặc định
    # ------------------------------------------------------------------ #

    @event_handler(priority=EventPriority.NORMAL)
    def on_player_join(self, event: PlayerJoinEvent) -> None:
        """Khi người chơi vào server: gán group mặc định (nếu chưa có) và cập nhật name tag."""
        player = event.player
        storage = self._plugin.storage

        group = storage.get_user_group(player.name)

        # Nếu player chưa có group -> gán group mặc định
        default_group = group.get("default_group", "default")
        # Kiểm tra nếu player là người chơi mới (chưa có entry trong storage)
        if player.name.lower() not in storage._data["users"]:
            storage.set_user_group(player.name, default_group)

        # Cập nhật name tag (tên hiển thị trên đầu người chơi)
        self._apply_name_tag(player)

        # Áp dụng permissions của group cho player
        self._apply_permissions(player)

        self._plugin.logger.info(
            f"{player.name} joined | Group: {storage.get_user_group_name(player.name)}"
        )

    # ------------------------------------------------------------------ #
    #  Helper — Áp dụng name tag và permissions
    # ------------------------------------------------------------------ #

    def _apply_name_tag(self, player: Player) -> None:
        """Đặt name tag cho player theo format: [Prefix] PlayerName."""
        storage = self._plugin.storage
        group = storage.get_user_group(player.name)
        prefix = group.get("prefix", "")

        if prefix:
            player.name_tag = f"{prefix} §r{player.name}"
        else:
            player.name_tag = player.name

    def _apply_permissions(self, player: Player) -> None:
        """Gán tất cả permissions của group cho player thông qua PermissionAttachment."""
        storage = self._plugin.storage
        group = storage.get_user_group(player.name)
        permissions = group.get("permissions", [])

        for perm in permissions:
            try:
                player.add_attachment(self._plugin, perm, True)
            except Exception as e:
                self._plugin.logger.warning(f"Could not attach permission '{perm}' to {player.name}: {e}")
