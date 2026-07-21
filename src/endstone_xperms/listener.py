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
        group = self._plugin.storage.get_user_group(player.name)
        message = event.message
        formatted = group.get("chat_format", "{prefix} {name}{suffix}§r: {message}")
        event.message = ""
        event.format = formatted.replace("{prefix}", group.get("prefix", "")).replace(
            "{name}", player.name
        ).replace("{suffix}", group.get("suffix", "")).replace("{message}", message)

    @event_handler(priority=EventPriority.NORMAL)
    def on_player_join(self, event: PlayerJoinEvent) -> None:
        player = event.player
        storage = self._plugin.storage
        if not storage.has_user(player.name):
            if storage.set_user_group(player.name, storage.default_group):
                self._plugin._schedule_flush()
        self.refresh_player(player)
        self._plugin.logger.info(f"{player.name} joined | Group: {storage.get_user_group_name(player.name)}")

    @event_handler(priority=EventPriority.NORMAL)
    def on_player_quit(self, event: PlayerQuitEvent) -> None:
        self._clear_permissions(event.player)

    def refresh_player(self, player: Player) -> None:
        self.refresh_name_tag(player)
        self.refresh_permissions(player)

    def refresh_permissions(self, player: Player) -> None:
        self._clear_permissions(player)
        permissions = self._plugin.storage.get_user_group(player.name).get("permissions", [])
        if not permissions:
            return
        try:
            attachment = player.add_attachment(self._plugin)
            for permission in permissions:
                attachment.set_permission(permission, True)
            self._player_attachments[player.name.lower()] = attachment
        except Exception as error:
            self._plugin.logger.warning(f"Could not apply permissions to {player.name}: {error}")

    def refresh_name_tag(self, player: Player) -> None:
        prefix = self._plugin.storage.get_user_group(player.name).get("prefix", "")
        player.name_tag = f"{prefix} §r{player.name}" if prefix else player.name

    def refresh_permissions_for_group(self, group_name: str) -> None:
        for player in self._plugin.server.online_players:
            if self._plugin.storage.get_user_group_name(player.name) == group_name.lower():
                self.refresh_permissions(player)

    def refresh_name_tags_for_group(self, group_name: str) -> None:
        for player in self._plugin.server.online_players:
            if self._plugin.storage.get_user_group_name(player.name) == group_name.lower():
                self.refresh_name_tag(player)

    def refresh_all_players(self) -> None:
        for player in self._plugin.server.online_players:
            self.refresh_player(player)

    def _clear_permissions(self, player: Player) -> None:
        key = player.name.lower()
        attachment = self._player_attachments.pop(key, None)
        if attachment is None:
            return
        try:
            player.remove_attachment(attachment)
        except Exception as error:
            self._plugin.logger.warning(f"Could not remove attachment from {player.name}: {error}")
