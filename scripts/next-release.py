#!/usr/bin/env python3
"""Compute the next DevFlow release from git tags and `changes/*.md` fragments.

Nothing is committed: the version lives only in the `vX.Y.Z` tag that release.yml creates
on push to main. next = the highest `vX.Y.Z` tag merged into HEAD (BASELINE when there is
none), bumped by the highest `bump:` among fragments ADDED since that tag; the notes are
those fragments' bullets. No fragment added since the tag means nothing to release.
Fragments are never deleted; they stay in the tree as history (docs/releasing.md).

  next-release.py                    preview: "<base> -> <version>" and the notes
  next-release.py --notes-file PATH  release.yml: print only the version (nothing when
                                     there is nothing to release) and write notes to PATH

Exit 1 on a malformed fragment or a git failure. Stdlib only.
"""

import argparse
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "check_change_fragment", Path(__file__).with_name("check-change-fragment.py"))
_CHECK = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CHECK)

BASELINE = "0.57.0"  # the last version committed to the manifests, before tags were the record
ORDER = ("patch", "minor", "major")
TAG_RE = re.compile(r"v(\d+)\.(\d+)\.(\d+)")


def _git(root, *args):
    proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def bumped(version, bump):
    major, minor, patch = map(int, version.split("."))
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def plan(root):
    """(tag or None, base version, next version or None, notes). Raises ValueError on a bad fragment."""
    tags = [t for t in _git(root, "tag", "--merged", "HEAD", "--list", "v*").split() if TAG_RE.fullmatch(t)]
    tag = max(tags, key=lambda t: tuple(map(int, TAG_RE.fullmatch(t).groups())), default=None)
    if tag:
        # --no-renames: a fragment counts when its path is new since the tag.
        listed = _git(root, "diff", "-z", "--no-renames", "--diff-filter=A", "--name-only",
                      f"{tag}..HEAD", "--", "changes/")
    else:
        listed = _git(root, "ls-files", "-z", "--", "changes/")
    paths = sorted(p for p in listed.split("\0") if _CHECK.FRAGMENT_RE.match(p))
    base = tag[1:] if tag else BASELINE
    if not paths:
        return tag, base, None, ""
    parsed = []
    for path in paths:
        try:
            parsed.append(_CHECK.parse_fragment(_git(root, "show", f"HEAD:{path}")))
        except ValueError as error:
            raise ValueError(f"{path} {error}")
    bump = max((b for b, _ in parsed), key=ORDER.index)
    return tag, base, bumped(base, bump), "\n".join(bullet for _, bullet in parsed) + "\n"


def main(argv):
    parser = argparse.ArgumentParser(description="Compute the next release from tags and changes/ fragments.")
    parser.add_argument("--notes-file", type=Path,
                        help="write the notes here and print only the version (release.yml)")
    args = parser.parse_args(argv)
    try:
        root = _git(".", "rev-parse", "--show-toplevel").strip()
        tag, base, version, notes = plan(root)
    except (RuntimeError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    if args.notes_file:
        if version:
            args.notes_file.write_text(notes, encoding="utf-8")
            print(version)
        return 0
    since = tag or f"baseline {BASELINE} (no vX.Y.Z tag)"
    if version is None:
        print(f"no fragments added since {since} — nothing to release")
    else:
        print(f"{base} -> {version} (since {since})\n\n{notes}", end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
