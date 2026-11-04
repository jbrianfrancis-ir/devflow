"""One-off job routing (/flow-new) and the plan-count guard (flow-plan-lint.py).

The routing is prompt text, so it is checked as text. The guard is deterministic, so it is
run as the real CLI against throwaway phase trees under the system temp dir: it must warn
(exit 0) past 8 plans, or past 2 phases on a lite/one-off job, and stay quiet at 8 / 2.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_flow_plan_lint import git, plan  # noqa: E402  (same fixture shape as the lint tests)

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins/devflow"
SCRIPT = PLUGIN / "scripts/flow-plan-lint.py"
WARN = ("WARN plan-count: {plans} plans across {phases} phases (guard: >8 plans, or >2 phases "
        "on a lite/one-off job). This looks like ceremony for the job size - consider "
        "/flow-quick or direct execution of the remaining work instead of more plans. "
        "Continue only if the extra plans carry real decisions.")


def read(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


class RoutingText(unittest.TestCase):
    def test_flow_new_routes_one_off_jobs_to_lite(self):
        text = read("skills/flow-new/SKILL.md")
        for signal in ("export", "dump", "CSV", "JSON export", "report", "format", "convert",
                       "one-off/one-time script", "backfill"):
            self.assertIn(signal, text)
        self.assertIn("**One-off jobs default to `lite` whatever the size**", text)
        self.assertIn("no long-lived service, no deploy target, and no UI", text)
        self.assertIn("A long-lived service (API, worker, daemon, web app, a scheduled pipeline "
                      "that keeps running) is not one-off", text)
        self.assertIn("Offer `/flow-quick` first", text)
        self.assertIn('`"one_off":true`', text)
        self.assertIn("One-off export/report job -> lite tier (say --tier full to opt in to the "
                      "full loop).", text)
        self.assertIn("never force full silently", text)

    def test_flow_plan_runs_the_guard_before_planning(self):
        text = read("skills/flow-plan/SKILL.md")
        step3 = text[text.index("3. **Plan**"):text.index("spawn `flow-planner`")]
        self.assertIn("--plan-count --adding", step3)
        self.assertIn("never blocks", step3)
        self.assertIn("offer to collapse", step3)
        self.assertIn("log it to JOURNAL.md, and continue", step3)

    def test_thresholds_live_only_in_the_script(self):
        self.assertIn("GUARD_MAX_PLANS = 8\nGUARD_MAX_SMALL_PHASES = 2\n",
                      SCRIPT.read_text(encoding="utf-8"))
        for rel in ("skills/flow-plan/SKILL.md", "skills/flow-new/SKILL.md",
                    "references/plan-format.md"):
            self.assertNotIn(">8", read(rel), rel)
            self.assertNotIn("8 plans", read(rel), rel)


class PlanCountGuard(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = Path(self.tempdir.name) / "repo"
        (self.repo / "src").mkdir(parents=True)
        (self.repo / "src/a.py").write_text("a = 1\n")
        git(self.repo, "init", "-q")
        git(self.repo, "add", "-A")
        git(self.repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid",
            "commit", "-q", "-m", "base")
        self.phases = self.repo / ".planning/phases"

    def tearDown(self):
        self.tempdir.cleanup()

    def tree(self, per_phase, config=None):
        """per_phase: plan counts, one entry per phase dir. Returns the first phase dir."""
        for n, count in enumerate(per_phase, 1):
            d = self.phases / f"{n:02d}-p{n}"
            d.mkdir(parents=True)
            for m in range(1, count + 1):
                (d / f"{n:02d}-{m:02d}-PLAN.md").write_text(plan(f"{n:02d}-{m:02d}"))
        if config is not None:
            (self.repo / ".planning/config.json").write_text(json.dumps(config))
        return self.phases / "01-p1"

    def run_cli(self, phase_dir, *args):
        return subprocess.run([sys.executable, str(SCRIPT), str(phase_dir), *args],
                              cwd=self.repo, capture_output=True, text=True)

    def assert_warns(self, result, plans, phases):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(WARN.format(plans=plans, phases=phases), result.stdout)

    def assert_quiet(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("WARN", result.stdout)

    def test_nine_plans_warn(self):
        self.assert_warns(self.run_cli(self.tree([5, 4]), "--plan-count"), 9, 2)

    def test_eight_plans_quiet(self):
        result = self.run_cli(self.tree([4, 4]), "--plan-count")
        self.assert_quiet(result)
        self.assertIn("plan-count: 8 plans across 2 phases (under the guard)", result.stdout)

    def test_plans_about_to_be_written_count(self):
        first = self.tree([4, 4])
        self.assert_warns(self.run_cli(self.phases / "03-p3", "--plan-count", "--adding", "1"),
                          9, 3)
        self.assert_quiet(self.run_cli(first, "--plan-count", "--adding", "0"))

    def test_lite_three_phases_warn(self):
        self.assert_warns(self.run_cli(self.tree([1, 1, 1], {"tier": "lite"}), "--plan-count"),
                          3, 3)

    def test_lite_two_phases_quiet(self):
        self.assert_quiet(self.run_cli(self.tree([1, 1], {"tier": "lite"}), "--plan-count"))

    def test_one_off_on_full_tier_three_phases_warn(self):
        config = {"tier": "full", "one_off": True}
        self.assert_warns(self.run_cli(self.tree([1, 1, 1], config), "--plan-count"), 3, 3)

    def test_full_tier_three_phases_quiet(self):
        self.assert_quiet(self.run_cli(self.tree([1, 1, 1], {"tier": "full"}), "--plan-count"))

    def test_regular_lint_prints_the_warning_without_failing(self):
        first = self.tree([1, 4, 4])
        result = self.run_cli(first)
        self.assert_warns(result, 9, 3)
        self.assertIn("0 findings", result.stdout)
        data = json.loads(self.run_cli(first, "--json").stdout)
        self.assertEqual(data["findings"], [])
        self.assertEqual(data["plan_count"], WARN.format(plans=9, phases=3))


if __name__ == "__main__":
    unittest.main()
