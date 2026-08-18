"""Tests for scripts/check-fenced-paths.py — the D-19 parity proof.

Every test drives scan(root), the guard's explicit-root seam, against a
disposable tempdir fixture it builds and tears down — never the CLI, and
never this repo's own tree, except RepoIsCleanTests, which is the one case
that deliberately checks this repo stays clean.
"""
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check-fenced-paths.py"
CHECKER_SOURCE = (ROOT / "scripts/check-links.py").read_text(encoding="utf-8")

SPEC = importlib.util.spec_from_file_location("check_fenced_paths", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

# The one repo path every "a real path inside a fence" fixture reuses — it
# must genuinely exist so the guard resolves it, per the plan's own choice
# of fixture (the same file phase-02's awk was probed against).
REAL_PATH = "plugins/devflow/references/conventions.md"


class CheckFencedPathsTestCase(unittest.TestCase):
    """Base: builds a disposable tempdir fixture and drives scan(root)."""

    def make_fixture(self, files, include_checker=True):
        """files: {relative_path: content}. Always plants a real
        plugins/devflow/references/conventions.md so REAL_PATH resolves,
        and — unless include_checker is False — a real copy of
        scripts/check-links.py so the loader succeeds. No git init: scan()
        never shells out to git, only main() does."""
        root = tempfile.mkdtemp(prefix="check-fenced-paths-fixture-")
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        full_files = dict(files)
        full_files.setdefault(REAL_PATH, "# Conventions\n")
        if include_checker:
            full_files["scripts/check-links.py"] = CHECKER_SOURCE
        for relpath, content in full_files.items():
            full = Path(root) / relpath
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
        return root


class BacktickFenceTests(CheckFencedPathsTestCase):
    def test_real_path_inside_backtick_fence_is_a_violation(self):
        root = self.make_fixture({
            "docs/a.md": f"# A\n\n```\n{REAL_PATH}\n```\n",
        })
        violations, files_scanned, fenced_lines = MODULE.scan(root)
        self.assertEqual(1, len(violations))
        v = violations[0]
        self.assertEqual("docs/a.md", v.file)
        self.assertEqual(4, v.line)
        self.assertEqual(REAL_PATH, v.token)
        self.assertGreater(files_scanned, 0)
        self.assertGreater(fenced_lines, 0)


class TildeFenceTests(CheckFencedPathsTestCase):
    def test_real_path_inside_tilde_fence_is_a_violation(self):
        root = self.make_fixture({
            "docs/a.md": f"# A\n\n~~~\n{REAL_PATH}\n~~~\n",
        })
        violations, _, _ = MODULE.scan(root)
        self.assertEqual(1, len(violations))
        v = violations[0]
        self.assertEqual("docs/a.md", v.file)
        self.assertEqual(4, v.line)
        self.assertEqual(REAL_PATH, v.token)


class TabIndentedFenceTests(CheckFencedPathsTestCase):
    def test_real_path_inside_tab_indented_fence_is_a_violation(self):
        # _code_fence_mask matches the *stripped* line (check-links.py:385),
        # so a tab-indented fence is masked by the checker too. Phase-02's
        # awk used an indent class of only spaces and missed this case —
        # the guard must see it the checker's way, not the awk's.
        root = self.make_fixture({
            "docs/a.md": f"# A\n\n\t```\n\t{REAL_PATH}\n\t```\n",
        })
        violations, _, _ = MODULE.scan(root)
        self.assertEqual(1, len(violations))
        v = violations[0]
        self.assertEqual("docs/a.md", v.file)
        self.assertEqual(4, v.line)
        self.assertEqual(REAL_PATH, v.token)


class ToggleInversionTests(CheckFencedPathsTestCase):
    """The phase-02 awk toggled its in-fence state on any fence-shaped line
    (``` or ~~~ indiscriminately). check-links.py's _code_fence_mask closes
    a fence only on its own character, so a ~~~ line appearing inside a ```
    block does not close it. Measured on the phase-02 awk against this exact
    fixture: it got both halves backwards — it reported the prose path
    below the closing ``` and missed the path still inside the ``` block.
    Both assertions live in one test on purpose: a suite that only checked
    "the prose path is skipped" would have passed against that broken
    reading too, since the awk also skips fenced-looking content — just the
    wrong span of it.
    """

    def test_toggle_inversion_reports_the_fenced_path_and_skips_the_prose_path(self):
        root = self.make_fixture({
            "docs/d.md": (
                "# D\n\n"
                "```\n"
                "~~~\n"
                f"{REAL_PATH}\n"
                "```\n\n"
                f"{REAL_PATH} prose\n"
            ),
        })
        violations, _, _ = MODULE.scan(root)

        # Still inside the ``` block (the ~~~ line does not close it) — reported.
        self.assertEqual(1, len(violations))
        v = violations[0]
        self.assertEqual("docs/d.md", v.file)
        self.assertEqual(5, v.line)
        self.assertEqual(REAL_PATH, v.token)

        # Ordinary prose after the closing ``` — not reported. Asserted
        # separately so a regression here shows up as its own failure
        # rather than hiding inside a changed violation count above.
        self.assertFalse(any(x.line == 8 for x in violations))


class UnterminatedFenceTests(CheckFencedPathsTestCase):
    def test_unterminated_fence_is_a_violation_naming_the_opener_line(self):
        root = self.make_fixture({
            "docs/a.md": "# A\n\n```\nexample\n",
        })
        violations, _, _ = MODULE.scan(root)
        self.assertEqual(1, len(violations))
        self.assertEqual("docs/a.md", violations[0].file)
        self.assertEqual(3, violations[0].line)


class NonExistentPathTests(CheckFencedPathsTestCase):
    def test_nonexistent_path_inside_a_fence_is_not_a_violation(self):
        root = self.make_fixture({
            "docs/nope.md": "# Nope\n\n```\ndocs/not-a-real-file.md\n```\n",
        })
        violations, _, _ = MODULE.scan(root)
        self.assertEqual([], violations)


class FrozenPageTests(CheckFencedPathsTestCase):
    def test_frozen_page_with_a_fenced_real_path_is_not_scanned(self):
        root = self.make_fixture({
            "docs/status-contract.md": f"# Status contract\n\n```\n{REAL_PATH}\n```\n",
        })
        violations, files_scanned, _ = MODULE.scan(root)
        self.assertEqual([], violations)
        # Excluded from scope entirely, not merely clean by luck: README.md
        # does not exist in this fixture and status-contract.md is frozen,
        # so nothing in scope was readable — files_scanned is 0, not 1.
        self.assertEqual(0, files_scanned)


class RepoIsCleanTests(unittest.TestCase):
    """The one case in this suite that scans this repo's own tree instead
    of a disposable fixture — deliberately, so the suite fails the day
    someone fences a real path into README or a docs/ page. This is what
    makes G3 a standing gate rather than a one-off command."""

    def test_this_repos_readme_and_docs_pages_are_clean(self):
        violations, files_scanned, fenced_lines = MODULE.scan(ROOT)
        self.assertEqual([], violations)
        self.assertGreater(files_scanned, 0)


class GuardUnavailableTests(CheckFencedPathsTestCase):
    """Fail-closed: without scripts/check-links.py to import, this guard has
    no fence rule of its own to fall back on and must not report clean."""

    def test_scan_raises_when_the_checker_cannot_be_loaded(self):
        root = self.make_fixture({
            "docs/a.md": "# A\n\nordinary prose, no fences.\n",
        }, include_checker=False)
        with self.assertRaises(MODULE.GuardUnavailable):
            MODULE.scan(root)


if __name__ == "__main__":
    unittest.main()
