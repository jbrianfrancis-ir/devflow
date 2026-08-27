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

# Kept byte-identical to the pattern in conventions.md's "Secret scan (fail-closed)" section —
# tests/test_flow_hooks.py asserts this constant matches that file's fenced pattern, so the two
# copies cannot drift silently.
SECRET_PATTERN = r"""-----BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|eyJhbGciOi[A-Za-z0-9_-]{20,}|(password|passwd|secret|token|api[_-]?key|connection[_-]?string)["' ]*[=:] *["'][^"']{8,}["']|(password|passwd|secret|token|api[_-]?key|connection[_-]?string)["' ]*[=:] *[A-Za-z0-9+/=_-]{16,} *$"""

SECRET_RE = re.compile(SECRET_PATTERN)

# Any added line in one of these is a hit regardless of content (except the two named exceptions).
CREDENTIAL_FILE_GLOBS = (".env*", "*.pem", "*.pfx", "*.key", "id_rsa*")
CREDENTIAL_FILE_EXCEPTIONS = {".env.example", ".env.template"}


def warn(message):
    print(f"secret-scan-guard: {message}", file=sys.stderr)


def is_credential_file(path):
    name = os.path.basename(path)
    if name in CREDENTIAL_FILE_EXCEPTIONS:
        return False
    return any(fnmatch.fnmatch(name, pattern) for pattern in CREDENTIAL_FILE_GLOBS)


def read_base(cwd):
    config_path = os.path.join(cwd, ".planning", "config.json")
    try:
        with open(config_path, encoding="utf-8") as stream:
            config = json.load(stream)
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as exc:
        warn(f"could not read {config_path}: {exc}")
        return None
    base = (config.get("git") or {}).get("base")
    return base or None


def diff_for(command, cwd):
    if re.search(r"\bgit\s+commit\b", command):
        args = ["git", "-C", cwd, "diff", "--cached", "-U0"]
    elif re.search(r"\bgit\s+push\b", command):
        base = read_base(cwd) or "main"
        args = ["git", "-C", cwd, "diff", f"{base}...HEAD", "-U0"]
    else:
        return None
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"{' '.join(args)} failed")
    return result.stdout


def scan(diff_text):
    """Return (file, pattern_class) for the first hit, or None if the diff is clean."""
    current_file = None
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            path = line[4:].strip()
            current_file = None if path == "/dev/null" else re.sub(r"^b/", "", path)
            continue
        if not line.startswith("+"):
            continue
        content = line[1:]
        if current_file and is_credential_file(current_file):
            return current_file, "credential-shaped filename"
        if SECRET_RE.search(content):
            return current_file or "<unknown file>", "secret pattern"
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as exc:
        warn(f"could not parse stdin JSON: {exc}")
        return 0

    command = (payload.get("tool_input") or {}).get("command") or ""
    if not re.search(r"\bgit\s+(commit|push)\b", command):
        return 0

    cwd = payload.get("cwd") or os.getcwd()

    try:
        diff_text = diff_for(command, cwd)
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
