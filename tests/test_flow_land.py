"""Tests for flow-land.py — serial local landing of per-plan worktrees.

Every fixture is a real git repo under the system temp dir: a bare `origin`, a main
checkout on the feature branch `flow/demo` (pushed), and task worktrees created the way
`/flow-execute` creates them — outside the main checkout, on `flow-task/<NN-MM>` at the
wave base. The script runs as a subprocess against them, so these exercise git's real
behaviour, not a model of it. Global and system git config are masked so a developer's
hooks or signing settings can't change the outcome.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/devflow/scripts/flow-land.py"


class Fixture:
    def __init__(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        empty = self.root / "gitconfig"
        empty.write_text("")
        self.env = {**os.environ, "GIT_CONFIG_GLOBAL": str(empty), "GIT_CONFIG_NOSYSTEM": "1"}
        self.origin = self.root / "origin.git"
        self.repo = self.root / "repo"
        self.git(self.root, "init", "-q", "--bare", "-b", "main", str(self.origin))
        self.git(self.root, "clone", "-q", str(self.origin), str(self.repo))
        for key, value in (("user.name", "T"), ("user.email", "t@example.com"),
                           ("commit.gpgsign", "false")):
            self.git(self.repo, "config", key, value)
        self.commit("README.md", "base\n", "chore: init")
        self.git(self.repo, "push", "-q", "origin", "main")
        self.git(self.repo, "switch", "-q", "-c", "flow/demo")
        self.commit("feature.txt", "feature\n", "feat: feature work")
        self.git(self.repo, "push", "-q", "-u", "origin", "flow/demo")

    def git(self, cwd, *args):
        result = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                                env=self.env)
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
        return result.stdout.strip()

    def commit(self, rel, text, message, cwd=None):
        cwd = cwd or self.repo
        (Path(cwd) / rel).parent.mkdir(parents=True, exist_ok=True)
        (Path(cwd) / rel).write_text(text)
        self.git(cwd, "add", rel)
        self.git(cwd, "commit", "-q", "-m", message)
        return self.git(cwd, "rev-parse", "HEAD")

    def head(self, ref="HEAD"):
        return self.git(self.repo, "rev-parse", ref)

    def task(self, plan, files, base=None):
        """A task worktree the way an executor leaves it: branch flow-task/<plan> at the wave
        base, one commit per file, with the attribution trailers conventions.md requires."""
        path = self.root / f"wt-{plan}"
        self.git(self.repo, "worktree", "add", "-q", "-b", f"flow-task/{plan}", str(path),
                 base or self.head())
        for rel, text in files:
            self.commit(rel, text, f"feat({plan}): {rel}\n\nDevFlow-Agent: executor/claude/-\n"
                        f"DevFlow-Plan: {plan}", cwd=path)
        return path

    def run(self, *args):
        result = subprocess.run([sys.executable, str(SCRIPT), *args, "--repo", str(self.repo)],
                                capture_output=True, text=True, env=self.env)
        return result.returncode, json.loads(result.stdout)

    def land(self, plan, worktree, *extra):
        return self.run("land", "--plan", plan, "--task-branch", f"flow-task/{plan}",
                        "--worktree", str(worktree), *extra)

    def branches(self):
        return self.git(self.repo, "for-each-ref", "--format=%(refname:short)",
                        "refs/heads/").splitlines()

    def worktree_paths(self):
        return [line.split(" ", 1)[1] for line in
                self.git(self.repo, "worktree", "list", "--porcelain").splitlines()
                if line.startswith("worktree ")]

    def origin_refs(self):
        return self.git(self.origin, "for-each-ref", "--format=%(refname) %(objectname)")

    def state_path(self):
        return Path(self.git(self.repo, "rev-parse", "--absolute-git-dir")) / "devflow-wave.json"


def kinds(report):
    return [f["kind"] for f in report["findings"]]


class LandTestCase(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        self.addCleanup(self.fx.tempdir.cleanup)


class WaveStartTest(LandTestCase):
    def test_records_wave_base_outside_the_tree(self):
        code, report = self.fx.run("wave-start")
        self.assertEqual(code, 0, report)
        self.assertEqual(report["wave_base"], self.fx.head())
        self.assertTrue(self.fx.state_path().is_file())
        self.assertEqual(self.fx.git(self.fx.repo, "status", "--porcelain"), "")

    def test_refuses_base_branch(self):
        self.fx.git(self.fx.repo, "switch", "-q", "main")
        code, report = self.fx.run("wave-start")
        self.assertEqual(code, 1)
        self.assertIn("base-branch", kinds(report))
        self.assertFalse(self.fx.state_path().exists())

    def test_refuses_configured_base_branch(self):
        self.fx.git(self.fx.repo, "switch", "-q", "-c", "trunk", "main")
        self.fx.commit(".planning/config.json", json.dumps({"git": {"base": "trunk"}}),
                       "chore: config")
        code, report = self.fx.run("wave-start")
        self.assertEqual(code, 1)
        self.assertIn("base-branch", kinds(report))

    def test_refuses_detached_head(self):
        self.fx.git(self.fx.repo, "switch", "-q", "--detach", "HEAD")
        code, report = self.fx.run("wave-start")
        self.assertEqual(code, 1)
        self.assertIn("detached-head", kinds(report))

    def test_refuses_dirty_tree(self):
        (self.fx.repo / "stray.txt").write_text("x")
        code, report = self.fx.run("wave-start")
        self.assertEqual(code, 1)
        self.assertIn("dirty", kinds(report))
        self.assertIn("stray.txt", report["findings"][0]["paths"])

    def test_refuses_a_second_wave_while_one_is_in_flight(self):
        self.assertEqual(self.fx.run("wave-start")[0], 0)
        code, report = self.fx.run("wave-start")
        self.assertEqual(code, 1)
        self.assertEqual(kinds(report), ["wave-in-flight"])
        self.assertEqual(report["state"]["wave_base"], self.fx.head())

    def test_refuses_task_branches_left_by_an_earlier_wave(self):
        self.fx.git(self.fx.repo, "branch", "flow-task/01-09")
        code, report = self.fx.run("wave-start")
        self.assertEqual(code, 1)
        self.assertIn("leftover-branch", kinds(report))


class LeakCheckTest(LandTestCase):
    def setUp(self):
        super().setUp()
        self.assertEqual(self.fx.run("wave-start")[0], 0)

    def test_clean_main_checkout_passes(self):
        self.assertEqual(self.fx.run("leak-check")[0], 0)

    def test_detects_an_untracked_file_written_into_the_main_checkout(self):
        (self.fx.repo / "LEAK.txt").write_text("written through Bash")
        code, report = self.fx.run("leak-check")
        self.assertEqual(code, 1)
        self.assertEqual(kinds(report), ["leak"])
        self.assertEqual(report["findings"][0]["paths"], ["LEAK.txt"])

    def test_detects_a_moved_head(self):
        self.fx.commit("other.txt", "x", "feat: committed in the main checkout")
        code, report = self.fx.run("leak-check")
        self.assertEqual(code, 1)
        self.assertIn("HEAD moved", report["findings"][0]["detail"])


    def test_detects_a_switched_branch(self):
        self.fx.git(self.fx.repo, "switch", "-q", "-c", "elsewhere")
        code, report = self.fx.run("leak-check")
        self.assertEqual(code, 1)
        self.assertIn("branch moved", report["findings"][0]["detail"])


class LandTest(LandTestCase):
    def test_happy_path_lands_serially_and_cleans_up_without_pushing(self):
        origin_before = self.fx.origin_refs()
        self.fx.run("wave-start")
        base = self.fx.head()
        wt1 = self.fx.task("01-01", [("a.txt", "a\n"), ("a2.txt", "a2\n")])
        wt2 = self.fx.task("01-02", [("b.txt", "b\n")])

        for plan, wt in (("01-01", wt1), ("01-02", wt2)):
            code, report = self.fx.land(plan, wt)
            self.assertEqual(code, 0, report)

        log = self.fx.git(self.fx.repo, "log", "--format=%s%n%(trailers:key=DevFlow-Plan)",
                          f"{base}..HEAD")
        subjects = [s for s in log.splitlines() if s.startswith("feat(")]
        self.assertEqual(subjects, ["feat(01-02): b.txt", "feat(01-01): a2.txt",
                                    "feat(01-01): a.txt"])
        self.assertIn("DevFlow-Plan: 01-01", log)
        self.assertEqual(self.fx.git(self.fx.repo, "branch", "--show-current"), "flow/demo")
        self.assertEqual(self.fx.branches(), ["flow/demo", "main"])
        self.assertEqual(self.fx.worktree_paths(), [str(self.fx.repo)])
        self.assertFalse(wt1.exists() or wt2.exists())
        self.assertEqual(self.fx.origin_refs(), origin_before)
        self.assertEqual(self.fx.run("wave-end")[0], 0)
        self.assertFalse(self.fx.state_path().exists())

    def test_refuses_a_task_branch_not_cut_at_the_wave_base(self):
        self.fx.run("wave-start")
        wt = self.fx.task("01-01", [("a.txt", "a\n")], base=self.fx.head("main"))
        before = self.fx.head()
        code, report = self.fx.land("01-01", wt)
        self.assertEqual(code, 1)
        self.assertIn("wrong-base", kinds(report))
        self.assertEqual(self.fx.head(), before)
        self.assertIn("flow-task/01-01", self.fx.branches())

    def test_conflict_is_aborted_never_resolved_and_blocks(self):
        self.fx.run("wave-start")
        wt1 = self.fx.task("01-01", [("same.txt", "one\n")])
        wt2 = self.fx.task("01-02", [("same.txt", "two\n")])
        self.assertEqual(self.fx.land("01-01", wt1)[0], 0)
        before = self.fx.head()
        code, report = self.fx.land("01-02", wt2)
        self.assertEqual(code, 1)
        self.assertEqual(kinds(report), ["conflict"])
        self.assertIn("aborted", report["findings"][0]["detail"])
        self.assertEqual(self.fx.head(), before)
        self.assertEqual(self.fx.git(self.fx.repo, "status", "--porcelain"), "")
        self.assertIn("flow-task/01-02", self.fx.branches())
        self.assertTrue(wt2.exists())

    def test_partial_landing_is_detected_by_git_cherry_and_blocks(self):
        self.fx.run("wave-start")
        wt = self.fx.task("01-01", [("a.txt", "a\n"), ("a2.txt", "a2\n")])
        first = self.fx.git(wt, "rev-list", "--reverse", f"{self.fx.head()}..HEAD").split()[0]
        # An interrupted land: the first task commit reached the feature branch, the
        # second did not. Record the new HEAD so only the landing rule is under test.
        self.fx.git(self.fx.repo, "cherry-pick", first)
        state = json.loads(self.fx.state_path().read_text())
        state["expected_head"] = self.fx.head()
        self.fx.state_path().write_text(json.dumps(state))
        code, report = self.fx.land("01-01", wt)
        self.assertEqual(code, 1)
        self.assertEqual(kinds(report), ["partial-landing"])
        self.assertIn("flow-task/01-01", self.fx.branches())
        self.assertTrue(wt.exists())

    def test_rerun_after_a_crash_between_landing_and_cleanup_finishes_cleanup(self):
        self.fx.run("wave-start")
        wt = self.fx.task("01-01", [("a.txt", "a\n")])
        base = self.fx.head()
        self.fx.git(self.fx.repo, "cherry-pick", f"{base}..flow-task/01-01")
        state = json.loads(self.fx.state_path().read_text())
        state["expected_head"] = self.fx.head()
        self.fx.state_path().write_text(json.dumps(state))
        head = self.fx.head()
        code, report = self.fx.land("01-01", wt)
        self.assertEqual(code, 0, report)
        self.assertTrue(report["recovered"])
        self.assertEqual(self.fx.head(), head)
        self.assertNotIn("flow-task/01-01", self.fx.branches())

    def test_incomplete_landing_is_detected_after_the_pick(self):
        self.fx.commit("shared.txt", "1\n2\n3\n4\n5\n", "feat: shared file")
        self.fx.run("wave-start")
        wt1 = self.fx.task("01-01", [("shared.txt", "one\n2\n3\n4\n5\n")])
        wt2 = self.fx.task("01-02", [("shared.txt", "1\n2\nthree\n4\n5\n")])
        self.assertEqual(self.fx.land("01-01", wt1)[0], 0)
        # Git merges plan 2 cleanly, but its diff context now differs from the task
        # commit's, so `git cherry` cannot prove the commit landed — that must block.
        code, report = self.fx.land("01-02", wt2)
        self.assertEqual(code, 1)
        self.assertEqual(kinds(report), ["incomplete-landing"])
        self.assertIn("flow-task/01-02", self.fx.branches())
        self.assertTrue(wt2.exists())
        self.assertEqual(self.fx.run("leak-check")[0], 0)

    def test_refuses_a_task_branch_with_no_commits(self):
        self.fx.run("wave-start")
        wt = self.fx.task("01-01", [])
        code, report = self.fx.land("01-01", wt)
        self.assertEqual(code, 1)
        self.assertEqual(kinds(report), ["no-commits"])
        self.assertTrue(wt.exists())

    def test_refuses_a_worktree_holding_another_plans_branch(self):
        self.fx.run("wave-start")
        self.fx.task("01-01", [("a.txt", "a\n")])
        wt2 = self.fx.task("01-02", [("b.txt", "b\n")])
        before = self.fx.head()
        code, report = self.fx.land("01-01", wt2)
        self.assertEqual(code, 1)
        self.assertEqual(kinds(report), ["worktree-branch"])
        self.assertEqual(self.fx.head(), before)
        self.assertTrue(wt2.exists())

    def test_task_branch_must_match_the_plan(self):
        self.fx.run("wave-start")
        wt = self.fx.task("01-01", [("a.txt", "a\n")])
        code, report = self.fx.run("land", "--plan", "01-01", "--task-branch", "main",
                                   "--worktree", str(wt))
        self.assertEqual(code, 1)
        self.assertEqual(kinds(report), ["usage"])

    def test_concurrent_land_is_refused_by_the_lock(self):
        self.fx.run("wave-start")
        wt = self.fx.task("01-01", [("a.txt", "a\n")])
        lock = self.fx.state_path().parent / "devflow-land.lock"
        lock.write_text("4242 01-02\n")
        before = self.fx.head()
        code, report = self.fx.land("01-01", wt)
        self.assertEqual(code, 1)
        self.assertEqual(kinds(report), ["locked"])
        self.assertEqual(self.fx.head(), before)
        self.assertEqual(lock.read_text(), "4242 01-02\n")

    def test_never_lands_on_the_base_branch(self):
        self.fx.git(self.fx.repo, "switch", "-q", "main")
        main_before = self.fx.head()
        wt = self.fx.task("01-01", [("a.txt", "a\n")])
        # A wave state that points at main (hand-edited, or written by a buggy caller):
        # nothing but the base-branch rule stands between it and a commit on main.
        self.fx.state_path().write_text(json.dumps({
            "branch": "main", "wave_base": main_before, "expected_head": main_before,
            "worktrees": [str(self.fx.repo)], "branches": ["flow/demo", "main"],
            "landed": []}))
        code, report = self.fx.land("01-01", wt)
        self.assertEqual(code, 1)
        self.assertIn("base-branch", kinds(report))
        self.assertEqual(self.fx.head(), main_before)

    def test_refuses_a_task_worktree_with_uncommitted_work(self):
        self.fx.run("wave-start")
        wt = self.fx.task("01-01", [("a.txt", "a\n")])
        (wt / "unfinished.txt").write_text("x")
        before = self.fx.head()
        code, report = self.fx.land("01-01", wt)
        self.assertEqual(code, 1)
        self.assertIn("dirty-worktree", kinds(report))
        self.assertEqual(self.fx.head(), before)

    def test_refuses_to_land_over_a_leak(self):
        self.fx.run("wave-start")
        wt = self.fx.task("01-01", [("a.txt", "a\n")])
        (self.fx.repo / "LEAK.txt").write_text("x")
        before = self.fx.head()
        code, report = self.fx.land("01-01", wt)
        self.assertEqual(code, 1)
        self.assertIn("leak", kinds(report))
        self.assertEqual(self.fx.head(), before)

    def test_unlocks_a_locked_task_worktree_before_removing_it(self):
        self.fx.run("wave-start")
        wt = self.fx.task("01-01", [("a.txt", "a\n")])
        self.fx.git(self.fx.repo, "worktree", "lock", str(wt))
        code, report = self.fx.land("01-01", wt)
        self.assertEqual(code, 0, report)
        self.assertEqual(self.fx.worktree_paths(), [str(self.fx.repo)])

    def test_host_branch_is_deleted_only_when_it_holds_no_unique_commits(self):
        self.fx.run("wave-start")
        self.fx.git(self.fx.repo, "branch", "worktree-agent-a", "main")
        self.fx.git(self.fx.repo, "branch", "worktree-agent-b", "main")
        self.fx.git(self.fx.repo, "switch", "-q", "worktree-agent-b")
        self.fx.commit("mine.txt", "x", "wip: work only on the host branch")
        self.fx.git(self.fx.repo, "switch", "-q", "flow/demo")
        wt1 = self.fx.task("01-01", [("a.txt", "a\n")])
        wt2 = self.fx.task("01-02", [("b.txt", "b\n")])
        self.assertEqual(self.fx.land("01-01", wt1, "--host-branch", "worktree-agent-a")[0], 0)
        self.assertNotIn("worktree-agent-a", self.fx.branches())
        code, report = self.fx.land("01-02", wt2, "--host-branch", "worktree-agent-b")
        self.assertEqual(code, 1)
        self.assertEqual(kinds(report), ["host-branch-has-commits"])
        self.assertIn("worktree-agent-b", self.fx.branches())

    def test_unreadable_wave_state_fails_closed(self):
        self.fx.run("wave-start")
        wt = self.fx.task("01-01", [("a.txt", "a\n")])
        self.fx.state_path().write_text("{not json")
        before = self.fx.head()
        code, report = self.fx.land("01-01", wt)
        self.assertEqual(code, 1)
        self.assertEqual(kinds(report), ["could-not-check"])
        self.assertEqual(self.fx.head(), before)


class WaveEndTest(LandTestCase):
    def test_fails_on_a_leftover_task_worktree(self):
        self.fx.run("wave-start")
        wt = self.fx.task("01-01", [("a.txt", "a\n")])
        self.fx.git(self.fx.repo, "branch", "-m", "flow-task/01-01", "renamed-away")
        code, report = self.fx.run("wave-end")
        self.assertEqual(code, 1)
        self.assertIn("leftover-worktree", kinds(report))
        self.assertIn(str(wt), next(f for f in report["findings"]
                                    if f["kind"] == "leftover-worktree")["paths"])
        self.assertTrue(self.fx.state_path().exists())

    def test_fails_on_a_leftover_task_branch(self):
        self.fx.run("wave-start")
        self.fx.git(self.fx.repo, "branch", "flow-task/01-01")
        code, report = self.fx.run("wave-end")
        self.assertEqual(code, 1)
        self.assertEqual(kinds(report), ["leftover-branch"])
        self.assertEqual(report["findings"][0]["paths"], ["flow-task/01-01"])

    def test_fails_on_a_task_branch_even_when_recorded_at_wave_start(self):
        self.fx.run("wave-start")
        self.fx.git(self.fx.repo, "branch", "flow-task/01-01")
        state = json.loads(self.fx.state_path().read_text())
        state["branches"].append("flow-task/01-01")
        self.fx.state_path().write_text(json.dumps(state))
        code, report = self.fx.run("wave-end")
        self.assertEqual(code, 1)
        self.assertEqual(report["findings"][0]["paths"], ["flow-task/01-01"])

    def test_fails_on_any_branch_the_wave_created(self):
        self.fx.run("wave-start")
        self.fx.git(self.fx.repo, "branch", "worktree-agent-x")
        code, report = self.fx.run("wave-end")
        self.assertEqual(code, 1)
        self.assertEqual(report["findings"][0]["paths"], ["worktree-agent-x"])

    def test_fails_on_a_leak(self):
        self.fx.run("wave-start")
        (self.fx.repo / "LEAK.txt").write_text("x")
        code, report = self.fx.run("wave-end")
        self.assertEqual(code, 1)
        self.assertIn("leak", kinds(report))

    def test_fails_while_a_land_lock_remains(self):
        self.fx.run("wave-start")
        (self.fx.state_path().parent / "devflow-land.lock").write_text("1 01-01\n")
        code, report = self.fx.run("wave-end")
        self.assertEqual(code, 1)
        self.assertEqual(kinds(report), ["locked"])


class NoPushTest(unittest.TestCase):
    def test_script_never_invokes_push_or_fetch(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for verb in ('"push"', '"fetch"', '"pull"', "--force"):
            self.assertNotIn(verb, source)


if __name__ == "__main__":
    unittest.main()
