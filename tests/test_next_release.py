"""Tests for scripts/next-release.py against tempdir git fixtures (never this repo's tree)."""
import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("next_release", ROOT / "scripts" / "next-release.py")
NEXT = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(NEXT)
GIT_ENV = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null",
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")


class NextReleaseTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="next-release-fixture-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.git("init", "-q", "-b", "main")
        self.commit({"changes/README.md": "not a fragment\n", "changes/old.md": "bump: major\nOld.\n"})

    def git(self, *args):
        subprocess.run(["git", "-C", self.root, *args], check=True, capture_output=True, env=GIT_ENV)

    def commit(self, files):
        for rel, text in files.items():
            Path(self.root, rel).parent.mkdir(parents=True, exist_ok=True)
            Path(self.root, rel).write_text(text, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "work")

    def test_no_tag_falls_back_to_baseline_and_counts_every_fragment(self):
        self.assertEqual(NEXT.plan(self.root), (None, NEXT.BASELINE, "1.0.0", "- Old.\n"))

    def test_no_fragment_since_the_tag_releases_nothing(self):
        self.git("tag", "v0.57.0")
        self.commit({"docs/x.md": "x\n", "changes/old.md": "bump: major\nOld, edited.\n"})
        self.assertEqual(NEXT.plan(self.root)[2:], (None, ""))

    def test_highest_bump_over_the_highest_tag(self):
        self.git("tag", "v0.9.0")
        self.git("tag", "v0.10.2")  # numeric, not lexical, order
        self.commit({"changes/b.md": "bump: patch\nFix b.\n"})
        self.assertEqual(NEXT.plan(self.root), ("v0.10.2", "0.10.2", "0.10.3", "- Fix b.\n"))
        self.commit({"changes/a.md": "---\nbump: minor\n---\n- Add a.\n"})
        self.assertEqual(NEXT.plan(self.root)[2:], ("0.11.0", "- Add a.\n- Fix b.\n"))
        self.commit({"changes/c.md": "bump: major\nBreak c.\n"})
        self.assertEqual(NEXT.plan(self.root)[2], "1.0.0")

    def test_malformed_fragment_raises(self):
        self.git("tag", "v0.57.0")
        self.commit({"changes/bad.md": "bump: huge\nx\n"})
        with self.assertRaises(ValueError):
            NEXT.plan(self.root)


if __name__ == "__main__":
    unittest.main()
