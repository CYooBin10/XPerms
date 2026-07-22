from typing import Optional
from endstone import Player

try:
    from jwplaceholderapi.expansion import PlaceholderExpansion
except ImportError:
    PlaceholderExpansion = object


class XPermsExpansion(PlaceholderExpansion):
    def __init__(self, plugin):
        self.plugin = plugin
        super().__init__()

    def get_identifier(self) -> str:
        return "xperm"

    def get_author(self) -> str:
        return "CYooBin10"

    def get_version(self) -> str:
        return "2.0.1"

    def on_request(self, player: Optional[Player], params: str) -> str:
        if not player:
            return ""
        storage = self.plugin.storage
        user_id = storage.claim_identity(str(player.unique_id), player.name, player.xuid)
        user = storage.user(user_id)
        group = storage.get_group(user.primary_group) or storage.get_group(storage.default_group) or {}
        key = params.lower()
        if key in {"group", "primary_group"}:
            return user.primary_group
        if key == "all_groups":
            return ",".join(user.groups)
        if key == "prefix":
            return str(group.get("prefix", ""))
        if key == "suffix":
            return str(group.get("suffix", ""))
        if key == "permission":
            return str(self.plugin.effective_permissions(player))
        if key.startswith("permission_"):
            return str(self.plugin._get_resolver().check(user_id, key[11:], self.plugin._listener.context(player))).lower()
        if key == "context":
            return str(self.plugin._listener.context(player))
        return ""
