"""Contract tests for the executor Haiku lane.

hosts.md holds the one deterministic criterion for spawning flow-executor on haiku and
its single sonnet retry; the dispatching skills must point at it, and the agent file
keeps sonnet as the default.
"""
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1] / "plugins/devflow"


def read(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


class HaikuLane(unittest.TestCase):
    def test_criterion_and_escalation_live_in_hosts(self):
        text = read("references/hosts.md")
        self.assertEqual(text.count("**Haiku lane**"), 1)
        for clause in ('`model: "haiku"`', "the only plan in its wave",
                       "`agents.models.executor` is unset", "`<falsify>`", "`checkpoint:*`",
                       '`model: "sonnet"`', "never a second retry",
                       "Tell the executor the model you passed"):
            self.assertIn(clause, text)

    def test_dispatchers_point_at_the_lane(self):
        for rel in ("skills/flow-execute/SKILL.md", "skills/flow-quick/SKILL.md"):
            self.assertIn("Haiku lane", read(rel), rel)

    def test_executor_default_stays_sonnet(self):
        self.assertIn("\nmodel: sonnet\n", read("agents/flow-executor.md"))


if __name__ == "__main__":
    unittest.main()
