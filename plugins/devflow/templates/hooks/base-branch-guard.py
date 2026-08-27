#!/usr/bin/env python3
"""PreToolUse (Bash) guard: block `git commit`/`git push` run directly on the project's base
branch, hardening conventions.md's "never commit to the base branch" rule so it holds even if
an agent ignores its written instructions.

This is a best-effort backstop layered on top of the still-primary agent-instruction control,
not the sole safety net — so on any internal error (no git repo, unreadable config, git call
fails) it fails open (exit 0) with a clear warning on stderr, never a silent pass.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hook_common as common  # noqa: E402


def warn(message):
    print(f"base-branch-guard: {message}", file=sys.stderr)


def current_branch(cwd):
    result = subprocess.run(
        ["git", "-C", cwd, "branch", "--show-current"],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git branch --show-current failed")
    return result.stdout.strip()


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

    try:
        branch = current_branch(cwd)
    except Exception as exc:
        warn(f"could not determine current branch in {cwd}: {exc}")
        return 0

    if not branch:
        warn(f"could not determine current branch in {cwd} (detached HEAD?)")
        return 0

    configured = common.read_configured_base(cwd, warn)
    base_hit = configured if configured else (branch if branch in common.FALLBACK_BASES else None)

    if configured is not None:
        matched = branch == configured
    else:
        matched = branch in common.FALLBACK_BASES

    if matched:
        print(
            f"Blocked: direct commit/push to base branch '{base_hit}' — use a flow/<slug> "
            "feature branch.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail open, loud — never a silent pass
        warn(f"unexpected error: {exc}")
        sys.exit(0)
