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
        """The whitespace must land after the first path separator *and* the
        token must still end in a checked extension, so R5 ("docs" is a real
        top-level entry) declines and the backtick extension filter still
        lets the token through — leaving R1 as the only rule that can skip
        it. (A token like `cat docs/readme.md` is pre-empted by R5 on its
        first segment "cat docs"; a token like `docs/readme.md and more` is
        filtered out before R1 even runs, because it no longer ends in
        `.md` — both would make this test vacuous.)"""
        root = self.make_repo({
            "doc.md": "# Doc\n\nSee `docs/read me.md` here.\n",
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


class LinkResolutionTests(CheckLinksTestCase):
    """B1: `[text](target)` resolves against the referring file's own
    directory only — GitHub's rule — never against the repo root or any
    other base. (Backticked tokens and `{devflow_root}/...` keep the
    multi-base walk; SkipRuleTests above already pins that.)"""

    def test_markdown_link_resolves_only_against_own_directory(self):
        """sub/a.md's link resolves on github.com to sub/docs/guide.md,
        which has the Beta heading. A resolver that tries the repo root
        first would grade it against docs/guide.md (heading Alpha) instead
        and report a working link as broken."""
        root = self.make_repo({
            "sub/a.md": "# A\n\nSee [beta](docs/guide.md#beta).\n",
            "docs/guide.md": "# Alpha\n",
            "sub/docs/guide.md": "# Beta\n",
        })
        self.assertEqual([], MODULE.check(root))

    def test_markdown_link_matching_only_the_root_base_is_reported_broken(self):
        """sub/a.md's link points at sub/docs/guide.md on github.com, which
        does not exist — only the root-level docs/guide.md does. A resolver
        that falls back to the root base would silently pass this 404."""
        root = self.make_repo({
            "sub/a.md": "# A\n\nSee [guide](docs/guide.md).\n",
            "docs/guide.md": "# Guide\n",
        })
        failures = MODULE.check(root)
        self.assertEqual(1, len(failures))
        self.assertEqual("sub/a.md", failures[0].file)
        self.assertEqual("docs/guide.md", failures[0].target)


class ReferenceCountTests(CheckLinksTestCase):
    """B2a: check() reports how many references it actually resolved, so
    '0 failures' and '0 references examined' are never indistinguishable."""

    def test_checked_count_covers_every_graded_reference(self):
        root = self.make_repo({
            "doc.md": "# Doc\n\nSee [ok](sub/other.md) and [bad](sub/missing.md).\n",
            "sub/other.md": "# Other\n",
        })
        result = MODULE.check(root)
        self.assertEqual(1, len(result))
        self.assertEqual(2, result.checked)

    def test_zero_failures_still_reports_a_nonzero_checked_count(self):
        """Without this, a checker that skipped everything would also print
        '0 failures' — indistinguishable from a checker that checked
        everything and found it clean."""
        root = self.make_repo({
            "doc.md": "# Doc\n\nSee [text](sub/other.md) and `sub/other.md`.\n",
            "sub/other.md": "# Other\n",
        })
        result = MODULE.check(root)
        self.assertEqual([], result)
        self.assertEqual(2, result.checked)


class UnterminatedFenceTests(CheckLinksTestCase):
    """B2b: an unterminated fence must surface as a Failure, not silently
    mask the rest of the file to EOF with no signal."""

    def test_unterminated_fence_is_reported_as_a_failure(self):
        root = self.make_repo({
            "doc.md": "# Doc\n\n```\nexample\n",
        })
        failures = MODULE.check(root)
        self.assertEqual(1, len(failures))
        self.assertEqual("doc.md", failures[0].file)
        self.assertEqual(3, failures[0].line)
        self.assertIn("unterminated", failures[0].reason)

    def test_a_closed_fence_elsewhere_in_the_file_reports_no_such_failure(self):
        root = self.make_repo({
            "doc.md": "# Doc\n\n```\nexample\n```\n",
        })
        self.assertEqual([], MODULE.check(root))


class FenceMaskingTests(CheckLinksTestCase):
    """B3: fence masking pinned in both directions — a reference inside a
    fence is skipped, one after a properly closed fence is still checked.
    (Mutation-proof: disabling the closing-fence branch, so `in_fence` never
    clears, makes the second case here fail — see M19 in findings-tests.md.)
    """

    def test_reference_inside_a_fence_is_not_checked(self):
        root = self.make_repo({
            "doc.md": "# Doc\n\n```\nSee [x](sub/missing.md) here.\n```\n",
            # Establishes "sub" as a real top-level entry, so an unmasked
            # reference here would be a checked miss, not an R5 skip.
            "sub/existing.md": "# Existing\n",
        })
        self.assertEqual([], MODULE.check(root))

    def test_reference_after_a_closed_fence_is_still_checked(self):
        root = self.make_repo({
            "doc.md": "# Doc\n\n```\nexample\n```\nSee [x](sub/missing.md) here.\n",
            "sub/existing.md": "# Existing\n",
        })
        failures = MODULE.check(root)
        self.assertEqual(1, len(failures))
        self.assertEqual("doc.md", failures[0].file)
        self.assertEqual(6, failures[0].line)
        self.assertEqual("sub/missing.md", failures[0].target)


class ContainmentTests(unittest.TestCase):
    """S1: a resolved target must stay under the repo root. `../` traversal
    and a symlink that escapes the checkout are treated as unresolved — the
    same verdict GitHub gives, since it cannot follow either one. These
    build their own fixture (not via make_repo) because the point is a real
    file sitting just *outside* the fixture root."""

    def make_nested_repo(self, files):
        parent = tempfile.mkdtemp(prefix="check-links-outside-")
        self.addCleanup(shutil.rmtree, parent, ignore_errors=True)
        root = os.path.join(parent, "repo")
        os.makedirs(root)
        for relpath, content in files.items():
            full = os.path.join(root, relpath)
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as stream:
                stream.write(content)
        subprocess.run(["git", "init", "-q"], cwd=root, env=GIT_ENV,
                        check=True, capture_output=True)
        subprocess.run(["git", "add", "-A"], cwd=root, env=GIT_ENV,
                        check=True, capture_output=True)
        return parent, root

    def test_parent_traversal_from_a_root_level_link_does_not_escape_the_repo(self):
        parent, root = self.make_nested_repo({
            "escape.md": "# Doc\n\nSee [x](../outside.md) here.\n",
        })
        with open(os.path.join(parent, "outside.md"), "w", encoding="utf-8") as stream:
            stream.write("# Outside\n")
        failures = MODULE.check(root)
        self.assertEqual(1, len(failures))
        self.assertEqual("escape.md", failures[0].file)
        self.assertEqual("../outside.md", failures[0].target)
        self.assertEqual("target does not exist", failures[0].reason)

    def test_symlink_escaping_the_repo_does_not_resolve(self):
        parent, root = self.make_nested_repo({
            "doc.md": "# Doc\n\nSee [x](evil.md) here.\n",
        })
        outside = os.path.join(parent, "secret.md")
        with open(outside, "w", encoding="utf-8") as stream:
            stream.write("# Secret\n")
        os.symlink(outside, os.path.join(root, "evil.md"))
        subprocess.run(["git", "add", "-A"], cwd=root, env=GIT_ENV,
                        check=True, capture_output=True)
        failures = MODULE.check(root)
        self.assertEqual(1, len(failures))
        self.assertEqual("evil.md", failures[0].target)
        self.assertEqual("target does not exist", failures[0].reason)


class DirectoryTargetTests(CheckLinksTestCase):
    """S2: a link to a tracked directory is a normal, correct thing to write
    (github.com renders a folder listing) and must not be reported broken."""

    def test_link_to_a_tracked_directory_is_accepted(self):
        root = self.make_repo({
            "doc.md": "# Doc\n\nSee [refs](docs) here.\n",
            "docs/guide.md": "# Guide\n",
        })
        self.assertEqual([], MODULE.check(root))

    def test_anchor_into_a_directory_target_is_not_heading_graded(self):
        root = self.make_repo({
            "doc.md": "# Doc\n\nSee [refs](docs#nonexistent) here.\n",
            "docs/guide.md": "# Guide\n",
        })
        self.assertEqual([], MODULE.check(root))


class TrackedFileEnumerationTests(CheckLinksTestCase):
    """S3: `git ls-files` (no `-z`) C-quotes any path with a newline, quote,
    backslash, or non-ASCII byte, which pushes it past the `.md` suffix
    filter and out of the scan with no signal — the "could not check
    reported as clean" failure conventions.md names."""

    def test_broken_reference_inside_a_specially_named_file_is_still_caught(self):
        root = self.make_repo({
            "sub/control.md": "# Control\n\nSee [x](sub/missing.md) here.\n",
            'sub/quo"te.md': "# Quote\n\nSee [x](sub/missing.md) here.\n",
        })
        failures = MODULE.check(root)
        self.assertEqual(2, len(failures))
        self.assertEqual({"sub/control.md", 'sub/quo"te.md'}, {f.file for f in failures})


class MainSignatureTests(unittest.TestCase):
    """S4: main() takes no argv — a caller mirroring flow-fleet.py's
    `main([root, "--json"])` contract must get a TypeError, not a silent
    full run against the ambient cwd with every argument dropped."""

    def test_main_does_not_silently_accept_an_argv_list(self):
        with self.assertRaises(TypeError):
            MODULE.main(["some", "argv"])


class FrontmatterMaskingTests(CheckLinksTestCase):
    """S5: `_check_file` must apply the same frontmatter mask `_heading_slugs`
    already uses, so a path-shaped token in YAML frontmatter — a data field,
    not prose — is not checked as a reference."""

    def test_path_shaped_token_in_frontmatter_is_not_checked_as_a_reference(self):
        root = self.make_repo({
            "doc.md": "---\ntemplate: `sub/missing.md`\n---\n# Doc\n",
            # Establishes "sub" as a real top-level entry so R5 alone
            # cannot explain a pass — the frontmatter mask has to do it.
            "sub/existing.md": "# Existing\n",
        })
        self.assertEqual([], MODULE.check(root))


if __name__ == "__main__":
    unittest.main()
