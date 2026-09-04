#!/usr/bin/env python3
"""Fail a pull request that changes shipped plugin content without bumping the version.

`release.yml` cuts a tag only when `plugins/devflow/.claude-plugin/plugin.json` carries
a version it has not already released. A PR that ships agent, skill, reference or
template changes without advancing that field merges green and releases nothing: the
workflow prints "already released — nothing to do" and exits 0, so a missed bump is
indistinguishable from a successful release in the Actions list. This turns it red.

`/flow-pr` step 2c asks for the same bump, but that is one step inside one skill — a PR
opened by hand bypasses it entirely. This is the deterministic backstop for every path.

Stdlib only — no network, no third-party import.
"""

import json
import os
import re
import subprocess
import sys
from typing import NamedTuple

SHIPPED_PREFIX = "plugins/devflow/"
MANIFEST = "plugins/devflow/.claude-plugin/plugin.json"
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")

# A manifest read resolves to one of three states, and they are not interchangeable:
# ABSENT means there is nothing to advance (a plugin this diff introduces) and passes,
# while UNREADABLE means the check could not be performed and must fail. Collapsing
# them to None is a fail-open inside a guard whose whole contract is fail-closed.
ABSENT = "absent"
UNREADABLE = "unreadable"


class Result(NamedTuple):
    failures: list
    notes: list
    checked: int


# --- git ---------------------------------------------------------------------

def _git(root, *args):
    """Run git in `root`, returning (ok, stdout). Never raises on a git failure —
    the caller decides whether an unresolvable ref is fatal."""
    proc = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    return proc.returncode == 0, proc.stdout


def _changed_files(root, base_ref):
    """Paths changed on HEAD since it diverged from base_ref, or None if the ref does
    not resolve. Three-dot: the PR's own changes, not the base's.

    NUL-separated deliberately. Plain `--name-only` C-quotes any path holding a
    non-ASCII or control byte (`"plugins/devflow/skills/na\\303\\257ve/SKILL.md"`), which
    no prefix match catches — the guard would then report green on precisely the change
    it exists to catch. Same trap ARCHITECTURE.md records for `check-links.py`.

    `--no-renames` for the mirror-image hole: rename detection reports a move as its
    destination alone, so a shipped file moved *out* of the payload leaves nothing
    matching the prefix. The payload loses a skill, the guard sees repo-internal
    churn. Suppressed, the move reads as a delete plus an add and the shipped
    deletion is visible.
    """
    ok, out = _git(root, "diff", "-z", "--no-renames", "--name-only", f"{base_ref}...HEAD")
    if not ok:
        return None
    return [path for path in out.split("\0") if path]


# --- manifest ----------------------------------------------------------------

def _version_from(text):
    """(state, version) for a manifest's contents. A manifest with no `version` key is
    unreadable for this purpose: something is there, and it is not a version."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return (UNREADABLE, None)
    if not isinstance(data, dict):
        return (UNREADABLE, None)
    version = data.get("version")
    if not isinstance(version, str) or not version:
        return (UNREADABLE, None)
    return ("ok", version)


def _version_at(root, ref):
    ok, out = _git(root, "show", f"{ref}:{MANIFEST}")
    if not ok:
        return (ABSENT, None)
    return _version_from(out)


def _version_on_disk(root):
    """The working tree's version, so this also answers before the bump is committed."""
    path = os.path.join(root, MANIFEST)
    if not os.path.exists(path):
        return (ABSENT, None)
    with open(path, encoding="utf-8") as stream:
        return _version_from(stream.read())


# --- check -------------------------------------------------------------------

def check(root, base_ref):
    """Empty `failures` means the diff is clear to merge."""
    failures, notes = [], []

    changed = _changed_files(root, base_ref)
    if changed is None:
        # Fail closed: a comparison that did not run is never a clean one.
        return Result([f"could not resolve base ref '{base_ref}' — the check did not run"], notes, 0)

    shipped = sorted(path for path in changed if path.startswith(SHIPPED_PREFIX))
    if not shipped:
        notes.append("no shipped content changed — no bump required")
        return Result(failures, notes, 0)

    head_state, head_version = _version_on_disk(root)
    if head_state != "ok":
        return Result([f"{MANIFEST} is {head_state} — cannot verify the version"], notes, len(shipped))

    base_state, base_version = _version_at(root, base_ref)
    if base_state == UNREADABLE:
        return Result(
            [f"{MANIFEST} is unreadable at {base_ref} — cannot verify the version advanced"],
            notes,
            len(shipped),
        )
    if base_state == ABSENT:
        notes.append(f"no manifest at {base_ref} — treating {head_version} as the first version")
        return Result(failures, notes, len(shipped))

    if head_version == base_version:
        sample = ", ".join(shipped[:3]) + (f", +{len(shipped) - 3} more" if len(shipped) > 3 else "")
        failures.append(
            f"{len(shipped)} shipped file(s) changed but the version is still {head_version} "
            f"— bump {MANIFEST} (and the Codex manifest and marketplace entry with it): {sample}"
        )
        return Result(failures, notes, len(shipped))

    head_parts, base_parts = SEMVER_RE.match(head_version), SEMVER_RE.match(base_version)
    if head_parts and base_parts:
        if tuple(map(int, head_parts.groups())) <= tuple(map(int, base_parts.groups())):
            failures.append(f"version moves backwards: {base_version} -> {head_version}")
    else:
        notes.append(
            f"version changed {base_version} -> {head_version}; ordering unverified "
            "(not a plain X.Y.Z on one side)"
        )

    notes.append(f"version {base_version} -> {head_version}")
    return Result(failures, notes, len(shipped))


def main(argv):
    if len(argv) != 2:
        print("usage: check-version-bump.py <base-ref>", file=sys.stderr)
        return 2
    root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    ).stdout.strip()
    if not root:
        print("not inside a git repository", file=sys.stderr)
        return 2

    # The root comes from the working directory, not from this file's location, so name
    # it: run by path from elsewhere, the guard answers about the repo you are standing
    # in, and a verdict about the wrong tree is the failure this script exists to prevent.
    print(f"repo: {root}")
    result = check(root, argv[1])
    for note in result.notes:
        print(note)
    for failure in result.failures:
        print(f"FAIL: {failure}")
    print(f"{len(result.failures)} failure(s), {result.checked} shipped file(s) checked")
    return 1 if result.failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
