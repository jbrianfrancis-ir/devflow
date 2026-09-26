"""Tests for the order of /flow-execute's run steps in its SKILL.md.

Plan lint (#43) and per-executor worktrees (#47) both edit the same pre-flight and wave
steps. The skill is prose an agent follows top to bottom, so the order of the steps in the
text is the order they run: the lint must block before any executor is spawned, and the
wave must land through flow-land.py.
"""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins/devflow/skills/flow-execute/SKILL.md"

# Each step, in the order the skill must run it.
STEPS = (
    ("plan lint", "**Plan lint**: from the repo root run `python3 {devflow_root}/scripts/flow-plan-lint.py"),
    ("worktree pre-flight", "**Worktree pre-flight**"),
    ("wave-start", "flow-land.py wave-start --repo <main checkout>"),
    ("spawn with isolation", 'pass `isolation: "worktree"` explicitly on every Agent call'),
    ("leak-check", "`leak-check --repo <main checkout>`"),
    ("land + re-verify", "`land --repo <main checkout> --plan NN-MM"),
    ("wave-end", "`wave-end --repo <main checkout>`"),
)


class FlowExecuteStepOrderTest(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")

    def test_plan_lint_blocks_before_any_executor(self):
        self.assertIn(STEPS[0][1], self.text)
        self.assertIn("stops the run before any executor is spawned", self.text)

    def test_every_step_is_present(self):
        for label, marker in STEPS:
            self.assertEqual(self.text.count(marker), 1, f"{label}: expected exactly once")

    def test_steps_appear_in_run_order(self):
        positions = [(self.text.find(marker), label) for label, marker in STEPS]
        for (before, first), (after, second) in zip(positions, positions[1:]):
            self.assertLess(before, after, f"{first} must come before {second}")


if __name__ == "__main__":
    unittest.main()
