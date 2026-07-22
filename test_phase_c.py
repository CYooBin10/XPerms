import tempfile
import unittest
from pathlib import Path

from endstone_xperms.linter import Linter
from endstone_xperms.storage import Storage
from endstone_xperms.tracks import Tracks


class PhaseCTest(unittest.TestCase):
    def test_transaction_audit_dry_run_and_rollback(self):
        with tempfile.TemporaryDirectory() as folder:
            storage = Storage(folder)
            with storage.transaction("tester", "create", dry_run=True):
                storage.create_group("vip")
            self.assertIsNone(storage.get_group("vip"))
            with storage.transaction("tester", "create"):
                storage.create_group("vip")
            records = storage.audit.recent()
            self.assertTrue(records)
            change_id = records[-1]["change_id"]
            self.assertTrue(storage.rollback(change_id, "tester"))
            self.assertIsNone(storage.get_group("vip"))

    def test_linter_and_atomic_track(self):
        with tempfile.TemporaryDirectory() as folder:
            storage = Storage(folder)
            storage.create_group("child")
            self.assertFalse(storage.add_group_parent("child", "missing"))
            self.assertFalse(Linter(storage).run())
            tracks = Tracks(folder, set(storage.groups))
            self.assertTrue(tracks.create("ranks", ["default", "child"]))
            self.assertEqual(tracks.promote("ranks", "default"), "child")
            self.assertTrue(Path(folder, "tracks.json").exists())


if __name__ == "__main__":
    unittest.main()
