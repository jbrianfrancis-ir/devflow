#!/usr/bin/env python3
"""Cut a release from the `changes/*.md` fragments.

Reads every fragment, takes the highest `bump:` against plugin.json's current version,
writes the next version to the three manifests, prepends one `## X.Y.Z (YYYY-MM-DD)`
CHANGELOG entry built from the fragment bullets, and deletes the fragments. Commit the
result on a `release/X.Y.Z` branch and open a PR; release.yml tags it once merged
(docs/releasing.md). `--dry-run` prints the result and writes nothing. Stdlib only.
"""

import argparse
import datetime
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "check_change_fragment", Path(__file__).with_name("check-change-fragment.py"))
_CHECK = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CHECK)

ORDER = ("patch", "minor", "major")


def next_version(current, bump):
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", current)
    if not match:
        raise ValueError(f"current version '{current}' is not X.Y.Z")
    major, minor, patch = map(int, match.groups())
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def cut(root, today, dry_run):
    """Returns (current, version, entry, fragments). Raises ValueError before writing anything."""
    root = Path(root)
    fragments = sorted(p for p in (root / "changes").glob("*.md") if _CHECK.FRAGMENT_RE.match(p.relative_to(root).as_posix()))
    if not fragments:
        raise ValueError("no changes/*.md fragments to release")
    parsed = []
    for path in fragments:
        try:
            parsed.append(_CHECK.parse_fragment(path.read_text(encoding="utf-8")))
        except ValueError as error:
            raise ValueError(f"{path.relative_to(root)} {error}")
    current = json.loads((root / _CHECK.MANIFEST).read_text(encoding="utf-8"))["version"]
    version = next_version(current, max((bump for bump, _ in parsed), key=ORDER.index))
    entry = f"## {version} ({today})\n" + "\n".join(bullet for _, bullet in parsed) + "\n"

    old_line = f'"version": "{current}"'
    manifests = {}
    for rel in _CHECK.MANIFESTS:
        text = (root / rel).read_text(encoding="utf-8")
        if text.count(old_line) != 1:
            raise ValueError(f"{rel} does not hold exactly one {old_line}")
        manifests[rel] = text.replace(old_line, f'"version": "{version}"')
    changelog = (root / _CHECK.CHANGELOG).read_text(encoding="utf-8")
    head, sep, rest = changelog.partition("\n## ")
    if not sep:
        raise ValueError(f"{_CHECK.CHANGELOG} has no '## ' entry to insert above")

    if not dry_run:
        for rel, text in manifests.items():
            (root / rel).write_text(text, encoding="utf-8")
        (root / _CHECK.CHANGELOG).write_text(f"{head}\n{entry}\n## {rest}", encoding="utf-8")
        for path in fragments:
            path.unlink()
    return current, version, entry, fragments


def main(argv):
    parser = argparse.ArgumentParser(description="Cut a release from changes/*.md fragments.")
    parser.add_argument("--dry-run", action="store_true", help="print the result, write nothing")
    args = parser.parse_args(argv)
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    if not root:
        print("not inside a git repository", file=sys.stderr)
        return 2
    try:
        current, version, entry, fragments = cut(root, datetime.date.today().isoformat(), args.dry_run)
    except ValueError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    verb = "would" if args.dry_run else "did"
    print(f"{current} -> {version} ({verb} write {', '.join(_CHECK.MANIFESTS)}, {_CHECK.CHANGELOG})")
    print(f"{verb} delete: {', '.join(str(p.relative_to(root)) for p in fragments)}\n")
    print(entry)
    if not args.dry_run:
        print(f"next: git switch -c release/{version} && git commit -am 'chore(release): {version}', then open a PR")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
