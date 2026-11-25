"""Plugin content must not tell agents to run `gh` invocations that older `gh` rejects.

`gh pr checks --json` fails on `gh` 2.46.0 with `unknown flag: --json`; it was copied into
`flow-ci` once and hit again in `flow-triager` before this guard existed.
"""
import re
import unittest
from pathlib import Path


PLUGIN = Path(__file__).resolve().parents[1] / "plugins" / "devflow"
PR_CHECKS_JSON = re.compile(r"gh pr checks[^`\n]*--json")


class GhPrChecksJsonTest(unittest.TestCase):
    def test_no_gh_pr_checks_json(self):
        hits = []
        for path in sorted(PLUGIN.rglob("*.md")):
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if PR_CHECKS_JSON.search(line):
                    hits.append(f"{path.relative_to(PLUGIN)}:{lineno}")
        self.assertEqual(hits, [], "`gh pr checks --json` fails on gh 2.46.0 (unknown flag: --json); "
                         "use `gh pr view <n> --json statusCheckRollup` instead")


if __name__ == "__main__":
    unittest.main()
