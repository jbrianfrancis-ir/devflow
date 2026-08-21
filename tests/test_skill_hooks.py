"""Tests for validate-plugin.py's skill-hooks check — the D-20 guard.

ARCHITECTURE.md D-20 permits a skill to declare `hooks` in SKILL.md
frontmatter, and makes "structurally validated" one of the four conditions.
Before this guard existed, validate-plugin.py's flat frontmatter parser
dropped every indented line, so the whole hooks: block was invisible: a
renamed event key or a de-indented entry left the full check surface green
while the hook silently never fired. Each test below is one of those
mutations.

check_hooks is driven directly against tempdir fixtures rather than through
the CLI, because the script resolves ROOT from its own location and can only
ever validate this repo's real tree.
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate-plugin.py"

SPEC = importlib.util.spec_from_file_location("validate_plugin", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
try:
    # The script validates this repo at import and exits non-zero on failure.
    # Swallow that here: these tests exercise one function, not the tree.
    SPEC.loader.exec_module(MODULE)
except SystemExit:
    pass

GOOD = """---
name: fixture
description: fixture skill
hooks:
  Stop:
    - hooks:
        - type: prompt
          prompt: |
            Allow stopping when done.
---

Body.
"""


class CheckHooksTests(unittest.TestCase):
    def run_check(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "SKILL.md"
            path.write_text(text, encoding="utf-8")
            MODULE.errors.clear()
            MODULE.check_hooks(str(path), "fixture/SKILL.md")
            return list(MODULE.errors)

    def test_wellformed_prompt_hook_passes(self):
        self.assertEqual(self.run_check(GOOD), [])

    def test_skill_without_hooks_is_not_checked(self):
        text = "---\nname: fixture\ndescription: no hooks here\n---\n\nBody.\n"
        self.assertEqual(self.run_check(text), [])

    def test_unknown_event_key_is_an_error(self):
        found = self.run_check(GOOD.replace("  Stop:", "  Stoop:"))
        self.assertTrue(any("unknown event 'Stoop'" in e for e in found), found)

    def test_command_type_is_refused(self):
        found = self.run_check(GOOD.replace("type: prompt", "type: command"))
        self.assertTrue(any("D-20 permits type: prompt only" in e for e in found), found)

    def test_entry_without_a_type_is_an_error(self):
        found = self.run_check(GOOD.replace("- type: prompt", "- kind: prompt"))
        self.assertTrue(any("no hook entry with a type" in e for e in found), found)

    def test_prompt_key_must_be_the_prompt_key(self):
        # Guards a substring bug: `"prompt:" in line` also matches `notprompt:`.
        found = self.run_check(GOOD.replace("          prompt: |", "          notprompt: |"))
        self.assertTrue(any("no prompt" in e for e in found), found)

    def test_empty_hooks_block_is_an_error(self):
        text = "---\nname: fixture\ndescription: fixture skill\nhooks:\n---\n\nBody.\n"
        found = self.run_check(text)
        self.assertTrue(any("declared but empty" in e for e in found), found)


class ShippedSkillsTests(unittest.TestCase):
    def test_every_shipped_skill_with_hooks_validates(self):
        skills = sorted((ROOT / "plugins/devflow/skills").glob("*/SKILL.md"))
        self.assertTrue(skills, "no skills found")
        for path in skills:
            MODULE.errors.clear()
            MODULE.check_hooks(str(path), str(path.relative_to(ROOT)))
            self.assertEqual(MODULE.errors, [], f"{path.name}: {MODULE.errors}")


if __name__ == "__main__":
    unittest.main()
