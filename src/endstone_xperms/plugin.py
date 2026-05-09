from endstone import ColorFormat, Player
from endstone.command import Command, CommandSender
from endstone.plugin import Plugin
from typing_extensions import override

from .listener import XPermsListener
from .storage import Storage


class XPermsPlugin(Plugin):
    prefix = "XPerms"
    api_version = "0.11"

    commands = {
        "xperms": {
            "description": "Quản lý group, rank và permission của người chơi",
            "usages": [
                "/xperms groups",
                "/xperms create <name: str>",
                "/xperms delete <name: str>",
                "/xperms info <name: str>",
                "/xperms setformat <name: str> <prefix: message>",
                "/xperms setprefix <name: str> <prefix: message>",
                "/xperms setsuffix <name: str> <suffix: message>",
                "/xperms addperm <name: str> <perm: str>",
                "/xperms removeperm <name: str> <perm: str>",
                "/xperms setgroup <player: str> <group: str>",
                "/xperms playerinfo <player: str>",
                "/xperms reload",
            ],
            "permissions": ["xperms.admin"],
        },
    }

    permissions = {
        "xperms.admin": {
            "description": "Cho phép sử dụng tất cả lệnh /xperms",
            "default": "op",
        },
    }

    @override
    def on_enable(self) -> None:
        self.storage = Storage(str(self.data_folder))
        self._listener = XPermsListener(self)
        self.register_events(self._listener)

        self.logger.info(f"XPerms v1.0.0 enabled! Loaded {len(self.storage.get_all_groups())} groups.")

    @override
    def on_disable(self) -> None:
        self.storage.save()
        self.logger.info("XPerms disabled. Data saved.")

    @override
    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        if command.name != "xperms":
            return False

        if not args:
            self._send_help(sender)
            return True

        action = args[0].lower()
        if action == "groups":
            return self._cmd_groups(sender)
        elif action == "create" and len(args) >= 2:
            return self._cmd_create_group(sender, args[1])
        elif action == "delete" and len(args) >= 2:
            return self._cmd_delete_group(sender, args[1])
        elif action == "info" and len(args) >= 2:
            return self._cmd_group_info(sender, args[1])
        elif action == "setprefix" and len(args) >= 3:
            return self._cmd_set_prefix(sender, args[1], args[2:])
        elif action == "setsuffix" and len(args) >= 3:
            return self._cmd_set_suffix(sender, args[1], args[2:])
        elif action == "setformat" and len(args) >= 3:
            return self._cmd_set_format(sender, args[1], args[2])
        elif action == "addperm" and len(args) >= 3:
            return self._cmd_add_perm(sender, args[1], args[2])
        elif action == "removeperm" and len(args) >= 3:
            return self._cmd_remove_perm(sender, args[1], args[2])
        # Player management
        elif action == "setgroup" and len(args) >= 3:
            return self._cmd_set_group(sender, args[1], args[2])
        elif action == "playerinfo" and len(args) >= 2:
            return self._cmd_player_info(sender, args[1])
        # Other
        elif action == "reload":
            return self._cmd_reload(sender)
        else:
            self._send_help(sender)
            return True

    def _cmd_groups(self, sender: CommandSender) -> bool:
        groups = self.storage.get_all_groups()
        sender.send_message(f"{ColorFormat.GOLD}===== XPerms Groups =====")
        for name, data in groups.items():
            prefix = data.get("prefix", "")
            perm_count = len(data.get("permissions", []))
            sender.send_message(
                f"{ColorFormat.YELLOW} - {ColorFormat.WHITE}{name} "
                f"{ColorFormat.GRAY}| Prefix: {ColorFormat.RESET}{prefix} "
                f"{ColorFormat.GRAY}| Perms: {ColorFormat.AQUA}{perm_count}"
            )
        sender.send_message(f"{ColorFormat.GOLD}Total: {ColorFormat.WHITE}{len(groups)} groups")
        return True

    def _cmd_create_group(self, sender: CommandSender, group_name: str) -> bool:
        if self.storage.create_group(group_name):
            sender.send_message(f"{ColorFormat.GREEN}Group '{group_name}' created successfully!")
        else:
            sender.send_error_message(f"Group '{group_name}' already exists!")
        return True

    def _cmd_delete_group(self, sender: CommandSender, group_name: str) -> bool:
        if group_name.lower() == "default":
            sender.send_error_message("Cannot delete the 'default' group!")
            return True
        if self.storage.delete_group(group_name):
            sender.send_message(
                f"{ColorFormat.GREEN}Group '{group_name}' deleted. "
                f"Affected users moved to 'default'."
            )
            self._refresh_online_players()
        else:
            sender.send_error_message(f"Group '{group_name}' does not exist!")
        return True

    def _cmd_group_info(self, sender: CommandSender, group_name: str) -> bool:
        group = self.storage.get_group(group_name)
        if group is None:
            sender.send_error_message(f"Group '{group_name}' does not exist!")
            return True
        sender.send_message(f"{ColorFormat.GOLD}===== Group: {group_name} =====")
        sender.send_message(f"{ColorFormat.YELLOW}Prefix: {ColorFormat.RESET}{group.get('prefix', '')}")
        sender.send_message(f"{ColorFormat.YELLOW}Suffix: {ColorFormat.RESET}{group.get('suffix', '')}")
        perms = group.get("permissions", [])
        sender.send_message(f"{ColorFormat.YELLOW}Permissions ({len(perms)}):")
        for p in perms:
            sender.send_message(f"{ColorFormat.GRAY}  - {ColorFormat.WHITE}{p}")
        return True


    def _cmd_set_format(self, sender: CommandSender, group_name: str, format: str) -> bool:
        if self.storage.set_format(group_name, format):
            sender.send_message(
                f"{ColorFormat.GREEN}Chat format of '{group_name}' set to: {ColorFormat.RESET}{format}"
            )
            self._refresh_online_players()
        else:
            sender.send_error_message(f"Group '{group_name}' does not exist!")
        return True

    def _cmd_set_prefix(self, sender: CommandSender, group_name: str, extra: list[str]) -> bool:
        prefix = " ".join(extra)
        if self.storage.set_prefix(group_name, prefix):
            sender.send_message(
                f"{ColorFormat.GREEN}Prefix of '{group_name}' set to: {ColorFormat.RESET}{prefix}"
            )
            self._refresh_online_players()
        else:
            sender.send_error_message(f"Group '{group_name}' does not exist!")
        return True

    def _cmd_set_suffix(self, sender: CommandSender, group_name: str, extra: list[str]) -> bool:
        suffix = " ".join(extra)
        if self.storage.set_suffix(group_name, suffix):
            sender.send_message(
                f"{ColorFormat.GREEN}Suffix of '{group_name}' set to: {ColorFormat.RESET}{suffix}"
            )
            self._refresh_online_players()
        else:
            sender.send_error_message(f"Group '{group_name}' does not exist!")
        return True

    def _cmd_add_perm(self, sender: CommandSender, group_name: str, perm: str) -> bool:
        if self.storage.add_permission(group_name, perm):
            sender.send_message(
                f"{ColorFormat.GREEN}Permission '{perm}' added to group '{group_name}'."
            )
        else:
            sender.send_error_message(
                f"Group '{group_name}' does not exist or already has this permission."
            )
        return True

    def _cmd_remove_perm(self, sender: CommandSender, group_name: str, perm: str) -> bool:
        if self.storage.remove_permission(group_name, perm):
            sender.send_message(
                f"{ColorFormat.GREEN}Permission '{perm}' removed from group '{group_name}'."
            )
        else:
            sender.send_error_message(
                f"Group '{group_name}' does not exist or doesn't have this permission."
            )
        return True

    def _cmd_set_group(self, sender: CommandSender, player_name: str, group_name: str) -> bool:
        if self.storage.set_user_group(player_name, group_name):
            sender.send_message(
                f"{ColorFormat.GREEN}Player '{player_name}' is now in group '{group_name}'."
            )
            online_player = self.server.get_player(player_name)
            if online_player:
                self._listener._apply_name_tag(online_player)
                self._listener._apply_permissions(online_player)
        else:
            sender.send_error_message(f"Group '{group_name}' does not exist!")
        return True

    def _cmd_player_info(self, sender: CommandSender, player_name: str) -> bool:
        group_name = self.storage.get_user_group_name(player_name)
        group = self.storage.get_user_group(player_name)
        sender.send_message(f"{ColorFormat.GOLD}===== Player: {player_name} =====")
        sender.send_message(f"{ColorFormat.YELLOW}Group: {ColorFormat.WHITE}{group_name}")
        sender.send_message(f"{ColorFormat.YELLOW}Prefix: {ColorFormat.RESET}{group.get('prefix', '')}")
        sender.send_message(f"{ColorFormat.YELLOW}Suffix: {ColorFormat.RESET}{group.get('suffix', '')}")
        return True

    def _cmd_reload(self, sender: CommandSender) -> bool:
        self.storage.load()
        # self.reload_config()
        self._refresh_online_players()
        sender.send_message(
            f"{ColorFormat.GREEN}XPerms data & config reloaded! "
            f"({len(self.storage.get_all_groups())} groups loaded)"
        )
        return True

    # ================================================================== #
    #  Helper — Cập nhật tất cả player online
    # ================================================================== #

    def _refresh_online_players(self) -> None:
        """Cập nhật lại name tag cho tất cả player đang online."""
        for player in self.server.online_players:
            self._listener._apply_name_tag(player)

    # ================================================================== #
    #  Helper — Hiển thị hướng dẫn sử dụng
    # ================================================================== #

    def _send_help(self, sender: CommandSender) -> None:
        """Gửi tin nhắn hướng dẫn sử dụng lệnh /xperms."""
        sender.send_message(f"{ColorFormat.GOLD}===== XPerms Help =====")
        sender.send_message(f"{ColorFormat.YELLOW}/xperms groups {ColorFormat.GRAY}— List all groups")
        sender.send_message(f"{ColorFormat.YELLOW}/xperms create <name> {ColorFormat.GRAY}— Create group")
        sender.send_message(f"{ColorFormat.YELLOW}/xperms delete <name> {ColorFormat.GRAY}— Delete group")
        sender.send_message(f"{ColorFormat.YELLOW}/xperms info <name> {ColorFormat.GRAY}— Show group info")
        sender.send_message(f"{ColorFormat.YELLOW}/xperms setformat <name> <format> {ColorFormat.GRAY}— Set chat format")
        sender.send_message(
            f"{ColorFormat.YELLOW}/xperms setprefix <name> <prefix> {ColorFormat.GRAY}— Set prefix"
        )
        sender.send_message(
            f"{ColorFormat.YELLOW}/xperms setsuffix <name> <suffix> {ColorFormat.GRAY}— Set suffix"
        )
        sender.send_message(
            f"{ColorFormat.YELLOW}/xperms addperm <name> <perm> {ColorFormat.GRAY}— Add permission"
        )
        sender.send_message(
            f"{ColorFormat.YELLOW}/xperms removeperm <name> <perm> {ColorFormat.GRAY}— Remove permission"
        )
        sender.send_message(
            f"{ColorFormat.YELLOW}/xperms setgroup <player> <group> {ColorFormat.GRAY}— Set player group"
        )
        sender.send_message(f"{ColorFormat.YELLOW}/xperms playerinfo <player> {ColorFormat.GRAY}— Show player info")
        sender.send_message(f"{ColorFormat.YELLOW}/xperms reload {ColorFormat.GRAY}— Reload data & config")
