"""Tests for flow-review-gate.py: open finding fails; deferred, closed or absent passes."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "plugins/devflow/scripts/flow-review-gate.py"

REVIEW = """---
status: issues_found
---
## Warnings

### WR-01: Retry loop swallows the timeout

**File:** `src/a.py:12`
**Issue:** the error is dropped.
**Fix:**
```python
# not a heading
raise
```
{disposition}

### IN-01: Naming

**Issue:** style only.
"""


class ReviewGateTest(unittest.TestCase):
    def run_gate(self, review=None, ledger=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".planning").mkdir()
            (root / ".planning/STATE.md").write_text("## Position\nPhase: 3 of 5 (api)\n")
            if review is not None:
                (root / ".planning/phases/03-api").mkdir(parents=True)
                (root / ".planning/phases/03-api/03-REVIEW.md").write_text(review)
            if ledger is not None:
                (root / ".planning/reviews").mkdir()
                (root / ".planning/reviews/LEDGER.md").write_text(ledger)
            return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root)],
                                  capture_output=True, text=True)

    def test_open_warning_fails(self):
        result = self.run_gate(REVIEW.format(disposition=""))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("OPEN .planning/phases/03-api/03-REVIEW.md: WR-01", result.stdout)
        self.assertNotIn("IN-01", result.stdout)

    def test_deferred_and_closed_pass_but_bare_deferral_fails(self):
        for disposition, code in (("deferred: TODOS.md — retry timeout", 0), ("fixed: 1a2b3c4d", 0),
                                  ("refuted: caller already retries", 0), ("deferred: later", 1)):
            with self.subTest(disposition):
                self.assertEqual(self.run_gate(REVIEW.format(disposition=disposition)).returncode, code)

    def test_ledger_current_round_unbackfilled_fix_now_fails(self):
        ledger = ("## Round 1 — 2026-11-01 · r1\n| # | Finding | Lens | Verdict | Disposition |\n|---|---|---|---|---|\n"
                  "| 1 | old | correctness | **CONFIRMED** | **FIX NOW** — x |\n"
                  "## Round 2 — 2026-11-02 · r2\n| # | Finding | Lens | Verdict | Disposition |\n|---|---|---|---|---|\n"
                  "| 1 | a | correctness | **CONFIRMED** | **FIX NOW** — guard → `a.py` (9f8e7d6) |\n"
                  "| 2 | b | tests | **CONFIRMED** | **FIX NOW** — add test → `t.py` |\n")
        result = self.run_gate(ledger=ledger)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertEqual(result.stdout.count("OPEN LEDGER round 2"), 1, result.stdout)

    def test_no_review_file_passes_with_note(self):
        result = self.run_gate()
        self.assertEqual(result.returncode, 0)
        self.assertIn("no review file", result.stdout)


if __name__ == "__main__":
    unittest.main()
