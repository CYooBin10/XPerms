from typing import TYPE_CHECKING

from endstone import Player
from endstone.event import (
    EventPriority,
    PlayerChatEvent,
    PlayerJoinEvent,
    PlayerQuitEvent,
    event_handler,
)

if TYPE_CHECKING:
    from .plugin import XPermsPlugin


class XPermsListener:
    def __init__(self, plugin: "XPermsPlugin") -> None:
        self._plugin = plugin
        self._player_attachments = {}

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

        if not storage.has_user(player.name):
            storage.set_user_group(player.name, storage._default_group)
        self._apply_name_tag(player)
        self._apply_permissions(player)

        self._plugin.logger.info(
            f"{player.name} joined | Group: {storage.get_user_group_name(player.name)}"
        )

    @event_handler(priority=EventPriority.NORMAL)
    def on_player_quit(self, event: PlayerQuitEvent) -> None:
        player_name = event.player.name.lower()
        if player_name in self._player_attachments:
            del self._player_attachments[player_name]

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

        self._clear_permissions(player)

        key = player.name.lower()
        for perm in permissions:
            try:
                attachment = player.add_attachment(self._plugin, perm, True)
                if key not in self._player_attachments:
                    self._player_attachments[key] = []
                self._player_attachments[key].append(attachment)
            except Exception as e:
                self._plugin.logger.warning(f"Could not attach permission '{perm}' to {player.name}: {e}")

    def _clear_permissions(self, player: Player) -> None:
        key = player.name.lower()
        if key in self._player_attachments:
            for attachment in self._player_attachments[key]:
                try:
                    player.remove_attachment(attachment)
                except Exception as e:
                    self._plugin.logger.warning(f"Could not remove attachment from {player.name}: {e}")
            self._player_attachments[key] = []
