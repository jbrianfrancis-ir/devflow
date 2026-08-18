#!/usr/bin/env python3
"""Guard against a repo path sitting inside a fenced code block on a page
this project writes (D-15/D-19).

`check-links.py` masks fenced code blocks before checking references — by
design, so a runnable example is never mistaken for a broken link. That
means a *real* repo path written inside a fence gets no coverage from that
checker at all: not checked, not reported, silently invisible. This guard
answers the one question `check-links.py` cannot: does a path that exists
in this repo sit inside a fence on README.md or a `docs/*.md` page?

Parity by construction: the fence and frontmatter masks are IMPORTED from
`scripts/check-links.py` (`_code_fence_mask`, `_frontmatter_mask`) rather
than reimplemented. Phase 02's awk guard was a second copy of the fence
rule and drifted from the checker in three ways — no same-character close
rule, no tab-indent handling, and a toggle that inverted on a mismatched
fence character — and it read clean throughout because no page it scanned
happened to exercise any of the three. Importing the checker's own
functions makes that class of drift impossible: there is only one fence
rule in this repo, and this guard uses it instead of guessing at it again.

Stdlib only (ARCHITECTURE.md -> Forbidden: no third-party dependency).
"""

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

# Pages out of scope for this guard: both already carry a repo path inside a
# fence on purpose and are frozen content this project does not rewrite.
# status-contract.md:90 fences `{devflow_root}/scripts/flow-fleet.py`.
FROZEN = ("docs/blitzos.md", "docs/status-contract.md")

DEVFLOW_ROOT_PREFIX = "{devflow_root}/"
DEVFLOW_ROOT_TARGET = "plugins/devflow/"

# The phase-02 token shape, which is check-links.py's backticked-path shape —
# reused here unbackticked, since inside a fence there is no backtick nesting
# to key off; the fence mask itself is what marks the line in scope.
TOKEN_RE = re.compile(r"[A-Za-z0-9_.{}-]+(?:/[A-Za-z0-9_.{}-]+)+\.(?:md|py|json|yml)")


class GuardUnavailable(Exception):
    """scripts/check-links.py could not be loaded — never treated as clean."""


class Violation(NamedTuple):
    file: str
    line: int
    token: str


def _load_checker(root):
    """Import scripts/check-links.py from `root` and return the module.

    Any failure to do so — missing file, unreadable, a syntax error in the
    checker itself — raises GuardUnavailable, which main() turns into a
    non-zero "could not check" exit. This guard has no fence rule of its
    own to fall back on; without the checker it cannot answer its question
    at all, so it must never print a clean result in that case.
    """
    path = Path(root) / "scripts" / "check-links.py"
    try:
        spec = importlib.util.spec_from_file_location("check_links", path)
        if spec is None or spec.loader is None:
            raise GuardUnavailable(f"could not load checker module at {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except GuardUnavailable:
        raise
    except (OSError, SyntaxError) as exc:
        raise GuardUnavailable(f"could not import {path}: {exc}") from exc
    return module


def _scope(root):
    """README.md plus every docs/*.md except the two frozen pages, sorted."""
    docs = sorted(
        p.relative_to(root).as_posix() for p in Path(root).glob("docs/*.md")
    )
    return ["README.md"] + [d for d in docs if d not in FROZEN]


def scan(root):
    """Scan `root`'s in-scope pages for a repo path hidden inside a fence.

    Returns (violations, files_scanned, fenced_lines). Raises
    GuardUnavailable if scripts/check-links.py cannot be loaded from root —
    this is the guard's own fail-closed seam (never called from main()
    without that exception being handled).
    """
    root = Path(root)
    mod = _load_checker(root)
    violations = []
    files_scanned = 0
    fenced_lines = 0

    for relfile in _scope(root):
        path = root / relfile
        try:
            with open(path, encoding="utf-8") as stream:
                lines = stream.read().splitlines()
        except OSError:
            continue
        files_scanned += 1

        front = mod._frontmatter_mask(lines)
        mask, unterminated_at = mod._code_fence_mask(lines, front)
        if unterminated_at is not None:
            # Mirrors check-links.py's own treatment: an unclosed fence is a
            # failure, never a silent mask (conventions.md -> Fail-closed).
            violations.append(
                Violation(relfile, unterminated_at, lines[unterminated_at - 1].strip())
            )

        for i, line in enumerate(lines):
            if not mask[i] or front[i]:
                continue
            fenced_lines += 1
            for match in TOKEN_RE.finditer(line):
                token = match.group(0)
                if token.startswith(".planning/") or token.startswith("~/"):
                    continue  # checker skip rule R4: out-of-scope tree or home-relative
                if token.startswith(DEVFLOW_ROOT_PREFIX):
                    token = DEVFLOW_ROOT_TARGET + token[len(DEVFLOW_ROOT_PREFIX):]
                joined = os.path.normpath(os.path.join(str(root), token))
                if not (joined == str(root) or joined.startswith(str(root) + os.sep)):
                    continue  # never resolve outside root
                if os.path.exists(joined):
                    # A path that does not exist was never checkable prose
                    # anyway — this guard is about coverage the checker
                    # would have provided and lost, not about typos.
                    violations.append(Violation(relfile, i + 1, token))

    return violations, files_scanned, fenced_lines


def _repo_root():
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"not inside a git repository: {result.stderr.strip()}")
    return result.stdout.strip()


def main():
    try:
        root = _repo_root()
        violations, files_scanned, fenced_lines = scan(root)
    except Exception as exc:  # fail-closed: could-not-check is never "0 violations"
        print(f"could not check: {exc}")
        return 2
    for v in violations:
        print(f"{v.file}:{v.line}: {v.token}")
    print(f"{len(violations)} violations, {files_scanned} files scanned, {fenced_lines} fenced lines")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
