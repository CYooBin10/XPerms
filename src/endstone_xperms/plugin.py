from endstone import ColorFormat, Player
from endstone.command import Command, CommandSender
from endstone.plugin import Plugin
from typing_extensions import override

from .listener import XPermsListener
from .resolver import Resolver
from .storage import Storage
from .api import Simulator
from .linter import Linter
from .tracks import Tracks
from .ui import XPermsUI


class XPermsPlugin(Plugin):
    prefix = "XPerms"
    api_version = "0.11"
    authors = ["CYooBin10"]
    depend = ["jwplaceholderapi"]
    version = "2.0.0"

    commands = {
        "xperms": {
            "description": "Manage player groups, ranks, and permissions",
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
                "/xperms default",
                "/xperms setdefault <group: str>",
                "/xperms lint",
                "/xperms simulate <user: str> <node: str> [context: str]",
                "/xperms audit [limit: int]",
                "/xperms track <action: str> [name: str] [value: str]",
                "/xperms rollback <change_id: str>",
                "/xperms ui",
            ],
            "permissions": ["xperms.admin"],
        },
    }

    permissions = {
        "xperms.admin": {
            "description": "Allow access to all /xperms commands",
            "default": "op",
        },
        "xperms.user": {"description": "Manage user permissions and groups", "default": "op"},
        "xperms.group": {"description": "Manage group inheritance", "default": "op"},
        "xperms.explain": {"description": "Explain effective permissions", "default": "op"},
        "xperms.lint": {"description": "Run permission linter", "default": "op"},
        "xperms.simulate": {"description": "Simulate permission checks", "default": "op"},
        "xperms.audit": {"description": "View permission audit", "default": "op"},
        "xperms.rollback": {"description": "Rollback permission change", "default": "op"},
        "xperms.track": {"description": "Manage permission tracks", "default": "op"},
        "xperms.ui": {"description": "Open XPerms UI", "default": "op"},
    }

    @override
    def on_enable(self) -> None:
        self.storage = Storage(str(self.data_folder), self.logger)
        self.tracks = Tracks(self.data_folder, set(self.storage.groups))
        self.linter = Linter(self.storage, self.tracks)
        self.simulator = Simulator(self.storage)
        self.ui = XPermsUI(self)
        self._context_providers = []
        self._flush_task = None
        self._cleanup_task = self.server.scheduler.run_task(self, self._cleanup_expired, delay=1200, period=1200)
        self._resolver_revision = -1
        self._resolver = None
        self._listener = XPermsListener(self)
        self.register_events(self._listener)

        papi = self.server.plugin_manager.get_plugin("jwplaceholderapi")
        if papi:
            from .xperms_expansion import XPermsExpansion
            try:
                papi.register_expansion(XPermsExpansion(self))
            except Exception as e:
                self.logger.warning(f"Failed to register PlaceholderAPI expansion: {e}")

        self.logger.info(f"XPerms v2.0.1 enabled! Loaded {len(self.storage.get_all_groups())} groups.")

    @override
    def on_disable(self) -> None:
        if self._flush_task:
            self._flush_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
        self._listener.cleanup()
        self.storage.flush()
        self.logger.info("XPerms disabled. Data saved.")

    def _permission_names(self) -> set[str]:
        registered = self.server.plugin_manager.permissions
        names = {str(getattr(permission, "name", permission)).lower() for permission in registered}
        for group in self.storage.groups.values():
            names.update(node.permission for node in group.permissions if not node.wildcard)
        for user in self.storage.users.values():
            names.update(node.permission for node in user.permissions if not node.wildcard)
        return names

    def _get_resolver(self) -> Resolver:
        if self._resolver is None or self._resolver_revision != self.storage.revision:
            self._resolver = Resolver(self.storage.users, self.storage.groups, self.storage.default_group)
            self._resolver_revision = self.storage.revision
        return self._resolver

    def effective_permissions(self, player) -> dict[str, bool]:
        user_id = self.storage.claim_identity(str(player.unique_id), player.name, player.xuid)
        resolver = self._get_resolver()
        context = self._listener.context(player)
        return {name: resolver.check(user_id, name, context) for name in self._permission_names()}

    def _resolve_user(self, identifier: str) -> str:
        player = self.server.get_player(identifier)
        return str(player.unique_id).lower() if player else self.storage.resolve_identity(identifier)

    def _allowed(self, sender: CommandSender, permission: str) -> bool:
        checker = getattr(sender, "has_permission", None)
        return bool(checker("xperms.admin") or checker(permission)) if callable(checker) else True

    def _cleanup_expired(self) -> None:
        for user_id in self.storage.cleanup_expired():
            self.refresh_user(user_id)
        if self.storage.dirty:
            self._schedule_flush()

    def refresh_user(self, user_id: str) -> None:
        key = str(user_id).lower()
        for player in self.server.online_players:
            if str(player.unique_id).lower() == key:
                self._listener.refresh_player(player)

    @override
    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        if command.name != "xperms":
            return False

        if not args:
            self._send_help(sender)
            return True

        action = args[0].lower()
        if action == "ui":
            if not isinstance(sender, Player):
                sender.send_error_message("Only players can open XPerms UI.")
            elif self._allowed(sender, "xperms.ui"):
                self.ui.open(sender)
            return True
        if action == "lint":
            if self._allowed(sender, "xperms.lint"):
                for issue in self.linter.run():
                    sender.send_message(f"{issue.code}: {issue.message}")
            return True
        if action == "simulate" and len(args) >= 3:
            if self._allowed(sender, "xperms.simulate"):
                context = dict(item.split("=", 1) for item in args[3:] if "=" in item)
                sender.send_message(str(self.simulator.resolve(self._resolve_user(args[1]), args[2], context)))
            return True
        if action == "audit":
            if self._allowed(sender, "xperms.audit"):
                limit = int(args[1]) if len(args) > 1 and args[1].isdigit() else 20
                for record in self.storage.audit.recent(limit):
                    sender.send_message(str(record))
            return True
        if action == "track" and len(args) >= 2:
            return self._cmd_track(sender, args[1:])
        if action == "rollback" and len(args) == 2:
            return self._cmd_rollback(sender, args[1])
        if action == "user" and len(args) >= 5:
            return self._cmd_user(sender, args[1:])
        if action == "group" and len(args) == 5 and args[2].lower() == "parent":
            return self._cmd_group(sender, [args[1], f"parent-{args[3].lower()}", args[4]])
        if action == "explain" and len(args) >= 3:
            return self._cmd_explain(sender, args[1], args[2])
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
        elif action == "default":
            return self._cmd_default_group(sender)
        elif action == "setdefault" and len(args) >= 2:
            return self._cmd_set_default_group(sender, args[1])
        else:
            self._send_help(sender)
            return True

    def resolve(self, user, node, context=None):
        return self.simulator.resolve(self._resolve_user(str(user)), node, self._context(context))

    def check(self, user, node, context=None):
        return self.resolve(user, node, context).value

    def explain(self, user, node, context=None):
        return self.resolve(user, node, context)

    def get_user(self, user):
        return self.storage.users.get(self._resolve_user(str(user)))

    def get_group(self, group):
        return self.storage.groups.get(str(group).lower())

    def primary(self, user):
        return self.storage.get_user_group_name(self._resolve_user(str(user)))

    def get_prefix(self, user):
        group = self.storage.get_user_group(self._resolve_user(str(user)))
        return group.get("prefix", "")

    def suffix(self, user):
        group = self.storage.get_user_group(self._resolve_user(str(user)))
        return group.get("suffix", "")

    def meta(self, user):
        group = self.storage.get_user_group(self._resolve_user(str(user)))
        return {"prefix": group.get("prefix", ""), "suffix": group.get("suffix", "")}

    def register_context_provider(self, provider):
        self._context_providers.append(provider)

    def invalidate_user(self, user):
        self.refresh_user(self._resolve_user(str(user)))

    def _context(self, context):
        merged = dict(context or {})
        for provider in self._context_providers:
            values = provider() if callable(provider) else {}
            if values:
                merged.update(values)
        return merged

    def _schedule_flush(self) -> None:
        if self._flush_task and not self._flush_task.is_cancelled:
            return

        def flush() -> None:
            self.storage.flush()
            self._flush_task = None

        self._flush_task = self.server.scheduler.run_task(self, flush, delay=20)

    def _cmd_track(self, sender, args):
        if not self._allowed(sender, "xperms.track"):
            return True
        action = args[0].lower()
        if action == "list":
            for name, groups in self.tracks.all().items():
                sender.send_message(f"{name}: {', '.join(groups)}")
        elif action == "create" and len(args) >= 3:
            self.tracks.create(args[1], args[2:])
        elif action == "delete" and len(args) == 2:
            self.tracks.delete(args[1])
        elif action in {"add", "remove"} and len(args) == 3:
            getattr(self.tracks, action)(args[1], args[2])
        elif action in {"promote", "demote"} and len(args) == 3:
            sender.send_message(str(getattr(self.tracks, action)(args[1], args[2])))
        return True

    def _cmd_rollback(self, sender, change_id):
        if not self._allowed(sender, "xperms.rollback"):
            return True
        try:
            if not self.storage.rollback(change_id, "command"):
                sender.send_error_message("Change not found.")
                return True
        except (RuntimeError, ValueError):
            sender.send_error_message("Rollback conflict or change not found.")
            return True
        self._schedule_flush()
        self._listener.refresh_all_players()
        sender.send_message("Change rolled back.")
        return True

    def _cmd_user(self, sender: CommandSender, args: list[str]) -> bool:
        user_id = self._resolve_user(args[0])
        storage = self.storage
        changed = None
        if len(args) >= 4 and args[1].lower() == "permission":
            action, node = args[2].lower(), args[3]
            if action == "set":
                if len(args) > 5 or (len(args) == 5 and args[4].lower() not in {"true", "false"}):
                    sender.send_error_message("User update failed.")
                    return True
                changed = storage.set_user_permission(user_id, node, len(args) == 4 or args[4].lower() == "true")
            elif action == "unset":
                changed = storage.unset_user_permission(user_id, node)
            elif action == "check":
                sender.send_message(str(self._get_resolver().check(user_id, node)))
                return True
        elif len(args) == 4 and args[1].lower() == "group":
            action, group = args[2].lower(), args[3]
            changed = storage.add_user_group(user_id, group) if action == "add" else storage.remove_user_group(user_id, group) if action == "remove" else storage.set_user_primary(user_id, group) if action == "primary" else None
        if changed:
            self._schedule_flush()
            self.refresh_user(user_id)
            sender.send_message(f"{ColorFormat.GREEN}Updated user '{user_id}'.")
        else:
            sender.send_error_message("User update failed.")
        return True

    def _cmd_group(self, sender: CommandSender, args: list[str]) -> bool:
        group, action, parent = args[0], args[1].lower(), args[2]
        changed = self.storage.add_group_parent(group, parent) if action == "parent-add" else self.storage.remove_group_parent(group, parent) if action == "parent-remove" else False
        if changed:
            self._schedule_flush()
            affected = self.storage.group_descendants(group)
            for player in self.server.online_players:
                if affected.intersection(self.storage.user_groups(str(player.unique_id))):
                    self._listener.refresh_player(player)
            sender.send_message(f"{ColorFormat.GREEN}Updated group '{group}'.")
        else:
            sender.send_error_message("Group update failed.")
        return True

    def _cmd_explain(self, sender: CommandSender, user_id: str, permission: str) -> bool:
        user_id = self._resolve_user(user_id)
        result = self._get_resolver().resolve(user_id, permission)
        sender.send_message(f"{permission}: {result.value}")
        for track in result.trace:
            sender.send_message(f"{track.reason}: {track.source} {track.permission}={track.value}")
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
            self._schedule_flush()
            sender.send_message(f"{ColorFormat.GREEN}Group '{group_name}' created successfully!")
        else:
            sender.send_error_message(f"Group '{group_name}' already exists!")
        return True

    def _cmd_delete_group(self, sender: CommandSender, group_name: str) -> bool:
        if group_name.strip().lower() == self.storage.default_group:
            sender.send_error_message(
                f"Cannot delete the default group '{self.storage.default_group}'!"
            )
            return True
        affected = [
            player for player in self.server.online_players
            if self.storage.get_user_group_name(str(player.unique_id)) == group_name.strip().lower()
        ]
        if self.storage.delete_group(group_name):
            self._schedule_flush()
            sender.send_message(
                f"{ColorFormat.GREEN}Group '{group_name}' deleted. "
                f"Affected users moved to '{self.storage.default_group}'."
            )
            for player in affected:
                self._listener.refresh_player(player)
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
            self._schedule_flush()
            sender.send_message(
                f"{ColorFormat.GREEN}Chat format of '{group_name}' set to: {ColorFormat.RESET}{format}"
            )
        else:
            sender.send_error_message(f"Group '{group_name}' does not exist or format is unchanged!")
        return True

    def _cmd_set_prefix(self, sender: CommandSender, group_name: str, extra: list[str]) -> bool:
        prefix = " ".join(extra)
        if self.storage.set_prefix(group_name, prefix):
            self._schedule_flush()
            sender.send_message(
                f"{ColorFormat.GREEN}Prefix of '{group_name}' set to: {ColorFormat.RESET}{prefix}"
            )
            self._listener.refresh_name_tags_for_group(group_name)
        else:
            sender.send_error_message(f"Group '{group_name}' does not exist or prefix is unchanged!")
        return True

    def _cmd_set_suffix(self, sender: CommandSender, group_name: str, extra: list[str]) -> bool:
        suffix = " ".join(extra)
        if self.storage.set_suffix(group_name, suffix):
            self._schedule_flush()
            sender.send_message(
                f"{ColorFormat.GREEN}Suffix of '{group_name}' set to: {ColorFormat.RESET}{suffix}"
            )
        else:
            sender.send_error_message(f"Group '{group_name}' does not exist or suffix is unchanged!")
        return True

    def _cmd_add_perm(self, sender: CommandSender, group_name: str, perm: str) -> bool:
        if self.storage.add_permission(group_name, perm):
            self._schedule_flush()
            sender.send_message(
                f"{ColorFormat.GREEN}Permission '{perm}' added to group '{group_name}'."
            )
            self._listener.refresh_permissions_for_group(group_name)
        else:
            sender.send_error_message(
                f"Group '{group_name}' does not exist or already has this permission."
            )
        return True

    def _cmd_remove_perm(self, sender: CommandSender, group_name: str, perm: str) -> bool:
        if self.storage.remove_permission(group_name, perm):
            self._schedule_flush()
            sender.send_message(
                f"{ColorFormat.GREEN}Permission '{perm}' removed from group '{group_name}'."
            )
            self._listener.refresh_permissions_for_group(group_name)
        else:
            sender.send_error_message(
                f"Group '{group_name}' does not exist or doesn't have this permission."
            )
        return True

    def _cmd_set_group(self, sender: CommandSender, player_name: str, group_name: str) -> bool:
        if self.storage.set_user_group(player_name, group_name):
            self._schedule_flush()
            sender.send_message(
                f"{ColorFormat.GREEN}Player '{player_name}' is now in group '{group_name}'."
            )
            online_player = self.server.get_player(player_name)
            if online_player:
                self._listener.refresh_player(online_player)
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
        if not self.storage.load():
            sender.send_error_message("XPerms reload failed; active data was kept.")
            return True
        self._listener.refresh_all_players()
        sender.send_message(
            f"{ColorFormat.GREEN}XPerms data & config reloaded! "
            f"({len(self.storage.get_all_groups())} groups loaded)"
        )
        return True

    def _cmd_default_group(self, sender: CommandSender) -> bool:
        sender.send_message(f"Default group: {self.storage.default_group}")
        return True

    def _cmd_set_default_group(self, sender: CommandSender, group_name: str) -> bool:
        if self.storage.set_default_group(group_name):
            self._schedule_flush()
            sender.send_message(f"Default group set to '{self.storage.default_group}'.")
        else:
            sender.send_error_message(f"Group '{group_name}' does not exist or is already default.")
        return True

    # ================================================================== #
    #  Helper — Display usage help
    # ================================================================== #

    def _send_help(self, sender: CommandSender) -> None:
        """Send command usage help message."""
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
