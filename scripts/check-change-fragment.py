#!/usr/bin/env python3
"""Fail a pull request that ships plugin content without a change fragment, or that edits
the shared release lines outside a release.

Parallel PRs used to each bump the three manifest `version` lines and prepend a CHANGELOG
entry, so every pair of them conflicted textually on the same lines and reused or skipped
versions. Now a feature PR adds one `changes/<slug>.md` fragment instead:

    bump: minor
    The CHANGELOG bullet text.

(or the same `bump:` line inside `---` front matter). `scripts/release-cut.py` later turns
every fragment into one version and one CHANGELOG entry on a `release/X.Y.Z` branch.

Rules, all fail-closed:
- shipped content (`plugins/devflow/**`) changed -> at least one added fragment;
- every added or edited fragment has a valid `bump:` line and bullet text;
- a non-release PR may not touch a manifest `version` line or CHANGELOG.md;
- a release PR (branch `release/*`, or a diff that is only release-cut output) may, and its
  CHANGELOG top entry must name the new plugin.json version.

Usage: check-change-fragment.py <base-ref> <head-branch>. Stdlib only.
"""

import json
import re
import subprocess
import sys
from typing import NamedTuple

SHIPPED_PREFIX = "plugins/devflow/"
MANIFEST = "plugins/devflow/.claude-plugin/plugin.json"
MANIFESTS = (MANIFEST, "plugins/devflow/.codex-plugin/plugin.json", ".claude-plugin/marketplace.json")
CHANGELOG = "CHANGELOG.md"
FRAGMENT_RE = re.compile(r"^changes/(?!README\.md$)[^/]+\.md$")
BUMP_RE = re.compile(r"^bump:\s*(major|minor|patch)\s*$")
VERSION_LINE_RE = re.compile(r'^[+-](?![+-]).*"version"\s*:')
FIX = "add a changes/<slug>.md fragment instead (first line `bump: major|minor|patch`, then the CHANGELOG bullet; see docs/releasing.md)"


class Result(NamedTuple):
    failures: list
    notes: list


def parse_fragment(text):
    """(bump, bullet) or raise ValueError. Shared with release-cut.py."""
    lines = text.strip().splitlines()
    if lines and lines[0].strip() == "---":
        try:
            end = [line.strip() for line in lines].index("---", 1)
        except ValueError:
            raise ValueError("front matter is not closed with ---")
        header, body = lines[1:end], lines[end + 1:]
    else:
        header, body = lines[:1], lines[1:]
    bumps = [m.group(1) for m in (BUMP_RE.match(line.strip()) for line in header) if m]
    if len(bumps) != 1:
        raise ValueError("needs exactly one `bump: major|minor|patch` line")
    body = "\n".join(body).strip()
    if not body:
        raise ValueError("has no CHANGELOG bullet text after the bump line")
    return bumps[0], body if body.startswith("- ") else "- " + " ".join(body.split())


def _git(root, *args):
    proc = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    return proc.returncode == 0, proc.stdout


def _changes(root, base_ref):
    """{path: status letter} for HEAD since it diverged from base_ref, or None. NUL-separated
    so a non-ASCII path is not C-quoted past the prefix match; --no-renames so a file moved
    out of the payload still shows as a shipped deletion."""
    ok, out = _git(root, "diff", "-z", "--no-renames", "--name-status", f"{base_ref}...HEAD")
    if not ok:
        return None
    parts = [p for p in out.split("\0") if p]
    return {parts[i + 1]: parts[i][0] for i in range(0, len(parts) - 1, 2)}


def _version_line_edits(root, base_ref):
    ok, out = _git(root, "diff", "-U0", f"{base_ref}...HEAD", "--", *MANIFESTS)
    return [line for line in out.splitlines() if VERSION_LINE_RE.match(line)] if ok else None


def _plugin_version(root, ref):
    ok, out = _git(root, "show", f"{ref}:{MANIFEST}")
    try:
        version = json.loads(out).get("version") if ok else None
    except (json.JSONDecodeError, AttributeError):
        version = None
    return version if isinstance(version, str) and version else None


def _is_release_cut_output(changes):
    """Only the three manifests, CHANGELOG.md and deleted fragments — what release-cut writes."""
    deleted = [p for p, s in changes.items() if FRAGMENT_RE.match(p) and s == "D"]
    rest = [p for p in changes if p not in MANIFESTS and p != CHANGELOG and p not in deleted]
    return bool(deleted) and not rest


def check(root, base_ref, head_branch):
    """Empty `failures` means the diff is clear to merge."""
    failures, notes = [], []
    changes = _changes(root, base_ref)
    if changes is None:
        return Result([f"could not resolve base ref '{base_ref}' — the check did not run"], notes)

    if head_branch.startswith("release/") or _is_release_cut_output(changes):
        version = _plugin_version(root, "HEAD")
        if version is None:
            return Result([f"{MANIFEST} has no readable version at HEAD"], notes)
        if version == _plugin_version(root, base_ref):
            failures.append(f"release PR but {MANIFEST} is still {version} — run scripts/release-cut.py")
        ok, log = _git(root, "show", f"HEAD:{CHANGELOG}")
        top = next((line for line in log.splitlines() if line.startswith("## ")), "") if ok else ""
        if not top.startswith(f"## {version} ("):
            failures.append(f"release PR: {CHANGELOG} top entry is '{top}', expected '## {version} (YYYY-MM-DD)'")
        notes.append(f"release PR for {version}")
        return Result(failures, notes)

    edits = _version_line_edits(root, base_ref)
    if edits is None:
        return Result(["could not diff the manifests — the check did not run"], notes)
    if edits:
        failures.append(f"manifest version line edited outside a release ({edits[0].strip()}) — {FIX}")
    if CHANGELOG in changes:
        failures.append(f"{CHANGELOG} edited outside a release — {FIX}")

    fragments = sorted(p for p, s in changes.items() if FRAGMENT_RE.match(p) and s != "D")
    for path in fragments:
        ok, text = _git(root, "show", f"HEAD:{path}")
        try:
            bump, _ = parse_fragment(text if ok else "")
            notes.append(f"{path}: bump {bump}")
        except ValueError as error:
            failures.append(f"{path} {error}")

    shipped = sorted(p for p in changes if p.startswith(SHIPPED_PREFIX) or p == SHIPPED_PREFIX.rstrip("/"))
    added = [p for p in fragments if changes[p] == "A"]
    if shipped and not added:
        sample = ", ".join(shipped[:3]) + (f", +{len(shipped) - 3} more" if len(shipped) > 3 else "")
        failures.append(f"{len(shipped)} shipped file(s) changed with no new fragment — {FIX}: {sample}")
    elif not shipped:
        notes.append("no shipped content changed — no fragment required")
    return Result(failures, notes)


def main(argv):
    if len(argv) != 3:
        print("usage: check-change-fragment.py <base-ref> <head-branch>", file=sys.stderr)
        return 2
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    if not root:
        print("not inside a git repository", file=sys.stderr)
        return 2
    print(f"repo: {root}")
    result = check(root, argv[1], argv[2])
    for note in result.notes:
        print(note)
    for failure in result.failures:
        print(f"FAIL: {failure}")
    print(f"{len(result.failures)} failure(s)")
    return 1 if result.failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
