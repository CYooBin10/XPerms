__version__ = "2.0.1"
__all__ = ["XPermsPlugin", "Storage", "Resolver", "Resolution", "PermissionNode", "User", "Group", "parse_duration", "expiration"]

from .domain import Group, PermissionNode, User
from .resolver import Resolution, Resolver
from .services import expiration, parse_duration
from .storage import Storage


def __getattr__(name: str):
    if name == "XPermsPlugin":
        from .plugin import XPermsPlugin

        return XPermsPlugin
    raise AttributeError(name)
