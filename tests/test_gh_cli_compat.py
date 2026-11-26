"""Plugin content must not tell agents to run `gh` invocations that older `gh` rejects.

`gh pr checks --json` fails on `gh` 2.46.0 with `unknown flag: --json`; it was copied into
`flow-ci` once and hit again in `flow-triager` before this guard existed.
"""
import re
import unittest
from pathlib import Path


PLUGIN = Path(__file__).resolve().parents[1] / "plugins" / "devflow"
PR_CHECKS_JSON = re.compile(r"gh pr checks[^`\n]*--json")
FENCE = re.compile(r"^\s*```.*?^\s*```", re.S | re.M)
SPAN = re.compile(r"`([^`]+)`")


def find_hits(text):
    """Line numbers of `gh pr checks … --json`, on one line or in an inline-code span wrapped across lines."""
    hits = [n for n, line in enumerate(text.splitlines(), 1) if PR_CHECKS_JSON.search(line)]
    prose = FENCE.sub(lambda m: "\n" * m.group().count("\n"), text)
    for m in SPAN.finditer(prose):
        if "\n" in m.group(1) and PR_CHECKS_JSON.search(" ".join(m.group(1).split())):
            hits.append(prose.count("\n", 0, m.start()) + 1)
    return hits


class GhPrChecksJsonTest(unittest.TestCase):
    def test_find_hits_catches_wrapped_span_and_skips_flag_mention(self):
        self.assertEqual(find_hits("run `gh pr checks 5 --json name`\n"), [1])
        self.assertEqual(find_hits("intro\nrun `gh pr\nchecks 5 --json name` now\n"), [2])
        self.assertEqual(find_hits("the `--json` flag of `gh pr checks` is missing\n"), [])

    def test_no_gh_pr_checks_json(self):
        hits = []
        for path in sorted(PLUGIN.rglob("*.md")):
            hits += [f"{path.relative_to(PLUGIN)}:{n}" for n in find_hits(path.read_text(encoding="utf-8"))]
        self.assertEqual(hits, [], "`gh pr checks --json` fails on gh 2.46.0 (unknown flag: --json); "
                         "use `gh pr view <n> --json statusCheckRollup` instead")


if __name__ == "__main__":
    unittest.main()
