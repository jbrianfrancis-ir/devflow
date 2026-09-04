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

SHIPPED_PREFIX = "plugins/devflow/"
MANIFEST = "plugins/devflow/.claude-plugin/plugin.json"
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def git(root, *args):
    """Run git in `root`, returning (ok, stdout). Never raises on a git failure —
    the caller decides whether an unresolvable ref is fatal."""
    proc = subprocess.run(
        ["git", "-C", root, *args], capture_output=True, text=True
    )
    return proc.returncode == 0, proc.stdout


def changed_files(root, base_ref):
    """Paths changed on HEAD since it diverged from base_ref, or None if the ref
    does not resolve. Three-dot: the PR's own changes, not the base's."""
    ok, out = git(root, "diff", "--name-only", f"{base_ref}...HEAD")
    if not ok:
        return None
    return [line for line in out.splitlines() if line]


def version_at(root, ref):
    """The manifest's version at `ref`, or None when the manifest does not exist
    there — a plugin added by this diff has no earlier version to advance."""
    ok, out = git(root, "show", f"{ref}:{MANIFEST}")
    if not ok:
        return None
    try:
        return json.loads(out).get("version")
    except json.JSONDecodeError:
        return None


def version_on_disk(root):
    """The working tree's version, so this also answers before the bump is committed."""
    path = os.path.join(root, MANIFEST)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as stream:
        try:
            return json.load(stream).get("version")
        except json.JSONDecodeError:
            return None


def check(root, base_ref):
    """Returns (failures, notes). Empty failures means the diff is clear to merge."""
    failures, notes = [], []

    changed = changed_files(root, base_ref)
    if changed is None:
        # Fail closed: a comparison that did not run is never a clean one.
        return ([f"could not resolve base ref '{base_ref}' — the check did not run"], notes)

    shipped = sorted(p for p in changed if p.startswith(SHIPPED_PREFIX))
    if not shipped:
        notes.append("no shipped content changed — no bump required")
        return (failures, notes)

    head_version = version_on_disk(root)
    if head_version is None:
        return ([f"{MANIFEST} is missing or unreadable — cannot verify the version"], notes)

    base_version = version_at(root, base_ref)
    if base_version is None:
        notes.append(f"no manifest at {base_ref} — treating {head_version} as the first version")
        return (failures, notes)

    if head_version == base_version:
        sample = ", ".join(shipped[:3]) + (f", +{len(shipped) - 3} more" if len(shipped) > 3 else "")
        failures.append(
            f"{len(shipped)} shipped file(s) changed but the version is still {head_version} "
            f"— bump {MANIFEST} (and the Codex manifest and marketplace entry with it): {sample}"
        )
        return (failures, notes)

    head_parts, base_parts = SEMVER_RE.match(head_version), SEMVER_RE.match(base_version)
    if head_parts and base_parts:
        if tuple(map(int, head_parts.groups())) <= tuple(map(int, base_parts.groups())):
            failures.append(
                f"version moves backwards: {base_version} -> {head_version}"
            )
    else:
        notes.append(
            f"version changed {base_version} -> {head_version}; ordering unverified "
            "(not a plain X.Y.Z on one side)"
        )

    notes.append(f"{len(shipped)} shipped file(s) changed, version {base_version} -> {head_version}")
    return (failures, notes)


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

    failures, notes = check(root, argv[1])
    for note in notes:
        print(note)
    for failure in failures:
        print(f"FAIL: {failure}")
    print(f"{len(failures)} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
