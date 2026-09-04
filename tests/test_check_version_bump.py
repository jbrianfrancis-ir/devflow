"""Tests for scripts/check-version-bump.py.

Pins the guard against tempdir git fixtures so its pass conditions cannot be quietly
widened later to make a red PR go green. Every test drives check(root, base_ref) — or
main(), for the exit-code contract CI actually consumes — against a fixture it builds
and tears down, never this repo's own tree.
"""
import contextlib
import importlib.util
import io
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
            ["git", "-C", self.root, *args], check=True, capture_output=True, env=GIT_ENV
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
        result = self.check()
        self.assertEqual(len(result.failures), 1)
        self.assertIn("still 0.19.0", result.failures[0])

    def test_shipped_change_with_bump_passes(self):
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.write(MANIFEST, self.manifest("0.20.0"))
        self.commit_feature()
        self.assertEqual(self.check().failures, [])

    def test_repo_internal_change_needs_no_bump(self):
        """CI, tests and docs are not installed by a consumer, so they never
        require a release."""
        self.write("docs/notes.md", "edited\n")
        self.write("tests/test_thing.py", "pass\n")
        self.commit_feature()
        result = self.check()
        self.assertEqual(result.failures, [])
        self.assertIn("no shipped content changed", result.notes[0])

    def test_templates_count_as_shipped(self):
        """A template ships to consumers even though it only describes their project."""
        self.write("plugins/devflow/templates/plan.md", "edited\n")
        self.commit_feature()
        result = self.check()
        self.assertEqual(len(result.failures), 1)
        self.assertIn("still 0.19.0", result.failures[0])

    def test_non_ascii_shipped_path_is_not_dropped(self):
        """Regression: plain `--name-only` C-quotes a path holding a non-ASCII byte, so
        a prefix match misses it and the guard reports green on the exact change it
        exists to catch. The NUL-separated read is what keeps this red."""
        self.write("plugins/devflow/skills/naïve/SKILL.md", "new\n")
        self.commit_feature()
        result = self.check()
        self.assertEqual(len(result.failures), 1)
        self.assertIn("still 0.19.0", result.failures[0])

    def test_shipped_file_moved_out_of_the_payload_fails(self):
        """Regression: git reports a rename as its destination alone, so a shipped file
        moved out of the payload would leave nothing matching the prefix — consumers
        lose a skill and the guard sees only repo-internal churn. `--no-renames` is
        what keeps this red."""
        self.git("mv", "plugins/devflow/agents/flow-planner.md", "docs/moved.md")
        self.commit_feature()
        result = self.check()
        self.assertEqual(len(result.failures), 1)
        self.assertIn("still 0.19.0", result.failures[0])

    def test_uncommitted_bump_is_seen(self):
        """The working tree answers too, so the guard is usable before committing."""
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.commit_feature()
        self.write(MANIFEST, self.manifest("0.20.0"))
        self.assertEqual(self.check().failures, [])


class VersionOrderingTests(CheckVersionBumpTestCase):
    def test_backwards_version_fails(self):
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.write(MANIFEST, self.manifest("0.18.0"))
        self.commit_feature()
        result = self.check()
        self.assertEqual(len(result.failures), 1)
        self.assertIn("moves backwards", result.failures[0])

    def test_non_semver_change_passes_with_a_note(self):
        """Ordering it cannot verify is reported, not silently graded green."""
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.write(MANIFEST, self.manifest("0.20.0-rc1"))
        self.commit_feature()
        result = self.check()
        self.assertEqual(result.failures, [])
        self.assertTrue(any("ordering unverified" in note for note in result.notes))


class FailClosedTests(CheckVersionBumpTestCase):
    def test_unresolvable_base_ref_fails(self):
        """A comparison that did not run is never a clean one."""
        result = MODULE.check(self.root, "no-such-ref")
        self.assertEqual(len(result.failures), 1)
        self.assertIn("did not run", result.failures[0])

    def test_missing_manifest_at_head_fails(self):
        os.remove(os.path.join(self.root, MANIFEST))
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.commit_feature()
        result = self.check()
        self.assertEqual(len(result.failures), 1)
        self.assertIn("cannot verify", result.failures[0])

    def test_unparseable_manifest_at_head_fails(self):
        self.write(MANIFEST, "not json\n")
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.commit_feature()
        result = self.check()
        self.assertEqual(len(result.failures), 1)
        self.assertIn("unreadable", result.failures[0])

    def test_unparseable_manifest_at_base_fails(self):
        """The fail-open this guard must not have: an unreadable base manifest is not
        the same as an absent one, and must never be read as 'first release'."""
        self.git("checkout", "-q", "main")
        self.write(MANIFEST, "not json\n")
        self.git("commit", "-qam", "corrupt manifest")
        self.git("checkout", "-q", "feature")
        self.git("rebase", "-q", "main")
        self.write(MANIFEST, self.manifest("0.20.0"))
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.commit_feature()
        result = self.check()
        self.assertEqual(len(result.failures), 1)
        self.assertIn("unreadable at main", result.failures[0])

    def test_manifest_that_is_not_an_object_fails(self):
        """Valid JSON that is not an object must return the UNREADABLE state, not raise
        through `check()`'s contract."""
        self.write(MANIFEST, "[]\n")
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.commit_feature()
        result = self.check()
        self.assertEqual(len(result.failures), 1)
        self.assertIn("unreadable", result.failures[0])

    def test_manifest_without_version_key_fails(self):
        self.write(MANIFEST, json.dumps({"name": "devflow"}) + "\n")
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.commit_feature()
        result = self.check()
        self.assertEqual(len(result.failures), 1)
        self.assertIn("unreadable", result.failures[0])

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
        result = self.check()
        self.assertEqual(result.failures, [])
        self.assertTrue(any("first version" in note for note in result.notes))


class ExitCodeTests(CheckVersionBumpTestCase):
    """main()'s exit code is the entire contract CI consumes — check() returning the
    right failures proves nothing if the mapping to an exit code is wrong."""

    def run_main(self, *argv):
        cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)
        with contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()):
            code = MODULE.main(["check-version-bump.py", *argv])
        return code, out.getvalue()

    def test_missing_bump_exits_1(self):
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.commit_feature()
        code, output = self.run_main("main")
        self.assertEqual(code, 1)
        self.assertIn("FAIL:", output)

    def test_bumped_exits_0(self):
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.write(MANIFEST, self.manifest("0.20.0"))
        self.commit_feature()
        code, output = self.run_main("main")
        self.assertEqual(code, 0)
        self.assertNotIn("FAIL:", output)

    def test_wrong_arity_exits_2(self):
        code, _ = self.run_main()
        self.assertEqual(code, 2)

    def test_outside_a_git_repository_exits_2(self):
        outside = tempfile.mkdtemp(prefix="check-version-bump-nonrepo-")
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        cwd = os.getcwd()
        os.chdir(outside)
        self.addCleanup(os.chdir, cwd)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(MODULE.main(["check-version-bump.py", "main"]), 2)

    def test_output_names_the_repo_it_checked(self):
        """Run by path from another directory, the guard answers about the tree you are
        standing in — so it has to say which one."""
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.commit_feature()
        _, output = self.run_main("main")
        self.assertIn(f"repo: {os.path.realpath(self.root)}", output)


if __name__ == "__main__":
    unittest.main()
