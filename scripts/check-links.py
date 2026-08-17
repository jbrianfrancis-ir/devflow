#!/usr/bin/env python3
"""Validate internal references across this repo's tracked markdown.

Checks three reference kinds: `[text](target)` links and `#anchor` fragments
(GitHub heading-slug rules), backticked repo-relative paths, and
`{devflow_root}/...` references (resolved to `plugins/devflow/...`).

Stdlib only — no network, no third-party import.
"""

import os
import re
import subprocess
import sys
from typing import NamedTuple

EXCLUDE_PREFIXES = ("plugins/devflow/templates/", ".planning/")
DEVFLOW_ROOT_PREFIX = "{devflow_root}/"
DEVFLOW_ROOT_TARGET = "plugins/devflow/"

LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
BACKTICK_RE = re.compile(r"`([^`]+)`")
BACKTICK_EXT_RE = re.compile(r"\.(md|py|json|yml)$")
PLACEHOLDER_SEGMENT_RE = re.compile(r"^(NNN|NN|MM|YYYY)(?![A-Za-z0-9])")
FAMILY_CHARS_RE = re.compile(r"[*<>{},|]")


class Failure(NamedTuple):
    file: str
    line: int
    target: str
    reason: str


def check(root):
    """Enumerate the markdown under `root` and return the list of failures.

    Prints nothing and reads no file until called — importing this module
    must have no side effect.
    """
    root = os.path.abspath(root)
    all_files = _all_tracked(root)
    md_files = [f for f in all_files if f.endswith(".md") and not f.startswith(EXCLUDE_PREFIXES)]

    failures = []
    heading_cache = {}
    for relfile in md_files:
        failures.extend(_check_file(root, relfile, all_files, heading_cache))
    failures.sort(key=lambda f: (f.file, f.line))
    return failures


def main(argv=None):
    try:
        root = _repo_root()
        failures = check(root)
    except Exception as exc:  # fail-closed: "could not check" is never silently clean
        print(f"could not check: {exc}")
        return 1
    for failure in failures:
        print(f"{failure.file}:{failure.line}: {failure.target} — {failure.reason}")
    print(f"{len(failures)} failure(s)" if failures else "0 failures")
    return 1 if failures else 0


# --- repo enumeration -------------------------------------------------------

def _repo_root():
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"not inside a git repository: {result.stderr.strip()}")
    return result.stdout.strip()


def _all_tracked(root):
    result = subprocess.run(
        ["git", "-C", root, "ls-files"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"git ls-files failed: {result.stderr.strip()}")
    return [f for f in result.stdout.splitlines() if f]


# --- per-file scan -----------------------------------------------------------

def _check_file(root, relfile, all_files, heading_cache):
    path = os.path.join(root, relfile)
    try:
        with open(path, encoding="utf-8") as stream:
            lines = stream.read().splitlines()
    except OSError as exc:
        return [Failure(relfile, 0, relfile, f"could not read file: {exc}")]

    fence_mask = _code_fence_mask(lines)
    failures = []
    for lineno, line in enumerate(lines, start=1):
        if fence_mask[lineno - 1]:
            continue
        for match in LINK_RE.finditer(line):
            target = _parse_link_target(match.group(2))
            failure = _check_reference(
                root, relfile, lineno, target, all_files, heading_cache, is_link=True
            )
            if failure:
                failures.append(failure)
        for match in BACKTICK_RE.finditer(line):
            token = match.group(1)
            if "/" not in token or not BACKTICK_EXT_RE.search(token):
                continue
            failure = _check_reference(
                root, relfile, lineno, token, all_files, heading_cache, is_link=False
            )
            if failure:
                failures.append(failure)
    return failures


def _parse_link_target(raw):
    raw = raw.strip()
    if raw.startswith("<"):
        end = raw.find(">")
        if end != -1:
            return raw[1:end]
    match = re.match(r"^(\S+)(?:\s+[\"'].*[\"'])?$", raw)
    if match:
        return match.group(1)
    parts = raw.split()
    return parts[0] if parts else raw


def _check_reference(root, relfile, lineno, target, all_files, heading_cache, is_link):
    if is_link and target.startswith(("http://", "https://", "mailto:")):
        return None

    if target.startswith(DEVFLOW_ROOT_PREFIX):
        target = DEVFLOW_ROOT_TARGET + target[len(DEVFLOW_ROOT_PREFIX):]

    if "#" in target:
        path_part, _, frag = target.partition("#")
    else:
        path_part, frag = target, None

    if path_part == "":
        # Bare #frag — check the current file's own headings.
        return _check_anchor(root, relfile, lineno, target, relfile, frag, heading_cache)

    if _skip(path_part, relfile, root, all_files):
        return None

    resolved = _resolve(root, relfile, path_part)
    if resolved is None:
        return Failure(relfile, lineno, target, "target does not exist")

    if frag is not None:
        return _check_anchor(
            root, relfile, lineno, target, path_part, frag, heading_cache, resolved
        )
    return None


# --- skip rules (R1-R5) -------------------------------------------------------

def _skip(token, relfile, root, all_files):
    if re.search(r"\s", token):
        return True  # R1: contains whitespace — a command, not a path
    if FAMILY_CHARS_RE.search(token):
        return True  # R2: family/placeholder punctuation survives the rewrite
    for segment in token.split("/"):
        if PLACEHOLDER_SEGMENT_RE.match(segment):
            return True  # R3: NN/NNN/MM/YYYY placeholder segment
    if token.startswith(".planning/") or token.startswith("~/"):
        return True  # R4: out-of-scope tree or home-relative
    if _r5_skip(token, relfile, all_files):
        return True  # R5: first segment names nothing under any resolution base
    return False


def _bases_for(relfile):
    bases = [""]
    own_dir = os.path.dirname(relfile)
    if own_dir:
        bases.append(own_dir)
    if relfile == DEVFLOW_ROOT_TARGET.rstrip("/") or relfile.startswith(DEVFLOW_ROOT_TARGET):
        if DEVFLOW_ROOT_TARGET.rstrip("/") not in bases:
            bases.append(DEVFLOW_ROOT_TARGET.rstrip("/"))
    ordered = []
    for base in bases:
        if base not in ordered:
            ordered.append(base)
    return ordered


def _top_level_entries(base, all_files):
    prefix = f"{base}/" if base else ""
    entries = set()
    for f in all_files:
        if base:
            if not f.startswith(prefix):
                continue
            rest = f[len(prefix):]
        else:
            rest = f
        if rest:
            entries.add(rest.split("/", 1)[0])
    return entries


def _r5_skip(token, relfile, all_files):
    first = token.split("/", 1)[0]
    if first in (".", ".."):
        return False
    for base in _bases_for(relfile):
        if first in _top_level_entries(base, all_files):
            return False
    return True


def _resolve(root, relfile, path_part):
    for base in _bases_for(relfile):
        candidate = os.path.normpath(os.path.join(root, base, path_part))
        if os.path.isfile(candidate):
            return candidate
    return None


# --- anchors -------------------------------------------------------------------

def _check_anchor(root, relfile, lineno, display_target, target_relpath, frag,
                   heading_cache, resolved_abs=None):
    if resolved_abs is None:
        resolved_abs = os.path.join(root, target_relpath)
    slug = _slugify(frag)
    if resolved_abs not in heading_cache:
        try:
            with open(resolved_abs, encoding="utf-8") as stream:
                text = stream.read()
            heading_cache[resolved_abs] = _heading_slugs(text)
        except OSError:
            heading_cache[resolved_abs] = set()
    if slug not in heading_cache[resolved_abs]:
        return Failure(relfile, lineno, display_target, f"no such heading #{frag}")
    return None


def _code_fence_mask(lines):
    mask = [False] * len(lines)
    fence_char = None
    fence_len = 0
    in_fence = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if in_fence:
            mask[i] = True
            if re.match(rf"^{re.escape(fence_char)}{{{fence_len},}}\s*$", stripped):
                in_fence = False
            continue
        match = re.match(r"^(`{3,}|~{3,})", stripped)
        if match:
            fence_char = stripped[0]
            fence_len = len(match.group(1))
            in_fence = True
            mask[i] = True
    return mask


def _frontmatter_mask(lines):
    mask = [False] * len(lines)
    if lines and lines[0].strip() == "---":
        mask[0] = True
        for i in range(1, len(lines)):
            mask[i] = True
            if lines[i].strip() == "---":
                break
    return mask


def _heading_slugs(text):
    lines = text.splitlines()
    fence_mask = _code_fence_mask(lines)
    front_mask = _frontmatter_mask(lines)
    counts = {}
    slugs = set()
    i = 0
    n = len(lines)
    while i < n:
        if fence_mask[i] or front_mask[i]:
            i += 1
            continue
        line = lines[i]
        heading_text = None
        consumed = 1
        atx = re.match(r"^(#{1,6})(?:\s+(.*))?$", line)
        if atx:
            heading_text = (atx.group(2) or "").strip()
            heading_text = re.sub(r"\s+#+\s*$", "", heading_text)
        elif (
            i + 1 < n
            and not fence_mask[i + 1]
            and not front_mask[i + 1]
            and line.strip()
            and not re.match(r"^[-*+]\s|^\d+[.)]\s|^#", line.strip())
        ):
            nxt = lines[i + 1].strip()
            if re.match(r"^=+$", nxt) or re.match(r"^-+$", nxt):
                heading_text = line.strip()
                consumed = 2
        if heading_text is not None:
            slug = _slugify(heading_text)
            count = counts.get(slug, 0)
            counts[slug] = count + 1
            slugs.add(slug if count == 0 else f"{slug}-{count}")
        i += consumed
    return slugs


def _strip_inline_markdown(text):
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"`+([^`]*)`+", r"\1", text)
    text = re.sub(r"(\*\*\*|\*\*|\*|___|__|_|~~)", "", text)
    return text


def _slugify(text):
    text = _strip_inline_markdown(text).strip().lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text


if __name__ == "__main__":
    sys.exit(main())
