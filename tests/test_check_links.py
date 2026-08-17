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


class ReferenceKindFailureTests(CheckLinksTestCase):
    """One failing case per reference kind, plus the anchor positive."""

    def test_markdown_link_to_missing_target_fails(self):
        root = self.make_repo({
            "doc.md": "# Doc\n\nSee [text](sub/missing.md) here.\n",
            "sub/other.md": "# Other\n",
        })
        failures = MODULE.check(root)
        self.assertEqual(1, len(failures))
        failure = failures[0]
        self.assertEqual("doc.md", failure.file)
        self.assertEqual(3, failure.line)
        self.assertEqual("sub/missing.md", failure.target)

    def test_anchor_to_no_such_heading_fails(self):
        root = self.make_repo({
            "doc.md": "# Doc Heading\n\nSee [text](#no-such-heading) here.\n",
        })
        failures = MODULE.check(root)
        self.assertEqual(1, len(failures))
        failure = failures[0]
        self.assertEqual("doc.md", failure.file)
        self.assertEqual(3, failure.line)
        self.assertEqual("#no-such-heading", failure.target)

    def test_anchor_to_real_heading_passes(self):
        """Exercises the GitHub slugger in both directions alongside the failing case above."""
        root = self.make_repo({
            "doc.md": "# Doc Heading\n\nSee [text](#doc-heading) here.\n",
        })
        self.assertEqual([], MODULE.check(root))

    def test_backticked_path_to_missing_target_fails(self):
        root = self.make_repo({
            "doc.md": "# Doc\n\nSee `some/missing.py` here.\n",
            # Establishes "some" as a real top-level entry so this is a checked
            # miss, not an R5 skip for an unrelated reason.
            "some/existing.py": "# placeholder\n",
        })
        failures = MODULE.check(root)
        self.assertEqual(1, len(failures))
        failure = failures[0]
        self.assertEqual("doc.md", failure.file)
        self.assertEqual(3, failure.line)
        self.assertEqual("some/missing.py", failure.target)

    def test_devflow_root_reference_to_missing_target_fails(self):
        root = self.make_repo({
            "doc.md": "# Doc\n\nSee `{devflow_root}/references/missing.md` here.\n",
            # Establishes "plugins" as a real top-level entry (see above).
            "plugins/devflow/dummy.txt": "placeholder\n",
        })
        failures = MODULE.check(root)
        self.assertEqual(1, len(failures))
        failure = failures[0]
        self.assertEqual("doc.md", failure.file)
        self.assertEqual(3, failure.line)
        # {devflow_root}/... is resolved to plugins/devflow/... before it is reported.
        self.assertEqual("plugins/devflow/references/missing.md", failure.target)


class ScopeExclusionTests(CheckLinksTestCase):
    """REQ-09d: templates/ and .planning/ describe a consuming project, not this repo."""

    def test_broken_reference_under_templates_is_not_checked(self):
        root = self.make_repo({
            "plugins/devflow/templates/plan.md": "# Plan\n\nSee `sub/missing.md` here.\n",
            # Establishes "sub" as a real top-level entry: absent scope exclusion,
            # this reference would be checked and would fail.
            "sub/existing.txt": "placeholder\n",
        })
        self.assertEqual([], MODULE.check(root))

    def test_broken_reference_under_planning_is_not_checked(self):
        root = self.make_repo({
            ".planning/PROJECT.md": "# Project\n\nSee `sub/missing.md` here.\n",
            "sub/existing.txt": "placeholder\n",
        })
        self.assertEqual([], MODULE.check(root))


class SkipRuleTests(CheckLinksTestCase):
    """REQ-09e, one assertion per rule so a future over-tightening names which rule it broke.

    Each fixture also plants a real top-level entry matching the token's first
    segment, so the case pins its own rule specifically — not an incidental R5 skip.
    """

    def test_r1_command_line_with_space_is_skipped(self):
        root = self.make_repo({
            "doc.md": "# Doc\n\nRun `cat docs/readme.md` to view it.\n",
            "docs/existing.md": "# Existing\n",
        })
        self.assertEqual([], MODULE.check(root))

    def test_r2_glob_token_is_skipped(self):
        root = self.make_repo({
            "doc.md": "# Doc\n\nSee `docs/*.md` for all topics.\n",
            "docs/existing.md": "# Existing\n",
        })
        self.assertEqual([], MODULE.check(root))

    def test_r3_nn_slug_placeholder_is_skipped(self):
        root = self.make_repo({
            "doc.md": "# Doc\n\nSee `phases/NN-slug/plan.md` for the pattern.\n",
            "phases/existing.txt": "placeholder\n",
        })
        self.assertEqual([], MODULE.check(root))

    def test_r4_planning_rooted_token_is_skipped(self):
        root = self.make_repo({
            "doc.md": "# Doc\n\nSee `.planning/STATE.md` for state.\n",
            ".planning/dummy.txt": "placeholder\n",
        })
        self.assertEqual([], MODULE.check(root))

    def test_r5_is_per_base_checks_other_base_and_skips_no_base(self):
        """R5 is per-base, not root-only: a broken token whose first segment is not
        a top-level entry of the fixture root but *is* one of the referring file's
        own directory must still be checked, while a token matching no base at all
        is skipped. A suite carrying only the skip half would pass under the wrong
        root-only reading too, so both assertions live here."""
        root = self.make_repo({
            "sub/a.md": (
                "# A\n\n"
                "See `helpers/missing.py` here.\n\n"
                "Also see `codebase/MAP.md` there.\n"
            ),
            # "helpers" is a top-level entry of sub/ (a.md's own dir) but not of
            # the fixture root — present.py exists, missing.py does not.
            "sub/helpers/present.py": "# placeholder\n",
        })
        failures = MODULE.check(root)

        # (a) checked against the referring file's own directory as a base.
        self.assertEqual(1, len(failures))
        failure = failures[0]
        self.assertEqual("sub/a.md", failure.file)
        self.assertEqual(3, failure.line)
        self.assertEqual("helpers/missing.py", failure.target)

        # (b) skipped: "codebase" matches no base's top-level entries at all.
        self.assertFalse(any(f.target == "codebase/MAP.md" for f in failures))


if __name__ == "__main__":
    unittest.main()
