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
    def __init__(self, plugin: "XPermsPlugin") -> None:
        self._plugin = plugin

    @event_handler(priority=EventPriority.HIGH)
    def on_player_chat(self, event: PlayerChatEvent) -> None:
        player = event.player
        storage = self._plugin.storage
        group = storage.get_user_group(player.name)
        prefix = group.get("prefix", "")
        suffix = group.get("suffix", "")
        chat_format = group.get("chat_format", "{prefix} {name}{suffix}§r: {message}")
        formatted = chat_format.replace("{prefix}", prefix)
        formatted = formatted.replace("{name}", player.name)
        formatted = formatted.replace("{suffix}", suffix)
        formatted = formatted.replace("{message}", event.message)
        event.message = ""
        event.format = formatted

    @event_handler(priority=EventPriority.NORMAL)
    def on_player_join(self, event: PlayerJoinEvent) -> None:
        player = event.player
        storage = self._plugin.storage

        group = storage.get_user_group(player.name)
        default_group = group.get("default_group", "default")
        if player.name.lower() not in storage._data["users"]:
            storage.set_user_group(player.name, default_group)
        self._apply_name_tag(player)
        self._apply_permissions(player)

        self._plugin.logger.info(
            f"{player.name} joined | Group: {storage.get_user_group_name(player.name)}"
        )

    def _apply_name_tag(self, player: Player) -> None:
        storage = self._plugin.storage
        group = storage.get_user_group(player.name)
        prefix = group.get("prefix", "")

        if prefix:
            player.name_tag = f"{prefix} §r{player.name}"
        else:
            player.name_tag = player.name

    def _apply_permissions(self, player: Player) -> None:
        storage = self._plugin.storage
        group = storage.get_user_group(player.name)
        permissions = group.get("permissions", [])

        for perm in permissions:
            try:
                player.add_attachment(self._plugin, perm, True)
            except Exception as e:
                self._plugin.logger.warning(f"Could not attach permission '{perm}' to {player.name}: {e}")
