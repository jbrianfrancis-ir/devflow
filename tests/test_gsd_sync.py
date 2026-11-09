"""Prose contracts from the 0.48.0 GSD Core sync (v1.15.0-v1.20.1, concepts only).

These rules are prompt content that an orchestrator, executor or migrator follows, so the
only way to keep one from being edited away is to pin its wording. Each test names the GSD
change it rebuilds.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "plugins/devflow"


def read(rel):
    return (P / rel).read_text(encoding="utf-8")


class GsdSyncContracts(unittest.TestCase):
    def test_checker_pass_with_issues_is_an_issue_list(self):
        # gsd-core #5578: a PASSED sentinel that still lists findings skipped revision.
        step = read("skills/flow-plan/SKILL.md").split("4. **Check**", 1)[1].split("\n", 1)[0]
        self.assertIn("says `PASS` but still lists a numbered issue is an issue list", step)

    def test_lint_rules_documented_where_the_script_defines_them(self):
        # gsd-core #4927 (truncated plan) and #4767 (absolute verify target in a worktree).
        doc = read("references/plan-format.md")
        script = read("scripts/flow-plan-lint.py")
        for rule in ("R9", "R10"):
            self.assertIn(f"({rule})", doc)
            self.assertRegex(script, rf"(?m)^  {rule} ")

    def test_executor_stops_on_a_refusal(self):
        # gsd-core #5085: an executor stops on a guard denial instead of routing around it.
        text = read("agents/flow-executor.md")
        self.assertIn("**A refusal is a stop, not a blocker**", text)
        self.assertIn("do not rephrase, split or re-run the command", text)

    def test_uat_deferral_is_human_only_with_a_reason(self):
        # gsd-core #4546: a deliberate deferral does not block, and it is never lost.
        step = read("skills/flow-uat/SKILL.md").split("5. **Acceptance**", 1)[1].split("\n", 1)[0]
        for phrase in ("only the human gives", "only with a reason (none → fail)",
                       "smoke and route-sweep rows cannot be deferred", "SIGNOFF.md lists it",
                       "TODOS.md line"):
            self.assertIn(phrase, step)
        self.assertEqual(read("templates/uat-plan.md").count("[ ] deferred (human only; reason required)"), 2)

    def test_necessity_findings_are_never_blocking(self):
        # gsd-core #4100: necessity review, with its negative space.
        reuse = re.search(r"(?m)^- \*\*reuse\*\* — .*$", read("agents/flow-reviewer.md")).group(0)
        self.assertIn("a guard for a state this stack cannot reach", reuse)
        self.assertIn("never `blocking`", reuse)
        self.assertIn("never a trust-boundary check", reuse)

    def test_migration_handles_milestone_scoped_phase_ids(self):
        # gsd-core #4144/#4698: bracket and milestone-prefixed ids restart per milestone.
        text = read("references/migrate-gsd.md")
        for token in ("phase_id_convention", "milestone-prefixed", "bracket", "project_code",
                      "`999.x`", "`.planning/seeds/SEED-*.md`", "Deferred follow-up:"):
            self.assertIn(token, text)
        self.assertEqual(len(re.findall(r"(?m)^\|.*`\.gsd/`", text)), 1)


if __name__ == "__main__":
    unittest.main()
