import json
import tempfile
import unittest
from pathlib import Path

from endstone_xperms.storage import Storage


class StorageTest(unittest.TestCase):
    def test_cache_defaults_and_atomic_save(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            storage = Storage(folder)
            self.assertTrue(storage.get_group(storage.default_group))
            self.assertTrue(storage.create_group(" VIP "))
            self.assertTrue(storage.set_default_group("VIP"))
            self.assertTrue(storage.set_user_group("Player", "vip"))
            self.assertTrue(storage.flush())
            data = json.loads(Path(folder, "data.json").read_text(encoding="utf-8"))
            self.assertEqual(data["default_group"], "vip")
            self.assertEqual(data["users"]["player"]["group"], "vip")

    def test_invalid_user_group_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "data.json")
            path.write_text(json.dumps({"groups": {"default": {}}, "users": {"p": {"group": "gone"}}}), encoding="utf-8")
            storage = Storage(folder)
            self.assertEqual(storage.get_user_group_name("P"), "default")
            self.assertTrue(storage.dirty)


if __name__ == "__main__":
    unittest.main()
