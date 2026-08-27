"""Shared helpers for DevFlow's guard hooks in this directory.

Copied alongside base-branch-guard.py and secret-scan-guard.py by the flow-hooks skill
whenever either is installed — protected-paths-guard.py has no git-resolution logic and
does not need this module. Kept as a single small file (not a package) so it copies as
one extra file, not a directory.
"""
import json
import os
import re
import subprocess

FALLBACK_BASES = ("main", "master")
GIT_COMMIT_OR_PUSH_RE = re.compile(r"\bgit\s+(commit|push)\b")


def matches_git_commit_or_push(command):
    return bool(GIT_COMMIT_OR_PUSH_RE.search(command))


def read_configured_base(cwd, warn):
    """The project's declared base branch from .planning/config.json's git.base, or None
    if unset/missing/unreadable (the caller decides the fallback)."""
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


def resolve_diff_base(cwd, warn):
    """A base ref safe to diff against: the configured git.base if it resolves, else the
    first of FALLBACK_BASES that exists as a ref in this repo. None if nothing resolves —
    the caller fails open on None, since diffing against a nonexistent ref only errors."""
    configured = read_configured_base(cwd, warn)
    candidates = [configured] if configured else list(FALLBACK_BASES)
    for candidate in candidates:
        result = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--verify", "--quiet", candidate],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return candidate
    warn(f"could not resolve a base branch among {candidates}")
    return None
