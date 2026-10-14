"""Tests for flow-rework.py — age-weighted rework rate, agent vs non-agent baseline.

Every fixture is a real git repo under the system temp dir, with author and committer
dates pinned per commit so the --window arithmetic is exact. Global and system git config
are masked so a developer's hooks or signing settings can't change the outcome.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins/devflow/scripts/flow-rework.py"
DAY = 86400
T0 = 1_700_000_000  # Nov 2023; the range below starts well before it
AGENT = "\n\nDevFlow-Agent: executor/claude/sonnet\nDevFlow-Plan: 01-01"


class Fixture:
    def __init__(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        empty = self.root / "gitconfig"
        empty.write_text("")
        self.env = {**os.environ, "GIT_CONFIG_GLOBAL": str(empty), "GIT_CONFIG_NOSYSTEM": "1"}
        self.repo = self.root / "repo"
        self.git("init", "-q", "-b", "main", str(self.repo), cwd=self.root)
        for key, value in (("user.name", "T"), ("user.email", "t@example.com"),
                           ("commit.gpgsign", "false")):
            self.git("config", key, value)

    def git(self, *args, cwd=None, env=None):
        result = subprocess.run(["git", "-C", str(cwd or self.repo), *args], capture_output=True,
                                text=True, env=env or self.env)
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
        return result.stdout.strip()

    def commit(self, files, message, day, agent=False):
        """Write {path: text or None (delete)} and commit at T0 + day days."""
        for rel, text in files.items():
            path = self.repo / rel
            if text is None:
                self.git("rm", "-q", rel)
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            self.git("add", rel)
        stamp = f"@{T0 + day * DAY} +0000"
        env = {**self.env, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}
        self.git("commit", "-q", "-m", message + (AGENT if agent else ""), env=env)

    def run(self, *args):
        result = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo),
                                 "--since", "2020-01-01", "--json", *args],
                                capture_output=True, text=True, env=self.env)
        if result.returncode != 0:
            raise AssertionError(f"flow-rework exited {result.returncode}: {result.stderr}")
        return json.loads(result.stdout)


def lines(n, tag):
    return "".join(f"{tag} {i}\n" for i in range(n))


class ReworkTest(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()
        self.addCleanup(self.fx.tempdir.cleanup)
        self.fx.commit({"base.txt": "base\n"}, "chore: init", day=0)

    def test_agent_line_reworked_within_window_is_counted(self):
        self.fx.commit({"a.py": lines(10, "agent")}, "feat: agent work", day=1, agent=True)
        self.fx.commit({"a.py": lines(7, "agent") + "fixed\n"}, "fix: rework", day=5)
        result = self.fx.run()
        self.assertEqual(result["agent"]["lines_added"], 10)
        self.assertEqual(result["agent"]["lines_reworked"], 3)  # 3 removed or modified
        self.assertEqual(result["agent"]["rework_rate_pct"], 30.0)
        self.assertEqual(result["top_files"], [{"path": "a.py", "lines_reworked": 3}])

    def test_change_outside_window_is_not_counted(self):
        self.fx.commit({"a.py": lines(10, "agent")}, "feat: agent work", day=1, agent=True)
        self.fx.commit({"a.py": lines(5, "agent")}, "refactor: much later", day=30)
        result = self.fx.run()
        self.assertEqual(result["agent"]["lines_reworked"], 0)
        self.assertEqual(self.fx.run("--window", "30")["agent"]["lines_reworked"], 5)

    def test_non_agent_baseline_is_separate(self):
        self.fx.commit({"a.py": lines(10, "agent")}, "feat: agent work", day=1, agent=True)
        self.fx.commit({"h.py": lines(20, "human")}, "feat: human work", day=1)
        self.fx.commit({"h.py": None}, "chore: drop it", day=3)
        result = self.fx.run()
        self.assertEqual(result["agent"]["lines_reworked"], 0)
        self.assertEqual(result["agent"]["commits"], 1)
        # base.txt (1 line, day 0) and h.py (20 lines) are the baseline's added lines
        self.assertEqual(result["baseline"]["lines_added"], 21)
        self.assertEqual(result["baseline"]["lines_reworked"], 20)
        self.assertEqual(result["top_files"], [])

    def test_rename_is_not_rework(self):
        self.fx.commit({"a.py": lines(10, "agent")}, "feat: agent work", day=1, agent=True)
        self.fx.git("mv", "a.py", "b.py")
        self.fx.commit({}, "chore: rename", day=2)
        self.assertEqual(self.fx.run()["agent"]["lines_reworked"], 0)

    def test_small_sample_is_stated(self):
        self.fx.commit({"a.py": lines(10, "agent")}, "feat: agent work", day=1, agent=True)
        result = self.fx.run()
        self.assertTrue(result["agent"]["small_sample"])
        self.assertTrue(any("agent: 10 lines added" in n and "too small" in n
                            for n in result["notes"]))

    def test_large_sample_has_no_small_sample_note(self):
        self.fx.commit({"a.py": lines(150, "agent")}, "feat: agent work", day=1, agent=True)
        result = self.fx.run()
        self.assertFalse(result["agent"]["small_sample"])
        self.assertFalse(any(n.startswith("agent:") for n in result["notes"]))

    def test_json_shape(self):
        self.fx.commit({"a.py": lines(10, "agent")}, "feat: agent work", day=1, agent=True)
        result = self.fx.run()
        self.assertEqual(set(result), {"range", "agent", "baseline", "top_files", "notes"})
        self.assertEqual(set(result["range"]), {"since", "head", "window_days"})
        for kind in ("agent", "baseline"):
            self.assertEqual(set(result[kind]), {"commits", "lines_added", "lines_reworked",
                                                 "rework_rate_pct", "small_sample"})
        self.assertEqual(result["range"]["window_days"], 14)
        self.assertEqual(result["range"]["head"], self.fx.git("rev-parse", "HEAD"))

    def test_sha_range_excludes_earlier_commits(self):
        self.fx.commit({"h.py": lines(20, "human")}, "feat: human work", day=1)
        start = self.fx.git("rev-parse", "HEAD")
        self.fx.commit({"a.py": lines(10, "agent")}, "feat: agent work", day=2, agent=True)
        self.fx.commit({"h.py": None}, "chore: drop it", day=3)
        result = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.fx.repo),
                                 "--since", start, "--json"], capture_output=True, text=True,
                                env=self.fx.env)
        data = json.loads(result.stdout)
        self.assertEqual(data["baseline"]["lines_added"], 0)
        self.assertEqual(data["baseline"]["lines_reworked"], 0)  # h.py predates the range
        self.assertEqual(data["agent"]["lines_added"], 10)

    def test_read_only(self):
        self.fx.commit({"a.py": lines(10, "agent")}, "feat: agent work", day=1, agent=True)
        before = self.fx.git("status", "--porcelain=v1", "--untracked-files=all")
        refs = self.fx.git("for-each-ref")
        self.fx.run()
        self.assertEqual(self.fx.git("status", "--porcelain=v1", "--untracked-files=all"), before)
        self.assertEqual(self.fx.git("for-each-ref"), refs)

    def test_not_a_repo_exits_2(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.fx.root)],
                                capture_output=True, text=True, env=self.fx.env)
        self.assertEqual(result.returncode, 2)
        self.assertIn("could not run", result.stderr)


if __name__ == "__main__":
    unittest.main()
