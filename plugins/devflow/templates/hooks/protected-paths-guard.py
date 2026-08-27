#!/usr/bin/env python3
"""PreToolUse (Edit|Write) guard: block an edit to a path listed in `.planning/config.json`'s
`protected_paths` unless a human has set DEVFLOW_PROTECTED_PATH_OK, hardening the class of hard
rules that says "this path needs a human before it changes" so it holds even if an agent ignores
its written instructions.

This is a best-effort backstop layered on top of the still-primary agent-instruction control,
not the sole safety net — so on any internal error (unreadable config) it fails open (exit 0)
with a clear warning on stderr, never a silent pass.
"""
import fnmatch
import json
import os
import sys


def warn(message):
    print(f"protected-paths-guard: {message}", file=sys.stderr)


def read_protected_paths(cwd):
    config_path = os.path.join(cwd, ".planning", "config.json")
    try:
        with open(config_path, encoding="utf-8") as stream:
            config = json.load(stream)
    except FileNotFoundError:
        return []
    except (OSError, json.JSONDecodeError) as exc:
        warn(f"could not read {config_path}: {exc}")
        return []
    paths = config.get("protected_paths")
    return paths if isinstance(paths, list) else []


def matching_glob(path, relative, patterns):
    # Normalize first: an un-normalized path (`sub/../secret`, `./secret`) can match the
    # literal file on disk while evading a glob written against its canonical form.
    norm_path = os.path.normpath(path)
    norm_relative = os.path.normpath(relative)
    for pattern in patterns:
        if fnmatch.fnmatch(norm_path, pattern) or fnmatch.fnmatch(norm_relative, pattern):
            return pattern
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as exc:
        warn(f"could not parse stdin JSON: {exc}")
        return 0

    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path")
    if not file_path:
        return 0

    cwd = payload.get("cwd") or os.getcwd()
    protected = read_protected_paths(cwd)
    if not protected:
        return 0

    relative = file_path
    if os.path.isabs(file_path):
        try:
            relative = os.path.relpath(file_path, cwd)
        except ValueError:
            relative = file_path

    pattern = matching_glob(file_path, relative, protected)
    if pattern is None:
        return 0

    if os.environ.get("DEVFLOW_PROTECTED_PATH_OK"):
        return 0

    print(
        f"Blocked: {file_path} is a protected path ({pattern}) — set "
        "DEVFLOW_PROTECTED_PATH_OK=1 after human review to proceed.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail open, loud — never a silent pass
        warn(f"unexpected error: {exc}")
        sys.exit(0)
