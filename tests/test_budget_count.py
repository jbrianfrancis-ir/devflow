"""The size budget gate: `scripts/budget-count.sh --check` passes on this tree and prints every metric."""
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYS = ["skills", "agents", "commands", "hooks", "prompt_lines",
        "prompt_bytes_info", "planning_lines_info"]


class BudgetCountTest(unittest.TestCase):
    def test_check_passes_and_prints_all_seven_keys(self):
        result = subprocess.run(["bash", str(ROOT / "scripts" / "budget-count.sh"), "--check"],
                                cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        rows = dict(line.split("\t") for line in result.stdout.splitlines() if "\t" in line)
        self.assertEqual(KEYS, list(rows))
        for key in KEYS:
            self.assertRegex(rows[key], r"^\d+$", key)


if __name__ == "__main__":
    unittest.main()
