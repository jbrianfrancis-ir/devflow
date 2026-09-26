"""Tests for flow-undo.py — every block reason, the expected-head refusal, and a real apply.

Each test builds a throwaway repo with a bare "origin" and drives the script as a
subprocess, the way /flow-undo does. The rules under test are the whole safety story:
undo never rewrites a base branch, published work, or a merge, and a publication check
that could not run blocks rather than reading as "unpublished".
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/devflow/scripts/flow-undo.py"
SKILL = ROOT / "plugins/devflow/skills/flow-undo/SKILL.md"

# Isolate from the developer's git config (signing, hooks, default branch) and give
# CI runners, which have no identity, one to commit with.
GIT_ENV = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")


def git(cwd, *args):
    out = subprocess.run(["git", *args], cwd=cwd, env=GIT_ENV, capture_output=True, text=True)
    if out.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {out.stderr}")
    return out.stdout.strip()


def run(*args):
    out = subprocess.run([sys.executable, str(SCRIPT), *args], env=GIT_ENV,
                         capture_output=True, text=True)
    return out.returncode, json.loads(out.stdout)


class UndoRepo(unittest.TestCase):
    """A work repo cloned from a bare origin: main pushed, then flow/feature with two
    local-only commits A and B on top of the pushed base commit."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="flow-undo-")
        self.addCleanup(shutil.rmtree, self.tmp)
        self.origin = os.path.join(self.tmp, "origin.git")
        self.repo = os.path.join(self.tmp, "work")
        git(self.tmp, "init", "--bare", "-b", "main", self.origin)
        git(self.tmp, "clone", "-q", self.origin, self.repo)
        git(self.repo, "checkout", "-q", "-b", "main")
        self.base = self.commit("base")
        git(self.repo, "push", "-q", "origin", "main")
        git(self.repo, "checkout", "-q", "-b", "flow/feature")
        self.a = self.commit("a")
        self.b = self.commit("b")

    def commit(self, name):
        Path(self.repo, f"{name}.txt").write_text(name + "\n")
        git(self.repo, "add", f"{name}.txt")
        git(self.repo, "commit", "-q", "-m", name)
        return git(self.repo, "rev-parse", "HEAD")

    def preview(self, to):
        return run("preview", "--repo", self.repo, "--to", to)

    def codes(self, result):
        return {b["code"] for b in result["blocked"]}

    def origin_refs(self):
        return git(self.origin, "for-each-ref", "--format=%(refname) %(objectname)")


class PreviewTest(UndoRepo):
    def test_unpublished_range_is_apply_ready(self):
        rc, result = self.preview(self.base)
        self.assertEqual(rc, 0, result)
        self.assertEqual(result["blocked"], [])
        self.assertEqual([c["sha"] for c in result["commits"]], [self.b, self.a])
        self.assertEqual(result["apply"], {"repo": result["repo"], "to": self.base,
                                           "expected_head": self.b})

    def test_base_branch_blocked(self):
        git(self.repo, "checkout", "-q", "main")
        self.commit("on-main")
        rc, result = self.preview(self.base)
        self.assertEqual(rc, 1)
        self.assertIn("base-branch", self.codes(result))
        self.assertIsNone(result["apply"])

    def test_configured_base_branch_blocked(self):
        # A project whose base is neither main nor dev: config.json names it.
        git(self.repo, "branch", "-q", "trunk", self.base)
        git(self.repo, "checkout", "-q", "trunk")
        Path(self.repo, ".planning").mkdir()
        Path(self.repo, ".planning/config.json").write_text('{"git": {"base": "trunk"}}')
        git(self.repo, "add", ".planning")
        git(self.repo, "commit", "-q", "-m", "config")
        rc, result = self.preview(self.base)
        self.assertEqual(rc, 1)
        self.assertIn("base-branch", self.codes(result))

    def test_detached_head_blocked(self):
        git(self.repo, "checkout", "-q", "--detach", self.b)
        rc, result = self.preview(self.base)
        self.assertEqual(rc, 1)
        self.assertIn("detached-head", self.codes(result))

    def test_dirty_tree_blocked(self):
        Path(self.repo, "a.txt").write_text("edited\n")
        rc, result = self.preview(self.base)
        self.assertEqual(rc, 1)
        self.assertIn("dirty-tree", self.codes(result))

    def test_untracked_file_blocked(self):
        Path(self.repo, "new.txt").write_text("x\n")
        rc, result = self.preview(self.base)
        self.assertEqual(rc, 1)
        self.assertIn("dirty-tree", self.codes(result))

    def test_non_ancestor_blocked(self):
        git(self.repo, "checkout", "-q", "-b", "side", self.base)
        side = self.commit("side")
        git(self.repo, "checkout", "-q", "flow/feature")
        rc, result = self.preview(side)
        self.assertEqual(rc, 1)
        self.assertIn("not-ancestor", self.codes(result))

    def test_target_is_head_blocked(self):
        rc, result = self.preview(self.b)
        self.assertEqual(rc, 1)
        self.assertIn("target-is-head", self.codes(result))

    def test_published_commit_blocked(self):
        git(self.repo, "push", "-q", "origin", f"{self.a}:refs/heads/flow/feature")
        rc, result = self.preview(self.base)
        self.assertEqual(rc, 1)
        published = [b for b in result["blocked"] if b["code"] == "published"]
        self.assertEqual(len(published), 1, result)
        self.assertIn(self.a, published[0]["detail"])

    def test_commit_published_after_last_fetch_blocked(self):
        # Pushed to origin by another clone — the local remote-tracking refs do not know yet.
        # Only a fresh fetch can see it, which is why preview fetches every time.
        other = os.path.join(self.tmp, "other")
        git(self.tmp, "clone", "-q", self.repo, other)
        git(other, "push", "-q", self.origin, f"{self.b}:refs/heads/someone-else")
        self.assertNotIn(self.b, git(self.repo, "for-each-ref", "refs/remotes"))
        rc, result = self.preview(self.base)
        self.assertEqual(rc, 1)
        self.assertIn("published", self.codes(result))

    def test_merge_commit_blocked(self):
        git(self.repo, "checkout", "-q", "-b", "side", self.base)
        self.commit("side")
        git(self.repo, "checkout", "-q", "flow/feature")
        git(self.repo, "merge", "-q", "--no-ff", "--no-edit", "side")
        rc, result = self.preview(self.base)
        self.assertEqual(rc, 1)
        self.assertIn("merge-commit", self.codes(result))

    def test_fetch_failure_is_could_not_check_not_unpublished(self):
        git(self.repo, "remote", "set-url", "origin", os.path.join(self.tmp, "missing.git"))
        rc, result = self.preview(self.base)
        self.assertEqual(rc, 1)
        self.assertIn("could-not-check", self.codes(result))
        self.assertNotIn("published", self.codes(result))
        self.assertIsNone(result["apply"])

    def test_unreadable_config_blocked(self):
        Path(self.repo, ".planning").mkdir()
        Path(self.repo, ".planning/config.json").write_text("{not json")
        git(self.repo, "add", ".planning")
        git(self.repo, "commit", "-q", "-m", "bad config")
        rc, result = self.preview(self.base)
        self.assertEqual(rc, 1)
        self.assertIn("config-unreadable", self.codes(result))


class ApplyTest(UndoRepo):
    def test_expected_head_mismatch_refused(self):
        rc, result = run("apply", "--repo", self.repo, "--to", self.base,
                         "--expected-head", self.a)
        self.assertEqual(rc, 1)
        self.assertFalse(result["applied"])
        self.assertIn("HEAD moved", result["refused"])
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), self.b)
        self.assertEqual(git(self.repo, "for-each-ref", "refs/devflow"), "")

    def test_blocked_preview_refuses_apply(self):
        Path(self.repo, "a.txt").write_text("edited\n")
        rc, result = run("apply", "--repo", self.repo, "--to", self.base,
                         "--expected-head", self.b)
        self.assertEqual(rc, 1)
        self.assertFalse(result["applied"])
        self.assertIn("dirty-tree", {b["code"] for b in result["preview"]["blocked"]})
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), self.b)
        self.assertEqual(Path(self.repo, "a.txt").read_text(), "edited\n")

    def test_apply_moves_branch_keeps_backup_and_pushes_nothing(self):
        before = self.origin_refs()
        _, preview = self.preview(self.base)
        params = preview["apply"]
        rc, result = run("apply", "--repo", params["repo"], "--to", params["to"],
                         "--expected-head", params["expected_head"])
        self.assertEqual(rc, 0, result)
        self.assertTrue(result["applied"])
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), self.base)
        self.assertEqual(git(self.repo, "symbolic-ref", "--short", "HEAD"), "flow/feature")
        self.assertFalse(Path(self.repo, "a.txt").exists())
        self.assertTrue(result["backup_ref"].startswith("refs/devflow/undo/"))
        self.assertEqual(git(self.repo, "rev-parse", result["backup_ref"]), self.b)
        self.assertEqual(self.origin_refs(), before)
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")
        # The documented restore path works.
        git(self.repo, "reset", "-q", "--hard", result["backup_ref"])
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), self.b)


class ExplicitOnlyTest(unittest.TestCase):
    def test_skill_frontmatter_is_explicit_only(self):
        text = SKILL.read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        self.assertIn("\ndisable-model-invocation: true\n", frontmatter)

    def test_validator_rejects_flow_undo_without_explicit_only(self):
        tmp = tempfile.mkdtemp(prefix="flow-undo-validate-")
        self.addCleanup(shutil.rmtree, tmp)
        for rel in ("scripts", "plugins", ".claude-plugin", ".agents"):
            shutil.copytree(ROOT / rel, Path(tmp, rel))
        script = [sys.executable, str(Path(tmp, "scripts/validate-plugin.py"))]
        self.assertEqual(subprocess.run(script, capture_output=True).returncode, 0)
        skill = Path(tmp, "plugins/devflow/skills/flow-undo/SKILL.md")
        skill.write_text(skill.read_text().replace("disable-model-invocation: true\n", ""))
        out = subprocess.run(script, capture_output=True, text=True)
        self.assertEqual(out.returncode, 1)
        self.assertIn("flow-undo/SKILL.md: explicit-only skill must set "
                      "disable-model-invocation: true", out.stdout)


if __name__ == "__main__":
    unittest.main()
