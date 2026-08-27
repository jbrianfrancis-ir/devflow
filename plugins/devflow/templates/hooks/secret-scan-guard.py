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
import shlex
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

# Present for every file in a diff, text or binary — unlike `+++ `/`+` lines, which binary
# files never emit. Used only to track the current file; the credential-filename rule for
# binary content fires on BINARY_DIFFER_RE below, not on this header alone (a header alone
# also introduces a deleted/renamed file, which shouldn't trip the "content was added" rule).
DIFF_GIT_HEADER_RE = re.compile(r"^diff --git a/.* b/(.*)$")

# "Binary files <old> and <new> differ" — <new> is /dev/null for a pure deletion (nothing
# added, must not trip the credential-filename rule) and the real path otherwise (a binary
# file being added or modified, which is exactly the case `+++ `/`+` lines can't catch).
BINARY_DIFFER_RE = re.compile(r"^Binary files (.+) and (.+) differ$")

# Tokens that mean "stage everything", not a specific path — seen after `git add`.
GIT_ADD_ALL_TOKENS = {".", "-A", "--all", "-u", "--update"}


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


def scan(diff_text):
    """Return (file, pattern_class) for the first hit, or None if the diff is clean."""
    current_file = None
    for line in diff_text.splitlines():
        header = DIFF_GIT_HEADER_RE.match(line)
        if header:
            current_file = header.group(1)
            continue
        binary = BINARY_DIFFER_RE.match(line)
        if binary:
            new_side = binary.group(2)
            if new_side != "/dev/null" and current_file and is_credential_file(current_file):
                return current_file, "credential-shaped filename"
            continue
        if line.startswith("+++ "):
            path = line[4:].strip()
            if path != "/dev/null":
                current_file = re.sub(r"^b/", "", path)
            continue
        if not line.startswith("+"):
            continue
        content = line[1:]
        if current_file and is_credential_file(current_file):
            return current_file, "credential-shaped filename"
        if SECRET_RE.search(content):
            return current_file or "<unknown file>", "secret pattern"
    return None


def added_paths(command):
    """Paths passed to `git add` in this same chained Bash command, or None if `git add`
    targets everything (`.`, `-A`, `--all`, `-u`) or the command can't be tokenized safely —
    both mean the caller should treat every untracked file as a candidate, not just named ones."""
    paths = []
    for statement in re.split(r"&&|\|\||;", command):
        try:
            tokens = shlex.split(statement)
        except ValueError:
            return None
        if len(tokens) >= 2 and tokens[0] == "git" and tokens[1] == "add":
            args = tokens[2:]
            if not args or GIT_ADD_ALL_TOKENS & set(args):
                return None
            paths.extend(a for a in args if not a.startswith("-"))
    return paths


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
    """Hit for a not-yet-tracked file this exact chained command is about to stage and
    commit in one Bash call (`git add newfile && git commit ...`) — a diff against HEAD or
    the index can never see this, since the file has no history to diff against yet."""
    if "git add" not in command:
        return None
    targets = added_paths(command)
    try:
        untracked = set(untracked_files(cwd))
    except Exception as exc:
        warn(f"could not list untracked files in {cwd}: {exc}")
        return None
    candidates = untracked if targets is None else {t for t in targets if t in untracked}
    for rel_path in sorted(candidates):
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
