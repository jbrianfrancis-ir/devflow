"""Tests for scripts/check-links.py's failure and skip rules.

Pins the checker's behavior against tempdir git fixtures so the skip rules (R1-R5)
cannot be quietly widened later to make a failing check go green. Every test drives
01-01's pinned seam, check(root), against a fixture it builds and tears down —
never the CLI, never this repo's own tree.
"""
import importlib.util
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check-links.py"
SPEC = importlib.util.spec_from_file_location("check_links", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

# A fixture's git init/add must not depend on the developer's global config, so
# behavior is identical on CI.
GIT_ENV = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")


class CheckLinksTestCase(unittest.TestCase):
    """Base: builds a temp git fixture and drives check(root) against it."""

    def make_repo(self, files):
        """files: {relative_path: content}. Writes them under a fresh tempdir,
        git-inits and stages it (no commit needed — check() reads the index via
        `git ls-files`), and returns the fixture's absolute root."""
        root = tempfile.mkdtemp(prefix="check-links-fixture-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        for relpath, content in files.items():
            full = os.path.join(root, relpath)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as stream:
                stream.write(content)
        subprocess.run(["git", "init", "-q"], cwd=root, env=GIT_ENV,
                        check=True, capture_output=True)
        subprocess.run(["git", "add", "-A"], cwd=root, env=GIT_ENV,
                        check=True, capture_output=True)
        return root


class CleanFixtureTests(CheckLinksTestCase):
    def test_fixture_with_only_resolving_references_has_no_failures(self):
        """Anti-tautology anchor: without this, a checker that always failed
        would still pass every other case in this suite."""
        root = self.make_repo({
            "doc.md": "# Doc\n\nSee [text](sub/other.md) and `sub/other.md`.\n",
            "sub/other.md": "# Other\n",
        })
        self.assertEqual([], MODULE.check(root))


if __name__ == "__main__":
    unittest.main()
