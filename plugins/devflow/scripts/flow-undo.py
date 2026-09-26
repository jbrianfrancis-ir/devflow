#!/usr/bin/env python3
"""Undo unpublished commits on a feature branch — the only undo authority /flow-undo uses.

Two subcommands, both printing one JSON object on stdout:

  preview --repo <root> --to <sha>
      What undoing to <sha> would remove, and either `apply` parameters or `blocked` reasons.
  apply --repo <root> --to <sha> --expected-head <sha>
      Refuses unless HEAD is still --expected-head and a fresh preview is unblocked. Then
      writes a backup ref at the old HEAD and moves the branch to <sha>.

Blocked (fail-closed — conventions.md → Fail-closed guards): the current branch is a base
branch (`main`, `dev`, or `git.base` in .planning/config.json) or HEAD is detached; the
working tree is not clean; <sha> is not a strict ancestor of HEAD; any commit being removed is
reachable from a remote-tracking ref (published) or is a merge; a `git fetch` that failed, so
publication could not be checked. A check that could not run blocks — it is never read as clean.

Never pushes, never force-pushes, never deletes a branch or a tag. Stdlib only.

Exit codes: 0 preview unblocked / apply done; 1 blocked or refused; 2 usage error.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys

ALWAYS_BASE = ("main", "dev")
BACKUP_PREFIX = "refs/devflow/undo/"
FETCH_TIMEOUT_S = 120


def git(repo, *args, timeout=None):
    """Run git; return (returncode, stdout, stderr). A git that cannot start is rc 127."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        out = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                             env=env, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)
    return out.returncode, out.stdout.strip(), out.stderr.strip()


def base_branches(root):
    """Return (set of base branch names, error or None). An unreadable config is an error,
    never a silent fall back to the defaults alone."""
    names = set(ALWAYS_BASE)
    path = os.path.join(root, ".planning", "config.json")
    if not os.path.exists(path):
        return names, None
    try:
        with open(path, encoding="utf-8") as stream:
            config = json.load(stream)
    except (OSError, ValueError) as exc:
        return names, f".planning/config.json unreadable: {exc}"
    base = (config.get("git") or {}).get("base") if isinstance(config, dict) else None
    if base is not None and not isinstance(base, str):
        return names, ".planning/config.json git.base is not a string"
    if base:
        names.add(base)
    return names, None


def preview(repo, to):
    result = {"repo": None, "branch": None, "head": None, "target": None, "commits": [],
              "remotes": [], "blocked": [], "apply": None}
    blocked = result["blocked"]

    def block(code, detail):
        blocked.append({"code": code, "detail": detail})

    rc, root, err = git(repo, "rev-parse", "--show-toplevel")
    if rc != 0:
        block("not-a-repo", err or f"{repo} is not a git work tree")
        return result
    result["repo"] = root

    rc, head, err = git(root, "rev-parse", "--verify", "HEAD")
    if rc != 0:
        block("no-head", err or "HEAD does not resolve")
        return result
    result["head"] = head

    rc, branch, _ = git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
    if rc != 0:
        block("detached-head", "HEAD is detached; undo works only on a checked-out branch")
    else:
        result["branch"] = branch
        bases, config_err = base_branches(root)
        if config_err:
            block("config-unreadable", config_err + " — cannot tell which branch is the base")
        if branch in bases:
            block("base-branch", f"'{branch}' is a base branch; undo never rewrites it")

    rc, status, err = git(root, "status", "--porcelain")
    if rc != 0:
        block("could-not-check", f"git status failed: {err}")
    elif status:
        block("dirty-tree", "working tree has uncommitted or untracked changes")

    rc, target, err = git(root, "rev-parse", "--verify", "--quiet", f"{to}^{{commit}}")
    if rc != 0:
        block("target-invalid", f"'{to}' does not name a commit")
        return result
    result["target"] = target
    if target == head:
        block("target-is-head", "target is HEAD; there is nothing to undo")
        return result
    rc, _, err = git(root, "merge-base", "--is-ancestor", target, head)
    if rc == 1:
        block("not-ancestor", f"{target} is not an ancestor of HEAD {head}")
        return result
    if rc != 0:
        block("could-not-check", f"ancestry check failed: {err}")
        return result

    rc, log, err = git(root, "log", "--format=%H%x09%P%x09%s", f"{target}..{head}")
    if rc != 0:
        block("could-not-check", f"git log failed: {err}")
        return result
    for line in log.splitlines():
        sha, parents, subject = line.split("\t", 2)
        result["commits"].append({"sha": sha, "subject": subject})
        if len(parents.split()) > 1:
            block("merge-commit", f"{sha} is a merge commit; undo never unwinds a merge")

    # Publication is the remote's fact. Refresh every remote first; a failed fetch leaves the
    # remote-tracking refs stale, so publication is unknown and the undo is blocked.
    rc, remotes, err = git(root, "remote")
    if rc != 0:
        block("could-not-check", f"git remote failed: {err}")
        return result
    result["remotes"] = remotes.split()
    fetched = True
    for remote in result["remotes"]:
        rc, _, err = git(root, "fetch", "--quiet", remote, timeout=FETCH_TIMEOUT_S)
        if rc != 0:
            fetched = False
            block("could-not-check",
                  f"git fetch {remote} failed ({err or 'no detail'}); publication is unknown")
    if fetched:
        for commit in result["commits"]:
            rc, refs, err = git(root, "for-each-ref", "--format=%(refname:short)",
                                "--contains", commit["sha"], "refs/remotes")
            if rc != 0:
                block("could-not-check", f"remote reachability check failed: {err}")
                break
            if refs:
                block("published", f"{commit['sha']} is reachable from "
                                   f"{', '.join(refs.split())}; undo never rewrites published work")

    if not blocked:
        result["apply"] = {"repo": root, "to": target, "expected_head": head}
    return result


def apply(repo, to, expected_head):
    fresh = preview(repo, to)
    head = fresh["head"]
    if head != expected_head:
        return {"applied": False, "refused": f"HEAD is {head}, expected {expected_head}; "
                                             "HEAD moved since the preview — preview again"}
    if fresh["blocked"] or not fresh["apply"]:
        return {"applied": False, "refused": "a fresh preview is blocked", "preview": fresh}
    root, target = fresh["apply"]["repo"], fresh["apply"]["to"]

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = BACKUP_PREFIX + stamp
    # Empty old value = create only: never overwrite an existing backup ref.
    rc, _, err = git(root, "update-ref", "-m", "devflow undo backup", backup, head, "")
    if rc != 0:
        return {"applied": False, "refused": f"could not write backup ref {backup}: {err}"}
    # Compare-and-swap on the branch: moves only if it still points at the previewed HEAD.
    rc, _, err = git(root, "update-ref", "-m", f"devflow undo: reset to {target}",
                     "HEAD", target, head)
    if rc != 0:
        return {"applied": False, "refused": f"branch moved; not reset ({err})",
                "backup_ref": backup}
    rc, _, err = git(root, "reset", "--hard", "--quiet")
    if rc != 0:
        return {"applied": False, "refused": f"branch moved to {target} but the work tree "
                                             f"reset failed: {err}", "backup_ref": backup}
    return {"applied": True, "branch": fresh["branch"], "from": head, "to": target,
            "removed": fresh["commits"], "backup_ref": backup,
            "restore": [f"git branch <name> {backup}   # recover as a new branch",
                        f"git reset --hard {backup}   # or move this branch back (clean tree)"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("preview")
    p.add_argument("--repo", required=True)
    p.add_argument("--to", required=True)
    a = sub.add_parser("apply")
    a.add_argument("--repo", required=True)
    a.add_argument("--to", required=True)
    a.add_argument("--expected-head", required=True)
    args = parser.parse_args(argv)

    if args.command == "preview":
        result = preview(args.repo, args.to)
        ok = not result["blocked"]
    else:
        result = apply(args.repo, args.to, args.expected_head)
        ok = result["applied"]
    print(json.dumps(result, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
