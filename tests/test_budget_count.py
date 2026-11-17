"""The size budget gate: `scripts/budget-count.sh --check` passes on this tree and prints every metric."""
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["skills", "agents", "commands", "hooks", "prompt_lines",
        "prompt_bytes_info", "planning_lines_info", "repo_docs_lines_info"]


class BudgetCountTest(unittest.TestCase):
    def test_check_passes_and_prints_all_eight_keys(self):
        result = subprocess.run(["bash", str(ROOT / "scripts" / "budget-count.sh"), "--check"],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        rows = dict(line.split("\t") for line in result.stdout.splitlines() if "\t" in line)
        self.assertEqual(KEYS, list(rows))
        for key in KEYS:
            self.assertRegex(rows[key], r"^\d+$", key)

    def test_repo_docs_do_not_count_as_prompt_lines(self):
        files = {"plugins/devflow/skills/a/SKILL.md": 2, "plugins/devflow/references/ui.json": 3,
                 "plugins/devflow/scripts/x.py": 50, "plugins/devflow/.claude-plugin/plugin.json": 50,
                 "CHANGELOG.md": 7}
        with tempfile.TemporaryDirectory() as tmp:
            def count():
                git("add", "-A")
                out = subprocess.run(["bash", str(ROOT / "scripts" / "budget-count.sh")], cwd=tmp,
                                     capture_output=True, text=True, check=True).stdout
                rows = dict(line.split("\t") for line in out.splitlines())
                return int(rows["prompt_lines"]), int(rows["repo_docs_lines_info"])
            git = lambda *a: subprocess.run(["git", "-C", tmp, *a], check=True, capture_output=True)
            git("init", "-q")
            for name, n in files.items():
                (Path(tmp) / name).parent.mkdir(parents=True, exist_ok=True)
                (Path(tmp) / name).write_text("x\n" * n)
            self.assertEqual((5, 7), count())
            (Path(tmp) / "CHANGELOG.md").write_text("x\n" * 100)
            self.assertEqual((5, 100), count())


if __name__ == "__main__":
    unittest.main()
