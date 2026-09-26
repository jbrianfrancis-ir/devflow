"""Tests for flow-plan-lint.py.

Each test builds a throwaway git repo under the system temp dir (never inside this repo),
commits a small tree, writes a phase dir of hand-written plans shaped like
templates/plan.md, and runs the real CLI against it. One passing phase, then one failing
fixture per rule R0-R7, each asserting the rule id and the plan it lands on.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/devflow/scripts/flow-plan-lint.py"


def git(repo, *args):
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout


def plan(pid, wave=1, depends_on="[]", files_modified="[src/a.py]", files_new=None,
         context="src/a.py", requirements="[REQ-01]", extra=""):
    new_line = f"files_new: {files_new}\n" if files_new is not None else ""
    return f"""<!-- .planning/phases/01-demo/{pid}-PLAN.md -->
---
phase: 01-demo
plan: {pid.split('-')[1]}
wave: {wave}
depends_on: {depends_on}
files_modified: {files_modified}
{new_line}autonomous: true
requirements: {requirements}
must_haves:
  truths:
    - "it works # really"
  artifacts: []
  key_links: []
{extra}---

<objective>Do the thing.</objective>

<context>
.planning/STATE.md, .planning/phases/01-demo/01-01-SUMMARY.md (written at execute time),
{context}
</context>

<tasks>
<task type="auto">
  <name>Task 1: thing</name>
  <files>src/a.py</files>
  <action>do it</action>
  <verify>true</verify>
  <falsify>false</falsify>
  <done>done</done>
</task>
</tasks>
"""


class LintCase(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name) / "repo"
        (self.repo / "src").mkdir(parents=True)
        (self.repo / "docs").mkdir()
        (self.repo / "src/a.py").write_text("a = 1\n")
        (self.repo / "src/b.py").write_text("b = 1\n")
        (self.repo / "docs/guide.md").write_text("# guide\n")
        git(self.repo, "init", "-q")
        git(self.repo, "add", "-A")
        git(self.repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid",
            "commit", "-q", "-m", "base")
        self.phase = self.repo / ".planning/phases/01-demo"
        self.phase.mkdir(parents=True)

    def tearDown(self):
        self.tempdir.cleanup()

    def write(self, name, text):
        (self.phase / name).write_text(text, encoding="utf-8")

    def run_lint(self, *extra, repo=None):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.phase),
                               "--repo", str(repo or self.repo), *extra],
                              capture_output=True, text=True)

    def assertFinding(self, result, rule, plan_id, fragment=""):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        lines = [ln for ln in result.stdout.splitlines()
                 if ln.startswith(f"{rule} {plan_id}:") and fragment in ln]
        self.assertTrue(lines, f"no {rule} finding on {plan_id} containing {fragment!r}:\n"
                               f"{result.stdout}")


class PassingPhase(LintCase):
    def test_clean_phase_exits_zero(self):
        self.write("01-01-PLAN.md", plan("01-01", files_modified="[src/a.py]",
                                         context="src/a.py, docs/guide.md (read first)"))
        self.write("01-02-PLAN.md", plan("01-02", files_modified="[src/b.py, src/new.py]",
                                         files_new="[src/new.py]", context="`src/b.py`."))
        self.write("01-03-PLAN.md", plan("01-03", wave=2, depends_on="[01-02]",
                                         files_modified="[src/new.py]",
                                         context="src/new.py:12 and docs/guide.md#intro"))
        result = self.run_lint()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("0 findings, 3 plans linted, 0 skipped (executed)", result.stdout)

    def test_template_inline_comments_parse(self):
        text = plan("01-01").replace("wave: 1", "wave: 1                # layer") \
                            .replace("depends_on: []", "depends_on: []   # real edges only") \
                            .replace("autonomous: true", "autonomous: true  # false if checkpoint")
        self.write("01-01-PLAN.md", text)
        result = self.run_lint()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_transitive_files_new_via_depends_on(self):
        self.write("01-01-PLAN.md", plan("01-01", files_modified="[src/gen.py]",
                                         files_new="[src/gen.py]"))
        self.write("01-02-PLAN.md", plan("01-02", wave=2, depends_on="[01-01]",
                                         files_modified="[src/b.py]"))
        self.write("01-03-PLAN.md", plan("01-03", wave=3, depends_on="[01-02]",
                                         files_modified="[src/gen.py]", context="src/gen.py"))
        result = self.run_lint()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_executed_plans_are_skipped(self):
        # 01-01 ran already: its frontmatter is broken and its paths are gone, but a
        # SUMMARY exists, so it is not linted — it still resolves as a dependency.
        self.write("01-01-PLAN.md", plan("01-01", files_modified="[src/gone.py]",
                                         requirements="[]"))
        self.write("01-01-SUMMARY.md", "---\nplan: 01-01\nstatus: complete\n---\n")
        self.write("01-02-PLAN.md", plan("01-02", wave=2, depends_on="[01-01]"))
        result = self.run_lint()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("0 findings, 1 plans linted, 1 skipped (executed)", result.stdout)

    def test_json_output(self):
        self.write("01-01-PLAN.md", plan("01-01", requirements="[]"))
        result = self.run_lint("--json")
        self.assertEqual(result.returncode, 1)
        data = json.loads(result.stdout)
        self.assertEqual(data["linted"], ["01-01"])
        self.assertEqual({f["rule"] for f in data["findings"]}, {"R1"})


class R0CouldNotCheck(LintCase):
    def test_unparseable_frontmatter(self):
        self.write("01-01-PLAN.md", "---\nphase: 01-demo\nwave 1 no colon\n---\n<context/>\n")
        self.assertFinding(self.run_lint(), "R0", "01-01", "unparseable frontmatter line")

    def test_missing_closing_fence(self):
        self.write("01-01-PLAN.md", "---\nphase: 01-demo\nwave: 1\n")
        self.assertFinding(self.run_lint(), "R0", "01-01", "closing")

    def test_non_git_repo(self):
        self.write("01-01-PLAN.md", plan("01-01"))
        not_git = Path(self.tempdir.name) / "plain"
        not_git.mkdir()
        self.assertFinding(self.run_lint(repo=not_git), "R0", "-", "not a git repository")

    def test_unresolvable_head(self):
        self.write("01-01-PLAN.md", plan("01-01"))
        empty = Path(self.tempdir.name) / "empty"
        empty.mkdir()
        git(empty, "init", "-q")
        self.assertFinding(self.run_lint(repo=empty), "R0", "-", "HEAD does not resolve")

    def test_no_plans(self):
        self.assertFinding(self.run_lint(), "R0", "-", "no NN-MM-PLAN.md files")


class R1RequiredFrontmatter(LintCase):
    def test_empty_requirements(self):
        self.write("01-01-PLAN.md", plan("01-01", requirements="[]"))
        self.assertFinding(self.run_lint(), "R1", "01-01", "'requirements' is empty")

    def test_missing_must_haves_key(self):
        self.write("01-01-PLAN.md", plan("01-01").replace("  key_links: []\n", ""))
        self.assertFinding(self.run_lint(), "R1", "01-01", "must_haves.key_links")


class R2DependsOnResolves(LintCase):
    def test_unknown_dependency(self):
        self.write("01-01-PLAN.md", plan("01-01"))
        self.write("01-02-PLAN.md", plan("01-02", wave=2, depends_on="[01-09]",
                                         files_modified="[src/b.py]"))
        self.assertFinding(self.run_lint(), "R2", "01-02", "'01-09'")


class R3WaveArithmetic(LintCase):
    def test_wave_not_max_dep_plus_one(self):
        self.write("01-01-PLAN.md", plan("01-01"))
        self.write("01-02-PLAN.md", plan("01-02", wave=1, depends_on="[01-01]",
                                         files_modified="[src/b.py]"))
        self.assertFinding(self.run_lint(), "R3", "01-02", "requires wave 2")


class R4NoCycles(LintCase):
    def test_cycle(self):
        self.write("01-01-PLAN.md", plan("01-01", wave=2, depends_on="[01-02]"))
        self.write("01-02-PLAN.md", plan("01-02", wave=2, depends_on="[01-01]",
                                         files_modified="[src/b.py]"))
        self.assertFinding(self.run_lint(), "R4", "01-01", "01-01 -> 01-02 -> 01-01")


class R5SameWaveDisjoint(LintCase):
    def test_same_wave_overlap(self):
        self.write("01-01-PLAN.md", plan("01-01", files_modified="[src/a.py]"))
        self.write("01-02-PLAN.md", plan("01-02", files_modified="[src/b.py, src/a.py]"))
        self.assertFinding(self.run_lint(), "R5", "01-02", "src/a.py")


class R6PathsAreReal(LintCase):
    def test_created_file_not_declared(self):
        self.write("01-01-PLAN.md", plan("01-01", files_modified="[src/a.py, src/invented.py]"))
        self.assertFinding(self.run_lint(), "R6", "01-01", "add it to files_new")

    def test_files_new_not_in_files_modified(self):
        self.write("01-01-PLAN.md", plan("01-01", files_new="[src/new.py]"))
        self.assertFinding(self.run_lint(), "R6", "01-01", "'src/new.py' is not in files_modified")

    def test_new_file_from_non_dependency(self):
        # 01-01 creates src/gen.py, but 01-02 does not depend on it: not declared for 01-02.
        self.write("01-01-PLAN.md", plan("01-01", files_modified="[src/gen.py]",
                                         files_new="[src/gen.py]"))
        self.write("01-02-PLAN.md", plan("01-02", wave=2, depends_on="[]",
                                         files_modified="[src/gen.py]"))
        result = self.run_lint()
        self.assertFinding(result, "R6", "01-02", "src/gen.py")

    def test_transitive_edge_required(self):
        # Same three plans as the passing transitive case, minus the 01-02 -> 01-01 edge.
        self.write("01-01-PLAN.md", plan("01-01", files_modified="[src/gen.py]",
                                         files_new="[src/gen.py]"))
        self.write("01-02-PLAN.md", plan("01-02", wave=1, files_modified="[src/b.py]"))
        self.write("01-03-PLAN.md", plan("01-03", wave=2, depends_on="[01-02]",
                                         files_modified="[src/gen.py]"))
        self.assertFinding(self.run_lint(), "R6", "01-03", "src/gen.py")


class R7ContextPathsExist(LintCase):
    def test_missing_context_path(self):
        self.write("01-01-PLAN.md", plan("01-01", context="src/a.py, docs/nowhere.md (read it)"))
        self.assertFinding(self.run_lint(), "R7", "01-01", "docs/nowhere.md")

    def test_prose_and_placeholders_ignored(self):
        context = ("the {devflow_root}/references/x.md contract, src/*.py, e.g. the "
                   "~/notes/a.md file, every file in docs/, and .planning/phases/01-demo/X.md")
        self.write("01-01-PLAN.md", plan("01-01", context=context))
        result = self.run_lint()
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
