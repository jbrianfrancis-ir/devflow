#!/usr/bin/env python3
"""DevFlow fleet scanner — one board for every DevFlow project on this machine.

Answers "what is every session actually doing" without visiting a single terminal
tab. Works under any substrate (tmux, herdr, cmux, Orca, Superset, plain windows)
because it reads files, never screens.

Reads ONLY: `.planning/STATE.md` (≤1.5KB), the `ROADMAP.md` table, the top lines
of `.planning/JOURNAL.md`, `.planning/config.json`, and git metadata. Never opens
source, `.env*`, or key files — same discipline as the BlitzOS scanner contract
(`docs/blitzos.md` §1).

Zero dependencies (stdlib only).

Usage:
    python3 scripts/flow-fleet.py [ROOT ...] [--json] [--stale-days N] [--depth N]

Roots resolve in this order: positional args → `~/.devflow/fleet.json`
(`{"roots": ["~/dev"], "stale_days": 3}`) → the parent of the current directory.
Git worktrees of a discovered repo are always included, even outside the roots.

Exit status: 0 if every project is CONTINUE/DONE, 1 if any project needs a human
(GATE/BLOCKED/stale/dirty) — so a foreman session can branch on it directly.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

CONFIG_PATH = os.path.expanduser("~/.devflow/fleet.json")
PRUNE = {
    ".git", "node_modules", "bin", "obj", "dist", "build", "out", "target",
    "vendor", ".venv", "venv", "env", "__pycache__", ".next", ".nuxt", ".svelte-kit",
    ".cache", ".terraform", ".gradle", "Pods", "DerivedData", ".pytest_cache",
}
FLOW_STATES = ("CONTINUE", "GATE", "BLOCKED", "DONE")
ATTENTION = ("GATE", "BLOCKED")


# ---------------------------------------------------------------- helpers

def git(repo, *args):
    """Run a git command in `repo`; return stripped stdout, or "" on any failure."""
    try:
        out = subprocess.run(
            ("git", "-C", repo) + args,
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def read_capped(path, limit=8192):
    """Read a small planning artifact. Returns "" if absent or unreadable."""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read(limit)
    except OSError:
        return ""


def parse_date(text):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", text or "")
    if not m:
        return None
    try:
        return datetime.date.fromisoformat(m.group(1))
    except ValueError:
        return None


def section(text, heading):
    """Body lines of a `## heading` section, up to the next `##`."""
    m = re.search(r"^##\s+%s\s*$" % re.escape(heading), text, re.M | re.I)
    if not m:
        return []
    rest = text[m.end():]
    nxt = re.search(r"^##\s+", rest, re.M)
    body = rest[: nxt.start()] if nxt else rest
    return [ln.strip() for ln in body.splitlines() if ln.strip()]


def trunc(s, n):
    s = s or ""
    return s if len(s) <= n else s[: n - 1] + "…"


def tilde(path):
    home = os.path.expanduser("~")
    return "~" + path[len(home):] if path.startswith(home + os.sep) else path


# ---------------------------------------------------------------- discovery

def find_projects(roots, depth):
    """Walk roots (depth-limited) collecting dirs that contain .planning/STATE.md."""
    found = []
    seen = set()
    for root in roots:
        root = os.path.abspath(os.path.expanduser(root))
        if not os.path.isdir(root):
            continue
        base_depth = root.rstrip(os.sep).count(os.sep)
        for dirpath, dirnames, _ in os.walk(root):
            if dirpath.count(os.sep) - base_depth >= depth:
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if d not in PRUNE and not d.startswith(".")]
            if os.path.isfile(os.path.join(dirpath, ".planning", "STATE.md")):
                real = os.path.realpath(dirpath)
                if real not in seen:
                    seen.add(real)
                    found.append(dirpath)
                dirnames[:] = []  # a DevFlow project is a leaf; don't descend
    # Pull in worktrees of discovered repos even when they live outside the roots.
    for path in list(found):
        for line in git(path, "worktree", "list", "--porcelain").splitlines():
            if not line.startswith("worktree "):
                continue
            wt = line[len("worktree "):].strip()
            real = os.path.realpath(wt)
            if real in seen or not os.path.isfile(os.path.join(wt, ".planning", "STATE.md")):
                continue
            seen.add(real)
            found.append(wt)
    return sorted(found)


# ---------------------------------------------------------------- per-project read

def scan(path, today, stale_days):
    state = read_capped(os.path.join(path, ".planning", "STATE.md"), 4096)
    journal = read_capped(os.path.join(path, ".planning", "JOURNAL.md"), 4096)
    roadmap = read_capped(os.path.join(path, "ROADMAP.md")) or \
        read_capped(os.path.join(path, ".planning", "ROADMAP.md"))

    p = {"path": path, "name": os.path.basename(os.path.abspath(path)), "flags": []}

    # --- STATE.md Position block (stable, capped, rewrite-in-place — quote verbatim)
    pos = re.search(r"^Phase:\s*(.+)$", state, re.M)
    p["position"] = pos.group(1).strip() if pos else ""
    m = re.search(r"Phase:\s*(\d+)\s+of\s+(\d+)", state)
    p["phase"] = "%s/%s" % (m.group(1), m.group(2)) if m else "?"
    m = re.search(r"Plans:\s*(\d+)\s*/\s*(\d+)", state)
    p["plans"] = "%s/%s" % (m.group(1), m.group(2)) if m else ""
    m = re.search(r"Status:\s*([A-Za-z_-]+)", state)
    p["status"] = m.group(1).lower() if m else "?"
    m = re.search(r"^Next:\s*(.+)$", state, re.M)
    p["next"] = m.group(1).strip() if m else ""
    m = re.search(r"^Last:\s*(.+)$", state, re.M)
    p["last"] = m.group(1).strip() if m else ""

    blockers = [b.lstrip("- ").strip() for b in section(state, "Blockers")]
    p["blockers"] = [b for b in blockers if b.lower() not in ("none", "- none", "n/a")]

    resume = re.search(r"^Resume:\s*(.+)$", state, re.M)
    p["resume"] = resume.group(1).strip() if resume else ""

    # --- JOURNAL.md newest-first top line: date | /flow-cmd | outcome | FLOW state
    p["journal"] = ""
    p["flow"] = "unknown"
    for line in journal.splitlines():
        line = line.strip()
        if line.startswith("- ") and re.search(r"\d{4}-\d{2}-\d{2}", line):
            p["journal"] = line[2:].strip()
            tail = line.rsplit("|", 1)[-1].strip().upper()
            if tail in FLOW_STATES:
                p["flow"] = tail
            break

    # --- age: newest signal we have, journal line or STATE Last:
    dates = [d for d in (parse_date(p["journal"]), parse_date(p["last"])) if d]
    last_date = max(dates) if dates else None
    p["last_date"] = last_date.isoformat() if last_date else None
    p["age_days"] = (today - last_date).days if last_date else None

    # --- roadmap phase totals (fallback when STATE lacks "of N")
    if p["phase"] == "?" and roadmap:
        rows = re.findall(r"^\|\s*\d+\s*\|", roadmap, re.M)
        if rows:
            p["phase"] = "?/%d" % len(rows)

    # --- git
    cfg = {}
    try:
        cfg = json.loads(read_capped(os.path.join(path, ".planning", "config.json")) or "{}")
    except json.JSONDecodeError:
        pass
    gitcfg = cfg.get("git") or {}
    base = gitcfg.get("base") or "main"

    p["branch"] = git(path, "rev-parse", "--abbrev-ref", "HEAD") or "?"
    p["dirty"] = len([ln for ln in git(path, "status", "--porcelain").splitlines() if ln])
    common = git(path, "rev-parse", "--git-common-dir")
    gitdir = git(path, "rev-parse", "--git-dir")
    p["worktree"] = bool(common and gitdir and os.path.realpath(
        os.path.join(path, common)) != os.path.realpath(os.path.join(path, gitdir)))
    origin = git(path, "remote", "get-url", "origin")
    m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?$", origin) if origin else None
    p["repo"] = m.group(1) if m else p["name"]

    # --- flags: everything that means "a human should look"
    if p["branch"] == base:
        p["flags"].append("ON-BASE")  # conventions.md: code never lands on the base branch
    if p["dirty"]:
        p["flags"].append("DIRTY:%d" % p["dirty"])
    in_flight = p["status"] in ("planning", "ready", "executing", "verifying")
    if p["age_days"] is not None and p["age_days"] >= stale_days and in_flight:
        p["flags"].append("STALE:%dd" % p["age_days"])
    if p["worktree"]:
        p["flags"].append("WT")
    decl = read_capped(os.path.join(path, ".claude", "settings.json"))
    if "devflow@devflow" not in decl:
        p["flags"].append("NO-DECL")

    p["needs_human"] = bool(
        p["flow"] in ATTENTION or p["blockers"]
        or any(f.startswith("STALE") for f in p["flags"])
    )
    return p


# ---------------------------------------------------------------- render

def rank(p):
    """Attention first: blocked, gated, stale, then in-flight, then done."""
    if p["flow"] == "BLOCKED" or p["blockers"]:
        return 0
    if p["flow"] == "GATE":
        return 1
    if any(f.startswith("STALE") for f in p["flags"]):
        return 2
    if p["flow"] == "DONE":
        return 4
    return 3


def render(projects, stale_days):
    if not projects:
        return ("No DevFlow projects found. Pass roots as arguments, or create "
                "%s with {\"roots\": [\"~/dev\"]}." % CONFIG_PATH)

    rows = [("REPO", "BRANCH", "PHASE", "STATUS", "FLOW", "AGE", "FLAGS", "NEXT")]
    for p in projects:
        age = "—" if p["age_days"] is None else ("today" if p["age_days"] == 0 else "%dd" % p["age_days"])
        phase = p["phase"] + (" (%s)" % p["plans"] if p["plans"] else "")
        rows.append((
            trunc(p["repo"], 24), trunc(p["branch"], 20), phase, trunc(p["status"], 10),
            p["flow"], age, trunc(" ".join(p["flags"]), 22), trunc(p["next"], 24),
        ))

    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    out = []
    for i, r in enumerate(rows):
        out.append("  ".join(c.ljust(widths[j]) for j, c in enumerate(r)).rstrip())
        if i == 0:
            out.append("  ".join("-" * w for w in widths))

    attention = [p for p in projects if p["needs_human"]]
    if attention:
        out.append("")
        out.append("Needs a human (%d):" % len(attention))
        for p in attention:
            stale = next((f for f in p["flags"] if f.startswith("STALE")), "")
            if p["blockers"]:
                why = p["blockers"][0]
            elif stale:
                why = "no activity for %s while %s — %s" % (
                    stale.split(":")[1], p["status"], p["resume"] or p["last"] or "check the worktree")
            else:
                why = p["journal"] or p["last"] or p["flow"]
            # Two worktrees of one repo share `repo` — the branch is what tells them apart.
            label = trunc("%s [%s]" % (p["repo"], p["branch"]), 38)
            out.append("  %-38s %s" % (label, trunc(why, 76)))
            if p["next"]:
                out.append("  %-38s → cd %s && %s" % ("", tilde(p["path"]), p["next"]))

    idle = [p for p in projects if not p["needs_human"] and p["flow"] == "CONTINUE"]
    if idle:
        out.append("")
        out.append("Ready to advance (%d): %s" % (
            len(idle), ", ".join("%s [%s]" % (p["repo"], p["branch"]) for p in idle)))

    out.append("")
    out.append("%d project(s) — stale threshold %dd. Flags: ON-BASE=committing to the base "
               "branch, WT=git worktree, NO-DECL=missing plugin self-bootstrap."
               % (len(projects), stale_days))
    return "\n".join(out)


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description="Board of every DevFlow project on this machine.")
    ap.add_argument("roots", nargs="*", help="directories to scan (default: ~/.devflow/fleet.json, else ..)")
    ap.add_argument("--json", action="store_true", dest="as_json", help="machine-readable output")
    ap.add_argument("--stale-days", type=int, default=None, help="in-flight with no activity for N days is stale (default 3)")
    ap.add_argument("--depth", type=int, default=None, help="max directory depth per root (default 3)")
    args = ap.parse_args(argv)

    cfg = {}
    try:
        cfg = json.loads(read_capped(CONFIG_PATH) or "{}")
    except json.JSONDecodeError:
        print("warning: %s is not valid JSON — ignoring" % CONFIG_PATH, file=sys.stderr)

    roots = args.roots or cfg.get("roots") or [os.path.dirname(os.path.abspath(os.getcwd()))]
    # `is not None`, not `or`: --stale-days 0 (everything idle is stale) is a valid ask.
    stale_days = args.stale_days if args.stale_days is not None else cfg.get("stale_days", 3)
    depth = args.depth if args.depth is not None else cfg.get("depth", 3)

    today = datetime.date.today()
    projects = [scan(p, today, stale_days) for p in find_projects(roots, depth)]
    projects.sort(key=lambda p: (rank(p), p["repo"]))

    if args.as_json:
        print(json.dumps({"scanned": roots, "stale_days": stale_days, "projects": projects}, indent=2))
    else:
        print(render(projects, stale_days))

    return 1 if any(p["needs_human"] for p in projects) else 0


if __name__ == "__main__":
    sys.exit(main())
