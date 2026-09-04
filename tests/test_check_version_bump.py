"""Tests for scripts/check-version-bump.py.

Pins the guard against tempdir git fixtures so its pass conditions cannot be quietly
widened later to make a red PR go green. Every test drives check(root, base_ref)
against a fixture it builds and tears down — never this repo's own tree.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check-version-bump.py"
SPEC = importlib.util.spec_from_file_location("check_version_bump", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

MANIFEST = "plugins/devflow/.claude-plugin/plugin.json"

# A fixture's git commands must not depend on the developer's global config, so
# behavior is identical on CI.
GIT_ENV = dict(
    os.environ,
    GIT_CONFIG_GLOBAL="/dev/null",
    GIT_CONFIG_SYSTEM="/dev/null",
    GIT_AUTHOR_NAME="t",
    GIT_AUTHOR_EMAIL="t@example.com",
    GIT_COMMITTER_NAME="t",
    GIT_COMMITTER_EMAIL="t@example.com",
)


class CheckVersionBumpTestCase(unittest.TestCase):
    """Base: builds a two-branch git fixture and drives check() against it."""

    def git(self, *args):
        subprocess.run(
            ["git", "-C", self.root, *args],
            check=True,
            capture_output=True,
            env=GIT_ENV,
        )

    def write(self, relpath, content):
        full = os.path.join(self.root, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as stream:
            stream.write(content)

    def manifest(self, version):
        return json.dumps({"name": "devflow", "version": version, "description": "d"}) + "\n"

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="check-version-bump-fixture-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.git("init", "-q", "-b", "main")
        self.write(MANIFEST, self.manifest("0.19.0"))
        self.write("plugins/devflow/agents/flow-planner.md", "original\n")
        self.write("docs/notes.md", "original\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        self.git("checkout", "-q", "-b", "feature")

    def commit_feature(self, message="work"):
        self.git("add", "-A")
        self.git("commit", "-qm", message)

    def check(self):
        return MODULE.check(self.root, "main")


class ShippedContentTests(CheckVersionBumpTestCase):
    def test_shipped_change_without_bump_fails(self):
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.commit_feature()
        failures, _ = self.check()
        self.assertEqual(len(failures), 1)
        self.assertIn("still 0.19.0", failures[0])

    def test_shipped_change_with_bump_passes(self):
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.write(MANIFEST, self.manifest("0.20.0"))
        self.commit_feature()
        failures, _ = self.check()
        self.assertEqual(failures, [])

    def test_repo_internal_change_needs_no_bump(self):
        """CI, tests and docs are not installed by a consumer, so they never
        require a release."""
        self.write("docs/notes.md", "edited\n")
        self.write("tests/test_thing.py", "pass\n")
        self.commit_feature()
        failures, notes = self.check()
        self.assertEqual(failures, [])
        self.assertIn("no shipped content changed", notes[0])

    def test_templates_count_as_shipped(self):
        """A template ships to consumers even though it only describes their project."""
        self.write("plugins/devflow/templates/plan.md", "edited\n")
        self.commit_feature()
        failures, _ = self.check()
        self.assertEqual(len(failures), 1)

    def test_uncommitted_bump_is_seen(self):
        """The working tree answers too, so the guard is usable before committing."""
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.commit_feature()
        self.write(MANIFEST, self.manifest("0.20.0"))
        failures, _ = self.check()
        self.assertEqual(failures, [])


class VersionOrderingTests(CheckVersionBumpTestCase):
    def test_backwards_version_fails(self):
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.write(MANIFEST, self.manifest("0.18.0"))
        self.commit_feature()
        failures, _ = self.check()
        self.assertEqual(len(failures), 1)
        self.assertIn("moves backwards", failures[0])

    def test_non_semver_change_passes_with_a_note(self):
        """Ordering it cannot verify is reported, not silently graded green."""
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.write(MANIFEST, self.manifest("0.20.0-rc1"))
        self.commit_feature()
        failures, notes = self.check()
        self.assertEqual(failures, [])
        self.assertTrue(any("ordering unverified" in note for note in notes))


class FailClosedTests(CheckVersionBumpTestCase):
    def test_unresolvable_base_ref_fails(self):
        """A comparison that did not run is never a clean one."""
        failures, _ = MODULE.check(self.root, "no-such-ref")
        self.assertEqual(len(failures), 1)
        self.assertIn("did not run", failures[0])

    def test_missing_manifest_fails(self):
        os.remove(os.path.join(self.root, MANIFEST))
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.commit_feature()
        failures, _ = self.check()
        self.assertEqual(len(failures), 1)
        self.assertIn("cannot verify", failures[0])

    def test_new_plugin_without_earlier_version_passes(self):
        """Nothing to advance when the manifest is introduced by this diff."""
        self.git("checkout", "-q", "main")
        self.git("rm", "-q", MANIFEST)
        self.git("commit", "-qm", "drop manifest")
        self.git("checkout", "-q", "feature")
        self.git("rebase", "-q", "main")
        self.write(MANIFEST, self.manifest("0.1.0"))
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.commit_feature()
        failures, notes = self.check()
        self.assertEqual(failures, [])
        self.assertTrue(any("first version" in note for note in notes))


if __name__ == "__main__":
    unittest.main()
