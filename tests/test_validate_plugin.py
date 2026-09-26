"""Tests for the explicit-only rules in scripts/validate-plugin.py.

Runs the real validator as CI does (subprocess, exit code, printed errors) against a temp
copy of the parts of this repo it reads, so a mutation never touches the working tree.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COPIED = ("scripts", "plugins", ".claude-plugin", ".agents")
FLAG = "disable-model-invocation: true\n"


class ExplicitOnlySkillsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        for name in COPIED:
            shutil.copytree(ROOT / name, self.tmp / name)

    def skill(self, name):
        return self.tmp / "plugins/devflow/skills" / name / "SKILL.md"

    def run_validator(self):
        return subprocess.run(
            [sys.executable, str(self.tmp / "scripts/validate-plugin.py")],
            capture_output=True, text=True, env=dict(os.environ))

    def test_unmodified_tree_passes(self):
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Plugin OK", result.stdout)

    def test_flag_removed_from_explicit_only_skill_fails(self):
        path = self.skill("flow-release")
        text = path.read_text(encoding="utf-8")
        self.assertIn(FLAG, text)
        path.write_text(text.replace(FLAG, ""), encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("flow-release/SKILL.md: explicit-only skill must set "
                      "disable-model-invocation: true", result.stdout)

    def test_flag_added_to_chained_skill_fails(self):
        path = self.skill("flow-pr")
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("disable-model-invocation", text)
        head, sep, rest = text.partition("\n---")
        path.write_text(head + "\n" + FLAG.rstrip("\n") + sep + rest, encoding="utf-8")
        result = self.run_validator()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("flow-pr/SKILL.md: /flow-next chains to this skill, so it must stay "
                      "model-invocable", result.stdout)


if __name__ == "__main__":
    unittest.main()
