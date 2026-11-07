"""Opt-in observed usage: the bridge's `usage` object and the flow-usage.py report.

protects: a user-visible behaviour through a real entry point — both scripts run as
subprocesses; the bridge talks to fake peer CLIs. Every fixture here is SYNTHETIC; none of
these numbers is a real provider observation. The report exists to compare executor lanes
honestly, so the failures that matter are an unobserved value shown as a number, a partial
sum shown as complete, and a dispatch counted twice.
"""
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "plugins/devflow/scripts/flow-agent.py"
REPORT = ROOT / "plugins/devflow/scripts/flow-usage.py"
GOOD = {"status": "COMPLETED", "summary": "done", "artifacts": [], "completed": ["abc123"],
        "checkpoint": None, "error": None}
SECRET_PROMPT = "PROMPT-TEXT-MUST-NOT-LEAK"
# Shape observed from `claude -p --output-format json` on Claude Code 2.1.319, values synthetic.
# Top-level `usage` is only the final message; `modelUsage` is the cumulative figure.
CLAUDE_OUT = {
    "structured_output": GOOD,
    "usage": {"input_tokens": 10, "output_tokens": 149, "cache_read_input_tokens": 3,
              "cache_creation_input_tokens": 4},
    "modelUsage": {
        "claude-haiku-4-5": {"inputTokens": 38, "outputTokens": 662,
                             "cacheReadInputTokens": 84991, "cacheCreationInputTokens": 31441},
        "claude-sonnet-4-5": {"inputTokens": 1, "outputTokens": 2,
                              "cacheReadInputTokens": 3, "cacheCreationInputTokens": 4},
    },
}


class Repo:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "repo"
        (self.root / ".git").mkdir(parents=True)
        (self.root / ".planning").mkdir()
        self.bin = Path(self.temp.name) / "bin"
        self.bin.mkdir()
        self.prompt = Path(self.temp.name) / "prompt.md"
        self.prompt.write_text(SECRET_PROMPT, encoding="utf-8")

    def config(self, **values):
        (self.root / ".planning/config.json").write_text(json.dumps(values), encoding="utf-8")

    def fake(self, name, stdout, code=0):
        path = self.bin / name
        body = json.dumps(stdout) if not isinstance(stdout, str) else stdout
        path.write_text("#!/bin/sh\nprintf '%s' '" + body.replace("'", "'\\''")
                        + f"'\nexit {code}\n", encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def bridge(self, provider, role="executor"):
        env = os.environ.copy()
        env["PATH"] = str(self.bin) + os.pathsep + env.get("PATH", "")
        host = "claude" if provider == "codex" else "codex"
        return subprocess.run([sys.executable, str(BRIDGE), "--host", host, "--provider",
                               provider, "--role", role, "--repo", str(self.root),
                               "--prompt-file", str(self.prompt)],
                              text=True, capture_output=True, env=env)

    def artifact(self, rel, usage=None, plan="01-01"):
        path = self.root / ".planning" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["<!-- template comment -->", "---", f"plan: {plan}", "status: complete"]
        if usage is not None:
            lines.append("usage: " + json.dumps(usage))
        path.write_text("\n".join(lines + ["---", "Body text."]) + "\n", encoding="utf-8")

    def report(self, *args):
        return subprocess.run([sys.executable, str(REPORT), "--repo", str(self.root), *args],
                              text=True, capture_output=True)


def rec(n, kind, tokens, duration, model="haiku", source="agent-tool", role="executor"):
    return {"role": role, "n": n, "kind": kind, "source": source, "provider": "claude",
            "model": model, "tokens": tokens, "duration_ms": duration}


def rows(stdout):
    return [line for line in stdout.splitlines() if line.startswith("| ") and "---" not in line]


class BridgeUsageTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.temp.cleanup)

    def test_default_disabled_output_is_the_pre_feature_bytes(self):
        # Pre-feature contract: exactly the compact result JSON and a newline, nothing added.
        expected = json.dumps(GOOD, separators=(",", ":")) + "\n"
        self.repo.fake("claude", CLAUDE_OUT)
        for config in (None, {"agents": {"provider": "native"}}, {"usage_report": False}):
            if config is not None:
                self.repo.config(**config)
            run = self.repo.bridge("claude")
            self.assertEqual((0, expected), (run.returncode, run.stdout), config)

    def test_claude_tokens_are_model_usage_summed_not_top_level_usage(self):
        self.repo.config(usage_report=True)
        self.repo.fake("claude", CLAUDE_OUT)
        run = self.repo.bridge("claude")
        value = json.loads(run.stdout)
        self.assertEqual(0, run.returncode)
        usage = value.pop("usage")
        self.assertEqual(GOOD, value)
        self.assertEqual(38 + 662 + 84991 + 31441 + 1 + 2 + 3 + 4, usage["tokens"])
        self.assertEqual({"source": "claude-cli", "provider": "claude", "model": "unknown"},
                         {k: usage[k] for k in ("source", "provider", "model")})
        self.assertIsInstance(usage["duration_ms"], int)
        self.assertNotIn(SECRET_PROMPT, run.stdout)

    def test_codex_tokens_are_unknown_never_zero(self):
        self.repo.config(usage_report=True)
        self.repo.fake("codex", GOOD)
        usage = json.loads(self.repo.bridge("codex", role="reviewer").stdout)["usage"]
        self.assertEqual(("codex-cli", "unknown"), (usage["source"], usage["tokens"]))

    def test_incomplete_model_usage_is_unknown_and_observed_zero_stays_zero(self):
        self.repo.config(usage_report=True)
        broken = dict(CLAUDE_OUT, modelUsage={"m": {"inputTokens": 5, "outputTokens": 5}})
        self.repo.fake("claude", broken)
        self.assertEqual("unknown", json.loads(self.repo.bridge("claude").stdout)["usage"]["tokens"])
        zero = dict(CLAUDE_OUT, modelUsage={"m": {"inputTokens": 0, "outputTokens": 0,
                                                  "cacheReadInputTokens": 0,
                                                  "cacheCreationInputTokens": 0}})
        self.repo.fake("claude", zero)
        self.assertEqual(0, json.loads(self.repo.bridge("claude").stdout)["usage"]["tokens"])

    def test_failed_peer_still_reports_its_usage(self):
        # A failed attempt consumed something; dropping it would understate a retried lane.
        self.repo.config(usage_report=True)
        self.repo.fake("claude", CLAUDE_OUT, code=1)
        run = self.repo.bridge("claude")
        value = json.loads(run.stdout)
        self.assertEqual(("FAILED", 2), (value["status"], run.returncode))
        self.assertEqual(117142, value["usage"]["tokens"])

    def test_non_boolean_setting_fails_before_dispatch(self):
        self.repo.config(usage_report="yes")
        self.repo.fake("claude", CLAUDE_OUT)
        run = self.repo.bridge("claude")
        self.assertEqual(2, run.returncode)
        self.assertIn("usage_report must be true or false", json.loads(run.stdout)["error"])


class UsageReportTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.addCleanup(self.repo.temp.cleanup)

    def test_disabled_by_default_reports_nothing(self):
        self.repo.artifact("phases/01-a/01-01-SUMMARY.md", [rec(1, "first", 5, 5)])
        for config in (None, {"mode": "interactive"}, {"usage_report": False}):
            if config is not None:
                self.repo.config(**config)
            run = self.repo.report()
            self.assertEqual(0, run.returncode)
            self.assertTrue(run.stdout.startswith("usage report: disabled"), run.stdout)
            self.assertNotIn("|", run.stdout)

    def test_groups_by_phase_and_role_with_retries_zero_unknown_and_partial(self):
        self.repo.config(usage_report=True)
        # Phase 01, plan 01-01: haiku attempt, then the lane's sonnet retry.
        self.repo.artifact("phases/01-a/01-01-SUMMARY.md",
                           [rec(1, "first", 100, 10), rec(2, "retry", 300, 30, model="sonnet")])
        # Plan 01-02: an observed zero and an unknown, plus a checkpoint continuation.
        self.repo.artifact("phases/01-a/01-02-SUMMARY.md",
                           [rec(1, "first", 0, "unknown"), rec(2, "continuation", "unknown", 7)],
                           plan="01-02")
        self.repo.artifact("phases/01-a/VERIFICATION.md",
                           [rec(1, "first", "unknown", "unknown", model="opus", role="verifier")])
        self.repo.artifact("phases/02-b/02-01-SUMMARY.md", [rec(1, "first", 0, 0)], plan="02-01")
        self.repo.artifact("phases/02-b/02-02-SUMMARY.md", None, plan="02-02")
        run = self.repo.report()
        self.assertEqual(0, run.returncode, run.stderr)
        self.assertEqual([
            "| Phase | Role | Source | Dispatches | Retries | Tokens | Duration ms (sum) |",
            "| 01 | executor | agent-tool | 4 | 1 | partial: 400 (3/4 known) | partial: 47 (3/4 known) |",
            "| 01 | verifier | agent-tool | 1 | 0 | unknown | unknown |",
            "| 02 | executor | agent-tool | 1 | 0 | 0 | 0 |",
            # 02-02 has no `usage` line: its own all-unknown row, so phase 02 never reads complete.
            "| 02 | executor | not recorded | unknown (1 unrecorded) | unknown | unknown | unknown |",
            "| Role | Provider | Model | Source | Dispatches | Retries | Tokens | Duration ms (sum) |",
            "| executor | claude | haiku | agent-tool | 4 | 0 | partial: 100 (3/4 known) | partial: 17 (3/4 known) |",
            "| executor | claude | sonnet | agent-tool | 1 | 1 | 300 | 30 |",
            "| executor | unknown | unknown | not recorded | unknown (1 unrecorded) | unknown | unknown | unknown |",
            "| verifier | claude | opus | agent-tool | 1 | 0 | unknown | unknown |",
        ], rows(run.stdout))
        self.assertIn("Not recorded (no `usage` line; not in the totals): 02/02-02", run.stdout)

    def test_sources_are_never_summed_together(self):
        self.repo.config(usage_report=True)
        self.repo.artifact("phases/01-a/01-01-SUMMARY.md",
                           [rec(1, "first", 100, 1), rec(2, "retry", 50, 1, source="claude-cli")])
        sources = [r.split(" | ")[2] for r in rows(self.repo.report("--phase", "01").stdout)[1:3]]
        self.assertEqual(["agent-tool", "claude-cli"], sources)

    def test_duplicate_dispatch_is_refused_not_counted_twice(self):
        self.repo.config(usage_report=True)
        self.repo.artifact("phases/01-a/01-01-SUMMARY.md",
                           [rec(1, "first", 100, 1), rec(1, "first", 100, 1)])
        run = self.repo.report()
        self.assertEqual(2, run.returncode)
        self.assertIn("counted twice", run.stderr)

    def test_records_carry_metadata_only(self):
        self.repo.config(usage_report=True)
        for bad, needle in (({**rec(1, "first", 1, 1), "prompt": "hello"}, "not allowed"),
                            (rec(1, "first", True, 1), "tokens must be"),
                            (rec(1, "first", "17,439", 1), "tokens must be"),
                            (rec(1, "retry", 1, 1), "does not fit"),
                            ({**rec(1, "first", 1, 1), "model": "see my notes here"}, "model")):
            self.repo.artifact("phases/01-a/01-01-SUMMARY.md", [bad])
            run = self.repo.report()
            self.assertEqual(2, run.returncode, bad)
            self.assertIn(needle, run.stderr, bad)

    def test_unmatched_phase_filter_is_an_error_not_an_empty_report(self):
        self.repo.config(usage_report=True)
        self.repo.artifact("phases/03-x/03-01-SUMMARY.md", [rec(1, "first", 1, 1)])
        run = self.repo.report("--phase", "3")
        self.assertEqual(2, run.returncode)
        self.assertIn("no SUMMARY or VERIFICATION for phase '3'", run.stderr)

    def test_provider_model_ids_with_version_suffix_are_accepted(self):
        self.repo.config(usage_report=True)
        self.repo.artifact("phases/01-a/01-01-SUMMARY.md",
                           [rec(1, "first", 1, 1, model="claude-sonnet-4-5@20250929")])
        self.assertEqual(0, self.repo.report().returncode)

    def test_quick_tasks_report_as_phase_quick(self):
        self.repo.config(usage_report=True)
        self.repo.artifact("quick/017-SUMMARY.md", [rec(1, "first", 9, 9)], plan="017")
        self.assertEqual("| quick | executor | agent-tool | 1 | 0 | 9 | 9 |",
                         rows(self.repo.report("--phase", "quick").stdout)[1])


if __name__ == "__main__":
    unittest.main()
