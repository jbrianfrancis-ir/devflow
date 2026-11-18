"""Tests for scripts/check-change-fragment.py and scripts/release-cut.py, against tempdir
git fixtures (never this repo's tree)."""
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


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CHECK = load("check_change_fragment", "check-change-fragment.py")
CUT = load("release_cut", "release-cut.py")
GIT_ENV = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null",
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com")


class FragmentFixture(unittest.TestCase):
    def git(self, *args):
        subprocess.run(["git", "-C", self.root, *args], check=True, capture_output=True, env=GIT_ENV)

    def write(self, rel, content):
        path = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as stream:
            stream.write(content)

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="change-fragment-fixture-")
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        self.git("init", "-q", "-b", "main")
        for rel in CHECK.MANIFESTS:
            self.write(rel, json.dumps({"name": "devflow", "version": "0.19.0"}, indent=2) + "\n")
        self.write("CHANGELOG.md", "# Changelog\n\n## 0.19.0 (2026-01-01)\n- old\n")
        self.write("plugins/devflow/agents/flow-planner.md", "original\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "base")
        self.git("checkout", "-q", "-b", "feature")

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "work")

    def check(self, branch="feature"):
        return CHECK.check(self.root, "main", branch)


class CheckTests(FragmentFixture):
    def test_shipped_change_without_fragment_fails(self):
        cases = {"edit": lambda: self.write("plugins/devflow/agents/flow-planner.md", "edited\n"),
                 "non-ascii path": lambda: self.write("plugins/devflow/skills/naïve/SKILL.md", "x\n"),
                 "moved out": lambda: self.git("mv", "plugins/devflow/agents/flow-planner.md", "moved.md")}
        for name, change in cases.items():
            with self.subTest(name):
                self.git("checkout", "-q", "-B", "feature", "main")
                change()
                self.commit()
                failures = self.check().failures
                self.assertEqual(len(failures), 1)
                self.assertIn("no new fragment", failures[0])

    def test_shipped_change_with_fragment_passes_and_internal_change_needs_none(self):
        self.write("docs/notes.md", "x\n")
        self.commit()
        self.assertEqual(self.check().failures, [])
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.write("changes/planner.md", "---\nbump: patch\n---\nFix the planner.\n")
        self.commit()
        self.assertEqual(self.check().failures, [])

    def test_malformed_fragment_fails(self):
        self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
        self.write("changes/planner.md", "bump: huge\nFix the planner.\n")
        self.commit()
        self.assertIn("bump: major|minor|patch", self.check().failures[0])
        for text in ("bump: minor\n", "Fix it.\nbump: minor\n", "---\nbump: minor\nFix it.\n"):
            with self.subTest(text), self.assertRaises(ValueError):
                CHECK.parse_fragment(text)

    def test_version_or_changelog_edit_outside_a_release_fails(self):
        self.write(CHECK.MANIFEST, json.dumps({"name": "devflow", "version": "0.20.0"}, indent=2) + "\n")
        self.write("CHANGELOG.md", "# Changelog\n\n## 0.20.0 (2026-01-02)\n- new\n\n## 0.19.0 (2026-01-01)\n- old\n")
        self.write("changes/planner.md", "bump: minor\nNew thing.\n")
        self.commit()
        failures = self.check().failures
        self.assertEqual(len(failures), 2)
        self.assertTrue(all("add a changes/<slug>.md fragment instead" in f for f in failures))

    def test_unresolvable_base_ref_fails_closed(self):
        self.assertIn("did not run", CHECK.check(self.root, "no-such-ref", "feature").failures[0])


class ReleaseCutTests(FragmentFixture):
    def setUp(self):
        super().setUp()
        self.write("changes/a.md", "bump: patch\nFix a.\n")
        self.write("changes/b.md", "bump: minor\n- Add b.\n")
        self.write("changes/README.md", "not a fragment\n")
        self.git("add", "-A")
        self.git("commit", "-qm", "fragments")
        self.git("checkout", "-q", "main")
        self.git("merge", "-q", "--ff-only", "feature")

    def test_cut_writes_one_version_and_entry_and_passes_the_check(self):
        _, version, _, _ = CUT.cut(self.root, "2026-02-03", dry_run=True)
        self.assertEqual(version, "0.20.0")
        self.assertTrue(os.path.exists(os.path.join(self.root, "changes/a.md")))  # dry run wrote nothing
        CUT.cut(self.root, "2026-02-03", dry_run=False)
        for rel in CHECK.MANIFESTS:
            self.assertEqual(json.loads(Path(self.root, rel).read_text())["version"], "0.20.0")
        self.assertTrue(Path(self.root, "CHANGELOG.md").read_text().startswith(
            "# Changelog\n\n## 0.20.0 (2026-02-03)\n- Fix a.\n- Add b.\n\n## 0.19.0"))
        self.assertEqual(sorted(os.listdir(os.path.join(self.root, "changes"))), ["README.md"])
        self.git("checkout", "-q", "-b", "chore/cut")
        self.commit()
        for branch in ("release/0.20.0", "chore/cut"):  # by branch name, or by release-cut shape
            with self.subTest(branch):
                self.assertEqual(self.check(branch).failures, [])

    def test_exit_codes(self):
        cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, cwd)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(CHECK.main(["x", "main"]), 2)
            self.git("checkout", "-q", "-b", "edit")
            self.write("plugins/devflow/agents/flow-planner.md", "edited\n")
            self.commit()
            self.assertEqual(CHECK.main(["x", "main", "edit"]), 1)
            self.assertEqual(CUT.main(["--dry-run"]), 0)


if __name__ == "__main__":
    unittest.main()
