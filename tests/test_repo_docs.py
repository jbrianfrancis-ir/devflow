"""Tests for repo-internal docs rules: the host smoke receipt and the non-goals record.

These read this repo's own files, because the rules are about those files: the PR
template must ask for a per-host receipt, the two root pointer files must stay
byte-identical and name it, and the maintainer's standing rule must stay on record.
"""
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STANDING_RULE = ("Never merge without a PR, anywhere, because it removes checks and "
                 "documentation.")


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


class HostSmokeReceiptTemplateTest(unittest.TestCase):
    def setUp(self):
        text = read(".github/pull_request_template.md")
        _, found, self.section = text.partition("## Host smoke receipt")
        self.assertTrue(found, "PR template has no '## Host smoke receipt' section")
        self.section = self.section.split("\n## ", 1)[0]

    def test_one_row_per_host(self):
        for host in ("Claude Code", "Codex"):
            self.assertRegex(self.section, rf"(?m)^\| {re.escape(host)} \|",
                             f"no receipt row for {host}")

    def test_not_run_needs_a_reason_and_rows_are_never_blank(self):
        self.assertIn("NOT RUN — <reason>", self.section)
        self.assertIn("never blank or removed", self.section)


class RootPointerFilesTest(unittest.TestCase):
    def test_agents_and_claude_md_are_byte_identical(self):
        self.assertEqual((ROOT / "AGENTS.md").read_bytes(), (ROOT / "CLAUDE.md").read_bytes())

    def test_repo_note_requires_the_receipt_and_names_the_load_command(self):
        note = read("AGENTS.md").partition("## Note for this repo specifically")[2]
        self.assertIn("host smoke receipt", note)
        self.assertIn("plugins/devflow/**", note)
        self.assertIn("claude --plugin-dir", note)


class NonGoalsDocTest(unittest.TestCase):
    def setUp(self):
        self.text = read("docs/non-goals.md")

    def test_standing_rule_is_verbatim(self):
        standing = self.text.partition("## Standing rules")[2].split("\n## ", 1)[0]
        self.assertIn(STANDING_RULE, " ".join(standing.split()))

    def test_direct_merge_mode_is_a_recorded_non_goal(self):
        non_goals = self.text.partition("## Non-goals")[2]
        row = next((line for line in non_goals.splitlines() if line.startswith("| I1 |")), "")
        self.assertIn("`direct` integration mode", row)
        self.assertIn("https://github.com/open-gsd/gsd-path/blob/v1.3.1/WORKFLOW.md", row)

    def test_linked_from_docs_index(self):
        self.assertIn("](non-goals.md)", read("docs/README.md"))


if __name__ == "__main__":
    unittest.main()
