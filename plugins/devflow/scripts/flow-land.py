#!/usr/bin/env python3
"""Land same-wave executor work from per-plan worktrees onto the feature branch, serially.

`/flow-execute` gives every executor in a wave its own git worktree on a task branch
`flow-task/<NN-MM>` cut at the wave base. This script is the only landing authority:

  wave-start --repo <main>   record the wave base (HEAD, branch, worktrees, branches) in a
                             state file under the main checkout's git dir, never the tree.
                             Refuses on a base branch, a detached HEAD, or a dirty tree.
  leak-check --repo <main>   the main checkout is exactly as the wave left it: same branch,
                             HEAD at the last landed commit, `git status --porcelain` empty.
                             Isolation guards edit tools, not Bash, so this is the enforcement.
  land --repo <main> --plan NN-MM --task-branch flow-task/NN-MM --worktree <path>
                             cherry-pick <wave-base>..<task-branch> onto the feature branch,
                             prove with `git cherry` that every task commit landed, then remove
                             the worktree and delete the task branch. One plan per call; a lock
                             file refuses a concurrent land. A conflict is aborted, never resolved.
  wave-end --repo <main>     no `flow-task/*` branch, no branch or worktree created during the
                             wave, no land lock, and a clean leak-check. Success clears the state.

Local only: nothing here pushes, fetches, or writes any ref other than the current feature
branch and the task branches it deletes, and every subcommand refuses to run on the base
branch. Output is one JSON object; exit 0 = ok, 1 = findings. Fail-closed: a git call that
fails, or state that cannot be read, is a `could-not-check` finding — never a pass
(conventions.md -> Fail-closed guards).

Stdlib only (ARCHITECTURE.md: Python 3.9+, no dependencies).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

STATE_FILE = "devflow-wave.json"
LOCK_FILE = "devflow-land.lock"
ALWAYS_PROTECTED = ("main", "dev")
TASK_PREFIX = "flow-task/"
PLAN_RE = re.compile(r"^\d+-\d+$")


class CouldNotCheck(Exception):
    """A check that could not be performed. Reported as a finding, never as clean."""


def finding(kind, detail, paths=None):
    item = {"kind": kind, "detail": detail}
    if paths:
        item["paths"] = paths
    return item


def git(repo, *args, check=True):
    result = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and result.returncode != 0:
        raise CouldNotCheck(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def out(repo, *args):
    return git(repo, *args).stdout.strip()


def toplevel(repo):
    return os.path.realpath(out(repo, "rev-parse", "--show-toplevel"))


def git_dir(repo):
    return out(repo, "rev-parse", "--absolute-git-dir")


def current_branch(repo):
    """The checked-out branch, or None on a detached HEAD."""
    result = git(repo, "symbolic-ref", "--short", "-q", "HEAD", check=False)
    if result.returncode == 0:
        return result.stdout.strip()
    if result.returncode == 1:
        return None
    raise CouldNotCheck(f"git symbolic-ref failed: {result.stderr.strip()}")


def protected_branches(repo):
    """main, dev, and `git.base` from .planning/config.json when the project declares one.
    A config that exists but cannot be read is could-not-check, not "no base declared"."""
    names = set(ALWAYS_PROTECTED)
    path = os.path.join(repo, ".planning", "config.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as stream:
                config = json.load(stream)
        except (OSError, json.JSONDecodeError) as exc:
            raise CouldNotCheck(f".planning/config.json unreadable: {exc}")
        base = (config.get("git") or {}).get("base") if isinstance(config, dict) else None
        if isinstance(base, str) and base:
            names.add(base)
    return names


def porcelain(repo):
    lines = git(repo, "status", "--porcelain", "--untracked-files=all").stdout.splitlines()
    return [line[3:] for line in lines if line.strip()]


def worktrees(repo):
    """Registered worktrees as {realpath: {"branch": ..., "locked": bool}}."""
    entries, current = {}, None
    for line in out(repo, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            current = os.path.realpath(line[len("worktree "):])
            entries[current] = {"branch": None, "locked": False}
        elif current and line.startswith("branch "):
            entries[current]["branch"] = line[len("branch "):].removeprefix("refs/heads/")
        elif current and (line == "locked" or line.startswith("locked ")):
            entries[current]["locked"] = True
    return entries


def branches(repo):
    return sorted(b for b in out(repo, "for-each-ref", "--format=%(refname:short)",
                                  "refs/heads/").splitlines() if b)


def rev(repo, name):
    result = git(repo, "rev-parse", "--verify", "-q", f"{name}^{{commit}}", check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def read_state(repo):
    path = os.path.join(git_dir(repo), STATE_FILE)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as stream:
            state = json.load(stream)
    except (OSError, json.JSONDecodeError) as exc:
        raise CouldNotCheck(f"wave state {path} unreadable: {exc}")
    for key in ("branch", "wave_base", "expected_head", "worktrees", "branches", "landed"):
        if key not in state:
            raise CouldNotCheck(f"wave state {path} is missing {key!r}")
    return state


def write_state(repo, state):
    path = os.path.join(git_dir(repo), STATE_FILE)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as stream:
        json.dump(state, stream, indent=2)
    os.replace(tmp, path)


def base_branch_findings(repo, branch):
    if branch is None:
        return [finding("detached-head", "HEAD is detached; landing needs the feature branch")]
    if branch in protected_branches(repo):
        return [finding("base-branch", f"current branch {branch!r} is a base branch; "
                        "landing runs only on a flow/<slug> feature branch")]
    return []


def leak_findings(repo, state):
    """The main checkout must be exactly where the wave left it."""
    findings = []
    branch = current_branch(repo)
    if branch != state["branch"]:
        findings.append(finding("leak", f"branch moved: {state['branch']!r} -> {branch!r}"))
    head = rev(repo, "HEAD")
    if head != state["expected_head"]:
        findings.append(finding("leak", f"HEAD moved: expected {state['expected_head']}, "
                                f"found {head}"))
    dirty = porcelain(repo)
    if dirty:
        findings.append(finding("leak", "main checkout has uncommitted or untracked changes",
                                dirty))
    return findings


def unlanded(repo, task_branch, wave_base, commits):
    """(landed, not_landed) task commits. `git cherry` compares by patch identity the task
    commits HEAD cannot reach; a commit it does not list is on HEAD already (a cherry-pick
    made in the same second as the original can reproduce the original SHA exactly)."""
    listed = {}
    for line in out(repo, "cherry", "HEAD", task_branch, wave_base).splitlines():
        sign, _, sha = line.partition(" ")
        listed[sha] = sign
    missing = [sha for sha in commits if listed.get(sha) == "+"]
    return [sha for sha in commits if sha not in missing], missing


# --- subcommands --------------------------------------------------------------------------

def cmd_wave_start(repo, args):
    existing = read_state(repo)
    if existing is not None:
        return [finding("wave-in-flight", "a wave is already recorded; finish it with land "
                        "and wave-end (resume uses its wave_base)")], {"state": existing}
    branch = current_branch(repo)
    findings = base_branch_findings(repo, branch)
    dirty = porcelain(repo)
    if dirty:
        findings.append(finding("dirty", "working tree is not clean", dirty))
    stale = [b for b in branches(repo) if b.startswith(TASK_PREFIX)]
    if stale:
        findings.append(finding("leftover-branch", "task branches from an earlier wave "
                                "remain", stale))
    if findings:
        return findings, {}
    head = rev(repo, "HEAD")
    if head is None:
        raise CouldNotCheck("HEAD does not resolve to a commit")
    state = {"branch": branch, "wave_base": head, "expected_head": head,
             "worktrees": sorted(worktrees(repo)), "branches": branches(repo), "landed": []}
    write_state(repo, state)
    return [], {"wave_base": head, "branch": branch}


def cmd_leak_check(repo, args):
    state = read_state(repo)
    if state is None:
        return [finding("no-wave", "no wave recorded; run wave-start first")], {}
    return leak_findings(repo, state), {}


def cmd_land(repo, args):
    if not PLAN_RE.match(args.plan):
        return [finding("usage", f"--plan must be NN-MM, got {args.plan!r}")], {}
    if args.task_branch != TASK_PREFIX + args.plan:
        return [finding("usage", f"--task-branch must be {TASK_PREFIX}{args.plan}")], {}
    lock = os.path.join(git_dir(repo), LOCK_FILE)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return [finding("locked", f"another land holds {lock}; landing is serial. If no land "
                        "is running, a crashed one left it — inspect, then remove it by hand")], {}
    try:
        os.write(fd, f"{os.getpid()} {args.plan}\n".encode())
        os.close(fd)
        return land(repo, args)
    finally:
        os.remove(lock)


def land(repo, args):
    state = read_state(repo)
    if state is None:
        return [finding("no-wave", "no wave recorded; run wave-start first")], {}
    findings = base_branch_findings(repo, current_branch(repo)) + leak_findings(repo, state)
    task, base = args.task_branch, state["wave_base"]
    if rev(repo, f"refs/heads/{task}") is None:
        findings.append(finding("no-task-branch", f"branch {task} does not exist"))
        return findings, {}
    wt_path = os.path.realpath(args.worktree)
    wt = worktrees(repo).get(wt_path)
    if wt is None and os.path.exists(wt_path):
        findings.append(finding("unregistered-worktree", f"{wt_path} exists but is not a "
                                "registered worktree of this repo"))
    elif wt is not None:
        if wt["branch"] != task:
            findings.append(finding("worktree-branch", f"{wt_path} has {wt['branch']!r} "
                                    f"checked out, not {task}"))
        dirty = porcelain(wt_path)
        if dirty:
            findings.append(finding("dirty-worktree", "task worktree holds uncommitted work "
                                    "that landing would lose", dirty))
    if findings:
        return findings, {}
    # The executor cut its branch at the wave base and committed linearly on it, so the
    # task commits must form one parent chain rooted exactly at the wave base.
    commits, parent = [], base
    for line in out(repo, "rev-list", "--reverse", "--parents", f"{base}..{task}").splitlines():
        sha, *parents = line.split()
        if parents != [parent]:
            return [finding("wrong-base", f"{task} is not a linear chain on the wave base "
                            f"{base}: {sha} has parent(s) {parents}")], {}
        commits.append(sha)
        parent = sha
    if not commits:
        return [finding("no-commits", f"{task} has no commits past the wave base")], {}

    landed, missing = unlanded(repo, task, base, commits)
    before, recovered = rev(repo, "HEAD"), not missing
    if landed and missing:
        return [finding("partial-landing", "some task commits are already on the feature "
                        "branch and some are not — an interrupted land; resolve by hand",
                        missing)], {}
    if missing:
        pick = git(repo, "cherry-pick", f"{base}..{task}", check=False)
        if pick.returncode != 0:
            conflicted = git(repo, "diff", "--name-only", "--diff-filter=U",
                             check=False).stdout.split()
            abort = git(repo, "cherry-pick", "--abort", check=False)
            clean = abort.returncode == 0 and rev(repo, "HEAD") == before and not porcelain(repo)
            detail = ("cherry-pick failed and was aborted; the feature branch is unchanged — "
                      "never resolved here" if clean else
                      "cherry-pick failed and the abort did NOT restore the feature branch")
            return [finding("conflict", detail, conflicted or None)], {}
        state["expected_head"] = rev(repo, "HEAD")
        write_state(repo, state)
        landed, missing = unlanded(repo, task, base, commits)
        if missing:
            return [finding("incomplete-landing", "git cherry does not find these task "
                            "commits on the feature branch (a same-wave plan changed the same "
                            "file nearby, or a pick went wrong); worktree and branch kept — "
                            "resolve by hand", missing)], {}

    head = rev(repo, "HEAD")
    state["expected_head"] = head
    if args.plan not in state["landed"]:
        state["landed"].append(args.plan)
    write_state(repo, state)

    cleanup = []
    if wt is not None:
        if wt["locked"]:
            git(repo, "worktree", "unlock", wt_path)
        removed = git(repo, "worktree", "remove", wt_path, check=False)
        if removed.returncode != 0:
            cleanup.append(finding("worktree-remove-failed", removed.stderr.strip(), [wt_path]))
    if not cleanup:
        # -D is safe here and only here: `git cherry` just proved every commit is on HEAD.
        git(repo, "branch", "-D", task)
        if args.host_branch:
            cleanup += delete_host_branch(repo, args.host_branch)
    return cleanup, {"plan": args.plan, "head": head, "commits": len(commits),
                     "recovered": recovered}


def delete_host_branch(repo, name):
    """The branch the host created the worktree on, abandoned when the executor switched to
    its task branch. Deleted only when every commit on it is reachable from another ref."""
    if rev(repo, f"refs/heads/{name}") is None:
        return []
    if name.startswith(TASK_PREFIX) or name in protected_branches(repo):
        return [finding("usage", f"--host-branch {name!r} is not a host worktree branch")]
    if any(w["branch"] == name for w in worktrees(repo).values()):
        return [finding("host-branch-in-use", f"{name} is still checked out in a worktree")]
    unique = out(repo, "rev-list", "--count", f"refs/heads/{name}", "--not",
                 f"--exclude={name}", "--branches", "--remotes", "--tags")
    if unique != "0":
        return [finding("host-branch-has-commits", f"{name} has {unique} commit(s) on no "
                        "other ref; not deleted")]
    git(repo, "branch", "-D", name)
    return []


def cmd_wave_end(repo, args):
    state = read_state(repo)
    if state is None:
        return [finding("no-wave", "no wave recorded; run wave-start first")], {}
    findings = leak_findings(repo, state)
    if os.path.exists(os.path.join(git_dir(repo), LOCK_FILE)):
        findings.append(finding("locked", "a land lock remains"))
    now = branches(repo)
    leftover = sorted(b for b in now if b.startswith(TASK_PREFIX)
                      or (b not in state["branches"] and b != state["branch"]))
    if leftover:
        findings.append(finding("leftover-branch", "branches left behind by the wave",
                                leftover))
    extra = sorted(set(worktrees(repo)) - set(state["worktrees"]))
    if extra:
        findings.append(finding("leftover-worktree", "worktrees left behind by the wave",
                                extra))
    if not findings:
        os.remove(os.path.join(git_dir(repo), STATE_FILE))
    return findings, {"landed": state["landed"]}


COMMANDS = {"wave-start": cmd_wave_start, "leak-check": cmd_leak_check,
            "land": cmd_land, "wave-end": cmd_wave_end}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in COMMANDS:
        p = sub.add_parser(name)
        p.add_argument("--repo", required=True, help="the main checkout (never a task worktree)")
        if name == "land":
            p.add_argument("--plan", required=True, help="NN-MM")
            p.add_argument("--task-branch", required=True, help="flow-task/NN-MM")
            p.add_argument("--worktree", required=True, help="the task worktree path")
            p.add_argument("--host-branch", help="branch the host created the worktree on")
    args = parser.parse_args(argv)
    result = {"command": args.command}
    try:
        repo = toplevel(args.repo)
        findings, extra = COMMANDS[args.command](repo, args)
        result.update(extra)
    except CouldNotCheck as exc:
        findings = [finding("could-not-check", str(exc))]
    result["ok"] = not findings
    result["findings"] = findings
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
