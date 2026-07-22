import unittest
from types import SimpleNamespace

from endstone_xperms.listener import XPermsListener


class Attachment:
    def __init__(self):
        self.permissions = {}

    def set_permission(self, name, value):
        self.permissions[name] = value


class Player:
    unique_id = "uuid"
    name = "Player"
    name_tag = ""

    def __init__(self):
        self.attachments = []
        self.removed = []
        self.recalculated = 0

    def add_attachment(self, plugin):
        attachment = Attachment()
        self.attachments.append(attachment)
        return attachment

    def remove_attachment(self, attachment):
        self.removed.append(attachment)
        return True

    def recalculate_permissions(self):
        self.recalculated += 1


class AttachmentTest(unittest.TestCase):
    def test_single_attachment_refresh_and_cleanup(self):
        player = Player()
        storage = SimpleNamespace(get_user_group=lambda _: {"prefix": ""})
        plugin = SimpleNamespace(storage=storage, effective_permissions=lambda _: {"a": True, "b": False}, logger=SimpleNamespace(warning=lambda _: None))
        listener = XPermsListener(plugin)
        listener.refresh_permissions(player)
        listener.refresh_permissions(player)
        self.assertEqual(len(listener._player_attachments), 1)
        self.assertEqual(player.attachments[-1].permissions, {"a": True, "b": False})
        self.assertEqual(player.removed, [player.attachments[0]])
        listener.clear_permissions(player)
        self.assertEqual(len(listener._player_attachments), 0)


if __name__ == "__main__":
    unittest.main()
