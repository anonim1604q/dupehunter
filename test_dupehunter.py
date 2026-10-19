import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path

from dupehunter.cli import main, parse_size
from dupehunter.core import PARTIAL, apply_action, choose_keeper, find_duplicates


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, data=b"hello"):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main([str(a) for a in args])
        return code, out.getvalue()


class FindTests(Base):
    def test_finds_duplicates(self):
        a, b = self.write("a.txt"), self.write("sub/b.txt")
        self.write("c.txt", b"other")
        res = find_duplicates([self.root])
        self.assertEqual(len(res.groups), 1)
        self.assertEqual(sorted(res.groups[0].files), sorted([a, b]))

    def test_same_size_different_content(self):
        self.write("a", b"aaaa")
        self.write("b", b"bbbb")
        self.assertEqual(find_duplicates([self.root]).groups, [])

    def test_large_files_differing_only_at_end(self):
        base = b"x" * (PARTIAL + 100)
        self.write("a", base)
        self.write("b", base[:-1] + b"y")
        self.write("c", base)
        res = find_duplicates([self.root])
        self.assertEqual(len(res.groups), 1)
        self.assertEqual({f.name for f in res.groups[0].files}, {"a", "c"})

    def test_hardlinks_are_not_duplicates(self):
        a = self.write("a")
        try:
            os.link(a, self.root / "b")
        except (OSError, NotImplementedError):
            self.skipTest("hardlinks unsupported")
        self.assertEqual(find_duplicates([self.root]).groups, [])

    def test_empty_files_and_min_size(self):
        self.write("e1", b"")
        self.write("e2", b"")
        self.write("s1", b"12")
        self.write("s2", b"12")
        self.assertEqual(len(find_duplicates([self.root]).groups), 1)
        self.assertEqual(find_duplicates([self.root], min_size=10).groups, [])

    def test_exclude_and_hidden(self):
        self.write("a.tmp")
        self.write("b.tmp")
        self.write(".hid1")
        self.write(".hid2")
        self.assertEqual(find_duplicates([self.root], excludes=["*.tmp"]).groups, [])
        self.assertEqual(len(find_duplicates([self.root], include_hidden=True,
                                             excludes=["*.tmp"]).groups), 1)


class ActionTests(Base):
    def test_keep_policies(self):
        a, b = self.write("a"), self.write("bb")
        os.utime(a, (1000, 1000))
        os.utime(b, (2000, 2000))
        self.assertEqual(choose_keeper([a, b], "oldest")[0], a)
        self.assertEqual(choose_keeper([a, b], "newest")[0], b)
        self.assertEqual(choose_keeper([a, b], "shortest")[0], a)

    def test_delete_move_hardlink(self):
        keeper = self.write("k")
        d1, d2, d3 = self.write("d1"), self.write("d2"), self.write("d3")
        apply_action("delete", keeper, d1)
        self.assertFalse(d1.exists())
        apply_action("move", keeper, d2, self.root / "trash")
        self.assertTrue((self.root / "trash" / "d2").exists())
        apply_action("hardlink", keeper, d3)
        self.assertTrue(os.path.samefile(keeper, d3))

    def test_refuses_changed_file(self):
        keeper, dup = self.write("k"), self.write("d")
        dup.write_bytes(b"changed")
        with self.assertRaises(RuntimeError):
            apply_action("delete", keeper, dup)
        self.assertTrue(dup.exists())


class CliTests(Base):
    def test_dry_run_changes_nothing_apply_deletes(self):
        a, b = self.write("a"), self.write("b")
        os.utime(a, (1000, 1000))
        code, out = self.run_cli(self.root, "--delete", "-q")
        self.assertEqual(code, 0)
        self.assertTrue(a.exists() and b.exists())
        self.assertIn("Dry run", out)
        self.run_cli(self.root, "--delete", "--apply", "--yes", "-q")
        self.assertTrue(a.exists())
        self.assertFalse(b.exists())

    def test_json_and_fail_on_dupes(self):
        self.write("a")
        self.write("b")
        code, out = self.run_cli(self.root, "--json", "--fail-on-dupes", "-q")
        self.assertEqual(code, 1)
        self.assertIn('"groups"', out)

    def test_parse_size(self):
        self.assertEqual(parse_size("10K"), 10 * 1024)
        self.assertEqual(parse_size("5M"), 5 * 1024**2)
        self.assertEqual(parse_size("500"), 500)


if __name__ == "__main__":
    unittest.main()
