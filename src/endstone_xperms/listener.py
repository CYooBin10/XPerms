from typing import TYPE_CHECKING

from endstone import Player
from endstone.event import (
    EventPriority,
    PlayerChatEvent,
    PlayerDimensionChangeEvent,
    PlayerGameModeChangeEvent,
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
        group = self._plugin.storage.get_user_group(str(player.unique_id))
        message = event.message
        event.message = ""
        event.format = group.get(
            "chat_format", "{prefix} {name}{suffix}§r: {message}"
        ).replace("{prefix}", group.get("prefix", "")).replace(
            "{name}", player.name
        ).replace("{suffix}", group.get("suffix", "")).replace("{message}", message)

    @event_handler(priority=EventPriority.NORMAL)
    def on_player_join(self, event: PlayerJoinEvent) -> None:
        player = event.player
        self._plugin.storage.claim_identity(str(player.unique_id), player.name, player.xuid)
        self._plugin._schedule_flush()
        self.refresh_player(player)

    @event_handler(priority=EventPriority.NORMAL)
    def on_player_quit(self, event: PlayerQuitEvent) -> None:
        self.clear_permissions(event.player)

    @event_handler(priority=EventPriority.NORMAL)
    def on_player_game_mode_change(self, event: PlayerGameModeChangeEvent) -> None:
        self.refresh_permissions(event.player)

    @event_handler(priority=EventPriority.NORMAL)
    def on_player_dimension_change(self, event: PlayerDimensionChangeEvent) -> None:
        self.refresh_permissions(event.player)

    def context(self, player: Player) -> dict[str, str]:
        return {
            "server": "default",
            "level": str(player.level.name).lower(),
            "dimension": str(player.dimension.name).lower(),
            "game_mode": str(player.game_mode.name).lower(),
            "device_os": player.device_os.lower(),
            "xuid_present": str(bool(player.xuid)).lower(),
        }

    def refresh_player(self, player: Player) -> None:
        self.refresh_name_tag(player)
        self.refresh_permissions(player)

    def refresh_permissions(self, player: Player) -> None:
        self.clear_permissions(player)
        permissions = self._plugin.effective_permissions(player)
        if permissions:
            try:
                attachment = player.add_attachment(self._plugin)
                for permission, value in permissions.items():
                    attachment.set_permission(permission, value)
                self._player_attachments[str(player.unique_id)] = attachment
            except RuntimeError as error:
                self._plugin.logger.warning(f"Could not apply permissions to {player.name}: {error}")
        player.recalculate_permissions()

    def refresh_name_tag(self, player: Player) -> None:
        group = self._plugin.storage.get_user_group(str(player.unique_id))
        prefix = group.get("prefix", "")
        player.name_tag = f"{prefix} §r{player.name}" if prefix else player.name

    def refresh_permissions_for_group(self, group_name: str) -> None:
        key = group_name.strip().lower()
        for player in self._plugin.server.online_players:
            if key in self._plugin.storage.user_groups(str(player.unique_id)):
                self.refresh_permissions(player)

    def refresh_name_tags_for_group(self, group_name: str) -> None:
        key = group_name.strip().lower()
        for player in self._plugin.server.online_players:
            if self._plugin.storage.get_user_group_name(str(player.unique_id)) == key:
                self.refresh_name_tag(player)

    def refresh_all_players(self) -> None:
        for player in self._plugin.server.online_players:
            self.refresh_player(player)

    def clear_permissions(self, player: Player) -> None:
        attachment = self._player_attachments.pop(str(player.unique_id), None)
        if attachment is None:
            return
        try:
            player.remove_attachment(attachment)
            player.recalculate_permissions()
        except RuntimeError as error:
            self._plugin.logger.warning(f"Could not remove attachment from {player.name}: {error}")

    def cleanup(self) -> None:
        for player in self._plugin.server.online_players:
            self.clear_permissions(player)
        self._player_attachments.clear()
