"""Contract tests for the lite tier and the read-only verifier.

The tier is chosen by /flow-new and read from .planning/config.json by every downstream
skill and agent, so each one must carry its own lite note; and flow-verifier is a
read-only role, so it returns VERIFICATION.md and its callers write it.
"""
import re
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1] / "plugins/devflow"


def read(rel):
    return (PLUGIN / rel).read_text(encoding="utf-8")


class TierSelection(unittest.TestCase):
    def test_flow_new_chooses_and_records_the_tier(self):
        text = read("skills/flow-new/SKILL.md")
        self.assertIn('"tier":"<full|lite>"', text)
        self.assertIn("--tier full|lite", text)
        for signal in ("one repo", "`deploy.tool` null", "~2k LOC"):
            self.assertIn(signal, text)
        self.assertIn("3–6 phases (lite: 1–3)", text)

    def test_every_downstream_reader_has_a_lite_note(self):
        for rel in ("skills/flow-plan/SKILL.md", "skills/flow-execute/SKILL.md",
                    "skills/flow-verify/SKILL.md", "agents/flow-planner.md",
                    "agents/flow-plan-checker.md", "agents/flow-verifier.md",
                    "references/plan-format.md"):
            self.assertRegex(read(rel), r"[Ll]ite tier|tier. is lite", rel)

    def test_lite_uses_existing_model_override_not_a_new_agent(self):
        self.assertIn("pass `sonnet` as the planner's model unless `agents.models.planner` is set",
                      read("skills/flow-plan/SKILL.md"))

    def test_lite_execution_skips_worktrees_and_reverify(self):
        text = read("skills/flow-execute/SKILL.md")
        self.assertIn("with no `isolation`", text)
        self.assertIn("never re-run its `<verify>` checks afterwards", text)


class VerifierIsReadOnly(unittest.TestCase):
    def test_frontmatter_has_no_write_tools(self):
        fm = read("agents/flow-verifier.md").split("---")[1]
        tools = re.search(r"^tools:(.*)$", fm, re.M).group(1)
        self.assertFalse({t.strip().lower() for t in tools.split(",")} & {"write", "edit"})

    def test_verifier_returns_and_callers_write(self):
        self.assertNotIn("Write `VERIFICATION.md`", read("agents/flow-verifier.md"))
        self.assertIn("return its full content", read("agents/flow-verifier.md"))
        for rel in ("skills/flow-execute/SKILL.md", "skills/flow-verify/SKILL.md"):
            self.assertIn("write the `VERIFICATION.md` content it returns", read(rel), rel)


if __name__ == "__main__":
    unittest.main()
