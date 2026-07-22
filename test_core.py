import json
import tempfile
import unittest
from pathlib import Path

from endstone_xperms.domain import Group, PermissionNode, User
from endstone_xperms.resolver import Resolver
from endstone_xperms.services import expiration, parse_duration
from endstone_xperms.storage import Storage


class CoreTest(unittest.TestCase):
    def test_resolver_order_context_false_and_identity(self):
        groups = {
            "low": Group("low", [PermissionNode("build.*", True)], weight=1),
            "high": Group("high", [PermissionNode("build.place", True, {"world": "nether"})], weight=9),
        }
        users = {"alice": User("Alice", ["low", "high"], "high", [PermissionNode("build.place", False)])}
        resolver = Resolver(users, groups)
        result = resolver.resolve("ALICE", "BUILD.PLACE", {"world": "nether"})
        self.assertFalse(result.value)
        self.assertEqual(result.trace[0].source, "user")
        self.assertEqual(users["alice"].groups, ["high", "low"])

    def test_exact_priority_weight_depth(self):
        groups = {
            "child": Group("child", [PermissionNode("x.*", False, priority=99)], ["parent"], 1),
            "parent": Group("parent", [PermissionNode("x.y", True)], weight=2),
        }
        self.assertTrue(Resolver({}, groups, "child").check("nobody", "x.y"))

    def test_cycle(self):
        groups = {"a": Group("a", parents=["b"]), "b": Group("b", parents=["a"])}
        with self.assertRaisesRegex(ValueError, "cycle"):
            Resolver({}, groups, "a").check("x", "p")

    def test_cache_revision_and_context(self):
        resolver = Resolver({}, {"g": Group("g", [PermissionNode("p", context={"world": "a"})])}, "g")
        one = resolver.resolve("x", "p", {"world": "a"})
        self.assertIs(one, resolver.resolve("x", "p", {"world": "a"}))
        self.assertIsNot(one, resolver.resolve("x", "p", {"world": "b"}))
        resolver.invalidate()
        self.assertIsNot(one, resolver.resolve("x", "p", {"world": "a"}))

    def test_migration_and_temp_expiration(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "data.json")
            path.write_text(json.dumps({"default_group": "default", "groups": {"default": {"permissions": ["legacy.node"]}}, "users": {"Bob": {"group": "default"}}}), encoding="utf-8")
            storage = Storage(folder)
            self.assertTrue(storage.dirty)
            self.assertEqual(storage.users["bob"].primary_group, "default")
            storage.flush()
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["schema_version"], 2)
        self.assertEqual(parse_duration("1d2h3m4s"), 93784)
        self.assertEqual(expiration("2m", 10), 130)
        self.assertFalse(PermissionNode("p", expires_at=9).matches("p", {}, 10))


if __name__ == "__main__":
    unittest.main()
