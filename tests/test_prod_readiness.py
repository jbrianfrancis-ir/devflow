"""Tests for the `/flow-prod-readiness` checklist.

The skill is prompt content, so these pin the contract a caller relies on: all
nine items are defined, results are pass/gap/unknown only, platform changes are
never DevFlow's to make, the skill is explicit-only and never chained per PR,
and the docs index and credit link to it.
"""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = "plugins/devflow/skills/flow-prod-readiness/SKILL.md"
REF = "plugins/devflow/references/prod-readiness.md"


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class ProdReadinessTest(unittest.TestCase):
    def test_nine_items_in_order(self):
        rows = re.findall(r"(?m)^\| (R\d) \| \*\*", read(REF))
        self.assertEqual(rows, [f"R{i}" for i in range(1, 10)])

    def test_items_cover_the_checklist(self):
        text = read(REF).lower()
        for phrase in ("geo-filter", "owasp", "false-positive", "every request",
                       "public network access", "secrets never in code",
                       "who accessed what and when", "tested restore",
                       "graceful shutdown", "other than the builder"):
            self.assertIn(phrase, text, phrase)

    def test_three_results_only(self):
        text = read(REF)
        self.assertIn("Three results only: `pass`, `gap`, `unknown`", text)
        self.assertIn("A check that did not run is `unknown`, never `pass`", text)

    def test_platform_changes_are_never_devflows(self):
        skill, ref = read(SKILL), read(REF)
        for text in (skill, ref):
            self.assertIn("platform owner (human)", text)
        self.assertIn("DevFlow never makes those changes", skill)
        self.assertIn("never DevFlow's, never an executor task", ref)

    def test_read_only_rules(self):
        text = read(REF)
        for rule in ("No `az login`", "no `az account get-access-token`",
                     "Never print or store a secret value", "no attack payloads",
                     "**test plan**"):
            self.assertIn(rule, text, rule)

    def test_explicit_only_and_not_per_pr(self):
        skill = read(SKILL)
        self.assertIn("disable-model-invocation: true", skill)
        self.assertIn("never per PR", skill)
        self.assertIn('"flow-prod-readiness"', read("scripts/validate-plugin.py"))
        self.assertIn("`/flow-prod-readiness`", read("plugins/devflow/references/autonomy.md"))
        for chained in ("flow-next", "flow-pr", "flow-harden", "flow-uat", "flow-release"):
            body = read(f"plugins/devflow/skills/{chained}/SKILL.md")
            self.assertNotIn("flow-prod-readiness", body, chained)

    def test_never_ends_done(self):
        lines = re.findall(r"(?m)^- `FLOW: ([A-Z]+)", read(SKILL))
        self.assertTrue(lines)
        self.assertNotIn("DONE", lines)

    def test_docs_linked_and_credited(self):
        self.assertIn("](prod-readiness.md)", read("docs/README.md"))
        self.assertIn("docs/prod-readiness.md", read("README.md"))
        self.assertIn("Mike Anderson", read("docs/acknowledgements.md"))
        self.assertIn("Mike Anderson", read("docs/prod-readiness.md"))
        self.assertIn("/flow-prod-readiness", read("plugins/devflow/references/aspire.md"))


if __name__ == "__main__":
    unittest.main()
