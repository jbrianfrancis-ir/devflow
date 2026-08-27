#!/usr/bin/env python3
"""PreToolUse (Bash) guard: block a `git commit`/`git push` whose diff contains an added line
matching conventions.md's secret-pattern class, hardening the "secret scan every commit and
push" hard rule so it holds even if an agent ignores its written instructions.

This is a best-effort backstop layered on top of the still-primary agent-instruction control,
not the sole safety net — so on any internal error (no git repo, unreadable config, git call
fails) it fails open (exit 0) with a clear warning on stderr, never a silent pass. Only a human
clears a real hit; this script never does more than block and name the pattern class.
"""
import fnmatch
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hook_common as common  # noqa: E402

# Kept byte-identical to the pattern in conventions.md's "Secret scan (fail-closed)" section —
# tests/test_flow_hooks.py asserts this constant matches that file's fenced pattern, so the two
# copies cannot drift silently.
SECRET_PATTERN = r"""-----BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|eyJhbGciOi[A-Za-z0-9_-]{20,}|(password|passwd|secret|token|api[_-]?key|connection[_-]?string)["' ]*[=:] *["'][^"']{8,}["']|(password|passwd|secret|token|api[_-]?key|connection[_-]?string)["' ]*[=:] *[A-Za-z0-9+/=_-]{16,} *$"""

SECRET_RE = re.compile(SECRET_PATTERN)

# Any added line in one of these is a hit regardless of content (except the two named exceptions).
CREDENTIAL_FILE_GLOBS = (".env*", "*.pem", "*.pfx", "*.key", "id_rsa*")
CREDENTIAL_FILE_EXCEPTIONS = {".env.example", ".env.template"}

# Splits a `git diff` into per-file sections — the delimiter git emits for every file in a
# diff, text or binary, added, modified, renamed, or deleted.
DIFF_GIT_HEADER_RE = re.compile(r"^diff --git a/.* b/(.*)$")

# Git always emits this line for a deletion (text or binary) — used to tell "this file's
# content is going away" apart from "this file's content is arriving", so a credential-shaped
# file's deletion (remediation) never trips the same rule that catches its arrival.
DELETED_FILE_RE = re.compile(r"^deleted file mode\b")

GIT_ADD_RE = re.compile(r"\bgit\s+add\b")


def warn(message):
    print(f"secret-scan-guard: {message}", file=sys.stderr)


def is_credential_file(path):
    name = os.path.basename(path)
    if name in CREDENTIAL_FILE_EXCEPTIONS:
        return False
    return any(fnmatch.fnmatch(name, pattern) for pattern in CREDENTIAL_FILE_GLOBS)


def diff_for(command, cwd, warn):
    if re.search(r"\bgit\s+commit\b", command):
        # `git diff HEAD` (working tree vs HEAD) covers staged AND unstaged changes to
        # tracked files in one shot — unlike `--cached` alone, it still sees what `git
        # commit -a`/`-am`/`--all` would commit even though nothing is staged yet.
        result = subprocess.run(
            ["git", "-C", cwd, "diff", "HEAD", "-U0"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            # No HEAD yet (first commit in the repo) — HEAD doesn't exist, fall back to
            # the index-vs-empty-tree diff, which works with zero commits.
            result = subprocess.run(
                ["git", "-C", cwd, "diff", "--cached", "-U0"],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "git diff failed")
        return result.stdout
    if re.search(r"\bgit\s+push\b", command):
        base = common.resolve_diff_base(cwd, warn)
        if base is None:
            return None
        result = subprocess.run(
            ["git", "-C", cwd, "diff", f"{base}...HEAD", "-U0"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "git diff failed")
        return result.stdout
    return None


def iter_file_chunks(diff_text):
    """Yield (file_path, chunk_lines) per file section of a `git diff` — everything from one
    `diff --git` header up to (not including) the next, or EOF. One pass over line-tracking
    state, so the per-file rules below don't have to reconstruct it themselves."""
    chunk_path = None
    chunk_lines = []
    for line in diff_text.splitlines():
        header = DIFF_GIT_HEADER_RE.match(line)
        if header:
            if chunk_path is not None:
                yield chunk_path, chunk_lines
            chunk_path = header.group(1)
            chunk_lines = []
            continue
        chunk_lines.append(line)
    if chunk_path is not None:
        yield chunk_path, chunk_lines


def scan(diff_text):
    """Return (file, pattern_class) for the first hit, or None if the diff is clean.

    The credential-filename rule ("any added line in one of these is a hit regardless of
    content") is evaluated per file, not per line: a credential-shaped file being added or
    modified is a hit even with zero `+`/`+++` lines to inspect (a binary file, or a newly
    added empty one) — but a credential-shaped file being *deleted* is remediation, not a
    hit, regardless of how its removal happens to render in the diff.
    """
    for file_path, lines in iter_file_chunks(diff_text):
        is_deletion = any(DELETED_FILE_RE.match(line) for line in lines)
        if not is_deletion and is_credential_file(file_path):
            return file_path, "credential-shaped filename"
        for line in lines:
            if not line.startswith("+") or line.startswith("+++"):
                continue
            if SECRET_RE.search(line[1:]):
                return file_path, "secret pattern"
    return None


def untracked_files(cwd):
    result = subprocess.run(
        ["git", "-C", cwd, "ls-files", "--others", "--exclude-standard"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git ls-files failed")
    return [line for line in result.stdout.splitlines() if line]


def scan_untracked_candidate(cwd, rel_path):
    if is_credential_file(rel_path):
        return rel_path, "credential-shaped filename"
    try:
        with open(os.path.join(cwd, rel_path), "rb") as stream:
            data = stream.read(1_000_000)  # cap — a secret worth catching is near the top
    except OSError:
        return None
    if b"\x00" in data:
        return None  # binary content with no credential-shaped name; nothing safe to regex
    for line in data.decode("utf-8", errors="ignore").splitlines():
        if SECRET_RE.search(line):
            return rel_path, "secret pattern"
    return None


def scan_new_untracked_files(command, cwd, warn):
    """Hit for a not-yet-tracked file this exact chained command might stage and commit in
    one Bash call (`git add newfile && git commit ...`) — a diff against HEAD or the index
    can never see this, since the file has no history to diff against yet.

    Deliberately conservative: rather than compute exactly which untracked files a `git add`
    invocation would stage — defeated, verified live, by a glob (`git add *.pem`), a shell
    variable (`git add $F`), `-C`/an env-var prefix, or the add and commit landing in separate
    newline-separated statements of the same command — scan every currently untracked file
    whenever the command contains `git add` at all. A false positive (flagging an untracked
    file this particular add wouldn't actually stage) costs less than the bypass a narrower,
    cleverer match kept reopening.
    """
    if not GIT_ADD_RE.search(command):
        return None
    try:
        untracked = untracked_files(cwd)
    except Exception as exc:
        warn(f"could not list untracked files in {cwd}: {exc}")
        return None
    for rel_path in sorted(untracked):
        hit = scan_untracked_candidate(cwd, rel_path)
        if hit:
            return hit
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as exc:
        warn(f"could not parse stdin JSON: {exc}")
        return 0

    command = (payload.get("tool_input") or {}).get("command") or ""
    if not common.matches_git_commit_or_push(command):
        return 0

    cwd = payload.get("cwd") or os.getcwd()

    hit = None
    if re.search(r"\bgit\s+commit\b", command):
        try:
            hit = scan_new_untracked_files(command, cwd, warn)
        except Exception as exc:
            warn(f"could not scan untracked files in {cwd}: {exc}")
            hit = None

    if hit is None:
        try:
            diff_text = diff_for(command, cwd, warn)
        except Exception as exc:
            warn(f"could not compute diff in {cwd}: {exc}")
            return 0

        if diff_text is None:
            return 0

        hit = scan(diff_text)

    if hit is None:
        return 0

    file_name, pattern_class = hit
    print(
        f"Blocked: possible secret in {file_name} (pattern: {pattern_class}) — "
        "remove/rotate before committing.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail open, loud — never a silent pass
        warn(f"unexpected error: {exc}")
        sys.exit(0)
