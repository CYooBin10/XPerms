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
        return "1.0.2"

    def on_request(self, player: Optional[Player], params: str) -> Optional[str]:
        if not player:
            return None

        if params == "group":
            return self.plugin.storage.get_user_group_name(player.name)
        
        group = self.plugin.storage.get_user_group(player.name)
        if params == "prefix":
            return group.get("prefix", "")
        elif params == "suffix":
            return group.get("suffix", "")
        
        return None
