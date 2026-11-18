"""destructive-git-guard.py's `gh pr create` Merge Danger check (office review 2026-11-18 row 4)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GUARD = Path(__file__).resolve().parents[1] / "plugins/devflow/templates/hooks/destructive-git-guard.py"
GOOD = "## Merge Danger\nMerge Danger: LOW — two-way door; blast radius: docs only"


def run(command, cwd="."):
    payload = json.dumps({"tool_input": {"command": command}, "cwd": str(cwd)})
    return subprocess.run([sys.executable, str(GUARD)], input=payload, capture_output=True, text=True)


class MergeDangerGuardTests(unittest.TestCase):
    def assertBlocked(self, result):
        self.assertEqual(2, result.returncode)
        self.assertIn("PR body needs: 'Merge Danger:", result.stderr)

    def test_allows_full_line_and_other_commands(self):
        for command in (f'gh pr create --title t --body "{GOOD}"', "gh pr list", "ls",
                        'git commit -m "run gh pr create later"'):
            with self.subTest(command=command):
                self.assertEqual(0, run(command).returncode)

    def test_blocks_missing_fill_and_level_only(self):
        for command in ('gh pr create --title t --body "## What\nstuff"', "gh pr create --fill",
                        'gh pr create -b "Merge Danger: LOW"',
                        'gh pr create -b "Merge Danger: HIGH — one-way door"'):
            with self.subTest(command=command):
                self.assertBlocked(run(command))

    def test_body_file_and_stdin(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "good.md").write_text(GOOD, encoding="utf-8")
            Path(tmp, "bad.md").write_text("## What\n", encoding="utf-8")
            self.assertEqual(0, run("gh pr create --body-file good.md", tmp).returncode)
            self.assertBlocked(run("gh pr create -F bad.md", tmp))
        self.assertEqual(0, run(f"gh pr create -F - <<'EOF'\nit's\n{GOOD}\nEOF").returncode)
        self.assertBlocked(run("gh pr create -F - <<'EOF'\nnothing\nEOF"))


if __name__ == "__main__":
    unittest.main()
