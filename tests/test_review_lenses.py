"""Tests for the comprehension/zoom-out review lenses and `/flow-audit --drift`.

The lenses and the drift mode are prompt content, so these pin the contract a
caller relies on: every lens /flow-pr can select is defined in flow-reviewer, the
drift mode keeps its five checks and stays read-only, and the docs name both.
"""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def defined_lenses():
    text = read("plugins/devflow/agents/flow-reviewer.md")
    section = text.split("## Lenses", 1)[1].split("\n## ", 1)[0]
    return set(re.findall(r"(?m)^- \*\*([a-z-]+)\*\* — ", section))


class ReviewLensesTest(unittest.TestCase):
    def test_new_lenses_are_defined(self):
        lenses = defined_lenses()
        for lens in ("comprehension", "zoom-out"):
            self.assertIn(lens, lenses)

    def test_every_lens_flow_pr_selects_is_defined(self):
        step = read("plugins/devflow/skills/flow-pr/SKILL.md")
        step = step.split("2. **Independent review**", 1)[1].split("\n", 1)[0]
        selected = set(re.findall(r"\*\*([a-z-]+)\*\*", step))
        selected.discard("Independent")
        self.assertTrue({"comprehension", "zoom-out"} <= selected, selected)
        self.assertEqual(selected - defined_lenses(), set())

    def test_comprehension_asks_the_four_questions(self):
        text = read("plugins/devflow/agents/flow-reviewer.md")
        line = next(l for l in text.splitlines() if l.startswith("- **comprehension**"))
        for word in ("*what*", "*why*", "**invariant**", "**blast radius**"):
            self.assertIn(word, line)

    def test_docs_list_matches_agent(self):
        docs = read("docs/review.md")
        for lens in ("comprehension", "zoom-out"):
            self.assertIn(lens, docs)


class AuditDriftModeTest(unittest.TestCase):
    def setUp(self):
        text = read("plugins/devflow/skills/flow-audit/SKILL.md")
        _, found, rest = text.partition("## --drift")
        self.assertTrue(found, "flow-audit has no '## --drift' section")
        self.section = rest.split("\n## ", 1)[0]
        self.frontmatter = text.split("---", 2)[1]

    def test_description_names_drift(self):
        self.assertIn("--drift", self.frontmatter)

    def test_five_checks(self):
        for check in ("X1", "X2", "X3", "X4", "X5"):
            self.assertIn(f"**{check} ", self.section)

    def test_read_only_and_fails_closed(self):
        self.assertIn("Strictly read-only", self.section)
        self.assertIn("Write nothing to `.planning/`", self.section)
        self.assertIn("never evidence of a clean result", self.section)

    def test_ends_with_status_lines(self):
        self.assertIn("FLOW: CONTINUE | drift audit clean", self.section)
        self.assertIn("FLOW: GATE | drift audit", self.section)


if __name__ == "__main__":
    unittest.main()
