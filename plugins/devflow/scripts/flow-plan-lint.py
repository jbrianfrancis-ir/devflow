#!/usr/bin/env python3
"""Deterministic lint of a phase's plans before any executor is dispatched.

    flow-plan-lint.py <phase-dir> [--repo <root>] [--json]

Lints every NN-MM-PLAN.md in <phase-dir> that has no matching NN-MM-SUMMARY.md (executed
plans are skipped — resume support; they still count as graph nodes). Exit 0 only when
there are zero findings; any finding exits 1. Rules (stable ids):

  R0 could-not-check  unreadable plan, unparseable frontmatter, non-git --repo, no HEAD
  R1 required frontmatter per references/plan-format.md
  R2 depends_on resolves to a plan in the phase
  R3 wave = 1 with no deps, else max(dependency wave) + 1
  R4 no dependency cycles
  R5 same-wave files_modified are disjoint
  R6 every files_modified path exists at HEAD, or is in files_new (this plan's, or a
     plan it transitively depends on); every files_new entry is also in files_modified
  R7 every repo-relative path in <context> exists at HEAD or is declared new as in R6

Fail-closed per conventions.md: a check that cannot run is an R0 finding, never a pass.
Frontmatter parsing is imported from flow-split-plan.py, so the two scripts cannot
disagree about what a plan says. Stdlib only.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

REQUIRED_KEYS = ("phase", "plan", "wave", "depends_on", "files_modified", "autonomous",
                 "requirements", "must_haves")
REQUIRED_MUST_HAVES = ("truths", "artifacts", "key_links")
LIST_KEYS = ("depends_on", "files_modified", "requirements")
# A <context> token is checked only when it is path-shaped: a `/`, a file extension, and
# none of the placeholder/glob punctuation that marks it as a family rather than a file.
CONTEXT_PATH_RE = re.compile(r"^[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+\.[A-Za-z0-9]+$")
CONTEXT_SPLIT_RE = re.compile(r"[\s,;()`\"'\[\]]+")


def load_split_plan():
    path = Path(__file__).resolve().parent / "flow-split-plan.py"
    spec = importlib.util.spec_from_file_location("flow_split_plan", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def strip_comments(fm_text: str) -> str:
    """Drop YAML `#` comments outside quotes (templates/plan.md carries them inline)."""
    out = []
    for line in fm_text.splitlines():
        quote = None
        cut = len(line)
        for i, ch in enumerate(line):
            if quote:
                if ch == quote:
                    quote = None
            elif ch in "\"'":
                quote = ch
            elif ch == "#" and (i == 0 or line[i - 1].isspace()):
                cut = i
                break
        out.append(line[:cut].rstrip())
    return "\n".join(out)


def clean(item: str, sp) -> str:
    return sp.dequote(item).strip("`").strip()


def parse_plan(path: Path, sp) -> dict:
    """Return {"fm": dict, "body": str}; raise sp.PlanError on anything unparseable."""
    text = sp.read_text(path)
    _, fm_text, body = sp.split_frontmatter(text)
    fm_text = strip_comments(fm_text)
    for n, line in enumerate(fm_text.splitlines(), 1):
        if line.strip() and not (sp.KEY_RE.match(line) or re.match(r"^\s*- ", line)):
            raise sp.PlanError(f"unparseable frontmatter line {n}: {line.strip()!r}")
    return {"fm": sp.parse_yaml_lite(fm_text), "body": body}


def check_required(fm: dict) -> list[str]:
    problems = []
    for key in REQUIRED_KEYS:
        if key not in fm:
            problems.append(f"missing required key '{key}'")
    for key in LIST_KEYS:
        if key in fm and not isinstance(fm[key], list):
            problems.append(f"'{key}' must be a list")
    if isinstance(fm.get("requirements"), list) and not fm["requirements"]:
        problems.append("'requirements' is empty (REQ-IDs from the roadmap — never empty)")
    if "wave" in fm and not (isinstance(fm["wave"], str) and fm["wave"].isdigit()
                             and int(fm["wave"]) >= 1):
        problems.append(f"'wave' must be a positive integer, got {fm['wave']!r}")
    if "autonomous" in fm and fm["autonomous"] not in ("true", "false"):
        problems.append(f"'autonomous' must be true or false, got {fm['autonomous']!r}")
    if "must_haves" in fm:
        mh = fm["must_haves"]
        if not isinstance(mh, dict):
            problems.append("'must_haves' must be a mapping")
        else:
            problems.extend(f"missing required key 'must_haves.{k}'"
                            for k in REQUIRED_MUST_HAVES if k not in mh)
    if "files_new" in fm and not isinstance(fm["files_new"], list):
        problems.append("'files_new' must be a list")
    return problems


def as_list(fm: dict, key: str, sp) -> list[str]:
    value = fm.get(key)
    return [clean(v, sp) for v in value] if isinstance(value, list) else []


def find_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
    """Every simple cycle reachable in `graph` (edges to unknown nodes ignored), each
    reported once, rotated to start at its smallest id."""
    cycles, seen = [], set()

    def walk(node: str, stack: list[str]) -> None:
        for dep in graph.get(node, []):
            if dep not in graph:
                continue
            if dep in stack:
                cyc = stack[stack.index(dep):]
                i = cyc.index(min(cyc))
                key = tuple(cyc[i:] + cyc[:i])
                if key not in seen:
                    seen.add(key)
                    cycles.append(list(key))
            else:
                walk(dep, stack + [dep])

    for start in sorted(graph):
        walk(start, [start])
    return cycles


def closure(pid: str, graph: dict[str, list[str]]) -> set[str]:
    """`pid` and every id it transitively depends on, resolvable or not (cycle-safe)."""
    out, todo = set(), [pid]
    while todo:
        node = todo.pop()
        if node in out:
            continue
        out.add(node)
        todo.extend(graph.get(node, []))
    return out


def repo_head(repo: Path) -> str | None:
    """Return None when `repo` is a git work tree with a resolvable HEAD, else the reason."""
    top = subprocess.run(["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    if top.returncode != 0:
        return f"--repo {repo} is not a git repository"
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "--quiet",
                           "HEAD^{commit}"], capture_output=True, text=True)
    if head.returncode != 0:
        return f"HEAD does not resolve in {repo}"
    return None


def exists_at_head(repo: Path, paths: set[str]) -> dict[str, bool] | None:
    """Batch `git cat-file -e HEAD:<path>`; None when git itself could not answer."""
    ordered = sorted(paths)
    if not ordered:
        return {}
    result = subprocess.run(["git", "-C", str(repo), "cat-file", "--batch-check"],
                            input="".join(f"HEAD:{p}\n" for p in ordered),
                            capture_output=True, text=True)
    lines = result.stdout.splitlines()
    if result.returncode != 0 or len(lines) != len(ordered):
        return None
    return {p: not line.endswith(" missing") for p, line in zip(ordered, lines)}


def repo_relative(path: str) -> bool:
    return bool(path) and not path.startswith("/") and ".." not in path.split("/")


def context_paths(body: str, sp) -> list[str]:
    m = sp.CONTEXT_RE.search(body)
    if not m:
        return []
    found = []
    for raw in CONTEXT_SPLIT_RE.split(m.group(0)[len("<context>"):-len("</context>")]):
        token = re.sub(r"(#.*|:\d+(-\d+)?)$", "", raw.rstrip(".:"))
        if token.startswith("./"):
            token = token[2:]
        # .planning/ is DevFlow state, not the codebase: it may be uncommitted
        # (commit_docs: false) and holds SUMMARYs an earlier wave writes at execute time.
        if token.startswith(".planning/") or not CONTEXT_PATH_RE.match(token):
            continue
        if repo_relative(token) and token not in found:
            found.append(token)
    return found


def lint(phase_dir: Path, repo: Path, sp) -> dict:
    findings: list[dict] = []

    def add(rule: str, plan: str, message: str) -> None:
        findings.append({"rule": rule, "plan": plan, "message": message})

    if not phase_dir.is_dir():
        add("R0", "-", f"phase dir {phase_dir} does not exist")
        return {"findings": findings, "linted": [], "skipped": []}
    plan_paths = {}
    for path in sorted(phase_dir.iterdir()):
        m = sp.PLAN_FILENAME_RE.match(path.name)
        if m and path.is_file():
            plan_paths[f"{m.group(1)}-{m.group(2)}"] = path
    if not plan_paths:
        add("R0", "-", f"no NN-MM-PLAN.md files found in {phase_dir}")
        return {"findings": findings, "linted": [], "skipped": []}

    skipped = [pid for pid in plan_paths if (phase_dir / f"{pid}-SUMMARY.md").is_file()]
    pending = [pid for pid in plan_paths if pid not in skipped]
    plans: dict[str, dict] = {}
    for pid, path in plan_paths.items():
        try:
            plans[pid] = parse_plan(path, sp)
        except sp.PlanError as exc:
            if pid in pending:
                add("R0", pid, f"could not parse {path.name}: {exc}")
            else:
                plans[pid] = None  # executed; only a problem if a pending plan needs it

    # R1 — on pending plans only; an executed plan already ran.
    valid: dict[str, dict] = {}
    for pid in pending:
        if pid not in plans:
            continue
        problems = check_required(plans[pid]["fm"])
        for problem in problems:
            add("R1", pid, problem)
        if not problems:
            valid[pid] = plans[pid]

    graph = {pid: as_list(p["fm"], "depends_on", sp) for pid, p in plans.items() if p}
    waves = {pid: int(p["fm"]["wave"]) for pid, p in plans.items()
             if p and str(p["fm"].get("wave", "")).isdigit()}

    for pid, plan in valid.items():
        deps = graph[pid]
        # R2
        unresolved = [d for d in deps if d not in plan_paths]
        for dep in unresolved:
            add("R2", pid, f"depends_on '{dep}' is not a plan in this phase "
                           f"(plans: {', '.join(plan_paths)})")
        # R3
        if unresolved:
            continue
        blind = [d for d in deps if d not in waves]
        if blind:
            add("R0", pid, f"could not check wave: dependency {', '.join(blind)} has no "
                           f"readable wave")
            continue
        expected = 1 if not deps else max(waves[d] for d in deps) + 1
        if waves[pid] != expected:
            add("R3", pid, f"wave {waves[pid]} but depends_on {deps or '[]'} requires wave "
                           f"{expected} (1 with no deps, else max(dependency wave) + 1)")

    # R4 — report each cycle once, on its smallest pending member.
    for cycle in find_cycles(graph):
        members = [pid for pid in cycle if pid in valid]
        if members:
            add("R4", min(members), "dependency cycle: " + " -> ".join(cycle + [cycle[0]]))

    # R5
    by_wave: dict[int, list[str]] = {}
    for pid in valid:
        by_wave.setdefault(waves[pid], []).append(pid)
    for wave, pids in sorted(by_wave.items()):
        for i, a in enumerate(pids):
            for b in pids[i + 1:]:
                shared = sorted(set(as_list(valid[a]["fm"], "files_modified", sp))
                                & set(as_list(valid[b]["fm"], "files_modified", sp)))
                if shared:
                    add("R5", b, f"wave {wave} shares files_modified with {a}: "
                                 f"{', '.join(shared)} — same-wave plans run in parallel")

    # R6/R7 need the repo; without it they are could-not-check, never a pass.
    reason = repo_head(repo)
    if reason is None:
        wanted: set[str] = set()
        for pid, plan in valid.items():
            wanted.update(p for p in as_list(plan["fm"], "files_modified", sp) if repo_relative(p))
            wanted.update(context_paths(plan["body"], sp))
        at_head = exists_at_head(repo, wanted)
        if at_head is None:
            reason = f"git cat-file could not read HEAD in {repo}"
    if reason is not None:
        add("R0", "-", f"could not check paths (R6/R7): {reason}")
    else:
        for pid, plan in valid.items():
            fm = plan["fm"]
            modified = as_list(fm, "files_modified", sp)
            own_new = as_list(fm, "files_new", sp)
            for path in own_new:
                if path not in modified:
                    add("R6", pid, f"files_new entry '{path}' is not in files_modified — "
                                   f"a created file is still a modified file; add it there")
            declared_new = set()
            for dep in closure(pid, graph):
                if dep not in plan_paths:
                    continue  # already an R2 finding
                if plans.get(dep) is None:
                    add("R0", pid, f"could not read files_new of dependency {dep}")
                    continue
                declared_new.update(as_list(plans[dep]["fm"], "files_new", sp))
            for path in modified:
                if not repo_relative(path):
                    add("R6", pid, f"files_modified entry '{path}' is not a repo-relative path")
                elif not at_head[path] and path not in declared_new:
                    add("R6", pid, f"files_modified path '{path}' does not exist at HEAD and "
                                   f"is not declared new — if this plan creates it, add it to "
                                   f"files_new; if a dependency creates it, declare it in that "
                                   f"plan's files_new; otherwise fix the path")
            for path in context_paths(plan["body"], sp):
                if not at_head[path] and path not in declared_new:
                    add("R7", pid, f"<context> path '{path}' does not exist at HEAD and is "
                                   f"not in files_new of this plan or a dependency — fix the "
                                   f"path, or declare the file new in the plan that creates it")

    return {"findings": findings, "linted": pending, "skipped": skipped}


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint a phase's plans before dispatch.")
    parser.add_argument("phase_dir", type=Path)
    parser.add_argument("--repo", type=Path, default=Path.cwd(),
                        help="repo whose HEAD the paths must exist in (default: cwd)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args()

    try:
        sp = load_split_plan()
    except Exception as exc:  # the parser is this lint's only way to read a plan
        result = {"findings": [{"rule": "R0", "plan": "-",
                                "message": f"could not load flow-split-plan.py: {exc}"}],
                  "linted": [], "skipped": []}
    else:
        result = lint(args.phase_dir, args.repo, sp)

    findings = result["findings"]
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        for f in findings:
            print(f"{f['rule']} {f['plan']}: {f['message']}")
        print(f"{len(findings)} findings, {len(result['linted'])} plans linted, "
              f"{len(result['skipped'])} skipped (executed)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
