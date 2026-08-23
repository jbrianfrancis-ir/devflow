#!/usr/bin/env python3
"""DevFlow fleet scanner — one board for every DevFlow project on this machine.

Answers "what is every session actually doing" without visiting a single terminal
tab. Works under any substrate (tmux, herdr, cmux, Orca, Superset, plain windows)
because it reads files, never screens.

Reads ONLY: `.planning/STATE.md` (≤1.5KB, including its `## Gate` and `## Run`
blocks), the `ROADMAP.md` table, the top lines of `.planning/JOURNAL.md`,
`.planning/config.json`, and git metadata. Never opens source, `.env*`, or key
files — same discipline as the BlitzOS scanner contract (`docs/blitzos.md` §1).

Zero dependencies (stdlib only).

Usage:
    python3 {devflow_root}/scripts/flow-fleet.py [ROOT ...] [--json] [--stale-days N] [--depth N]

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
PLUGIN_ROOT = os.path.expanduser("~/.claude/plugins")
INSTALLED_PLUGINS = os.path.join(PLUGIN_ROOT, "installed_plugins.json")
MARKETPLACE_MANIFEST = os.path.join(
    PLUGIN_ROOT, "marketplaces", "devflow", ".claude-plugin", "marketplace.json")
MARKETPLACE_CACHE = os.path.join(PLUGIN_ROOT, "marketplaces", "devflow")


# ---------------------------------------------------------------- helpers

def git(repo, *args):
    """Run a git command in `repo`. Returns stripped stdout, or None if the command
    could not be answered (git missing, not a repo, timeout, non-zero exit).

    None is deliberately distinct from "": a guard that cannot check must never
    report the clean answer. Callers decide what an unanswerable check means; none
    of them may treat it as "fine". See references/conventions.md → Fail-closed guards.
    """
    try:
        out = subprocess.run(
            ("git", "-C", repo) + args,
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


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
    """Body lines of a `## heading` section, up to the next `##`.

    HTML comments are stripped first. The templates carry their format spec as a
    commented-out example inside the very section it describes, so a line-prefix
    filter is not enough — an unfiltered inner line reads exactly like real content
    and would surface a template placeholder as a live gate. Only closed comments are
    removed: an unterminated one leaves its text visible, which errs toward flagging
    attention rather than hiding it.
    """
    text = re.sub(r"<!--.*?-->", "", text or "", flags=re.S)
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


def parse_gate(state):
    """The `## Gate` block — the one structured exception to "never parse skill prose".

    Returns None when absent or `none`. Everything inside is optional except `asked`:
    a gate that does not say what it is asking is not a gate record, so we return None
    rather than an object whose fields a driver would render as blanks.
    """
    lines = [ln for ln in section(state, "Gate") if not ln.startswith("<!--")]
    if not lines or lines[0].strip().lower() == "none":
        return None
    g = {"type": "", "asked": "", "options": [], "default": "", "plan": "", "task": ""}
    in_options = False
    for ln in lines:
        m = re.match(r"^(type|asked|default)\s*:\s*(.*)$", ln, re.I)
        if m:
            in_options = False
            g[m.group(1).lower()] = m.group(2).strip()
            continue
        if re.match(r"^options\s*:", ln, re.I):
            in_options = True
            continue
        m = re.match(r"^plan\s*:\s*([^|]+?)\s*(?:\|\s*task\s*:\s*(.*))?$", ln, re.I)
        if m:
            in_options = False
            g["plan"] = m.group(1).strip()
            g["task"] = (m.group(2) or "").strip()
            continue
        if in_options:
            opt = re.sub(r"^[-*]?\s*\d+[.)]\s*", "", ln).strip()
            if opt:
                g["options"].append(opt)
    return g if g["asked"] else None


def parse_run(state):
    """The `## Run` block — the autonomous loop's cross-iteration memory.

    Three outcomes, not two (conventions.md → Fail-closed guards): absent is a
    legitimate cold start (None), well-formed is the counters, and malformed is
    `{"malformed": True}` — never a zeroed counter, which would read as "fresh run"
    and silently disarm the stuck rail.
    """
    lines = [ln for ln in section(state, "Run") if not ln.startswith("<!--")]
    if not lines:
        return None
    it = re.search(r"Iteration:\s*(\d+)", "\n".join(lines))
    if not it:
        return {"malformed": True}
    started = re.search(r"Started:\s*([^|\s]+)", "\n".join(lines))
    repeats = re.search(r"Repeats:\s*(\d+)", "\n".join(lines))
    sig = re.search(r"^Signature:\s*(.+)$", "\n".join(lines), re.M)
    if repeats is None:
        return {"malformed": True}
    return {
        "iteration": int(it.group(1)),
        "started": started.group(1).strip() if started else None,
        "repeats": int(repeats.group(1)),
        "signature": sig.group(1).strip() if sig else None,
    }


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
        for line in (git(path, "worktree", "list", "--porcelain") or "").splitlines():
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

def semver(text):
    """(1, 2, 3) from "1.2.3"; None when it is not a plain version."""
    if not isinstance(text, str):
        return None
    parts = text.split(".")
    if len(parts) != 3 or not all(x.isdigit() for x in parts):
        return None
    return tuple(int(x) for x in parts)


def plugin_versions():
    """Which DevFlow build each project is pinned to, read locally.

    Every DevFlow repo carries the self-bootstrap block (conventions.md), so each
    one gets its OWN pinned install alongside the user-scope one, and they drift
    apart independently — a project can run a build two minors old with nothing
    saying so. This reads that pinning; it never touches the network, so
    `latest` is the newest build this machine has *heard of*, which may itself
    lag the published release. Reported as such rather than as the truth.

    Returns {"by_path", "user", "latest", "state"} where state is one of
    "ok" | "absent" (no Claude plugin system here — not applicable, not a
    failure) | "unreadable" (it exists but could not be parsed — a check that
    did not run, per conventions.md → Fail-closed guards).
    """
    out = {"by_path": {}, "user": None, "latest": None, "state": "ok",
           "cache_commit": None, "cache_age_days": None}
    if not os.path.isdir(PLUGIN_ROOT):
        out["state"] = "absent"
        return out
    try:
        with open(INSTALLED_PLUGINS, encoding="utf-8") as fh:
            installed = json.load(fh)
    except (OSError, ValueError):
        out["state"] = "unreadable"
        return out

    known = []
    for name, entries in (installed.get("plugins") or {}).items():
        if not name.startswith("devflow@"):
            continue
        for entry in entries if isinstance(entries, list) else []:
            version = entry.get("version")
            if semver(version):
                known.append(semver(version))
            if entry.get("scope") == "project" and entry.get("projectPath"):
                out["by_path"][os.path.realpath(entry["projectPath"])] = version
            elif entry.get("scope") == "user":
                out["user"] = version

    try:
        with open(MARKETPLACE_MANIFEST, encoding="utf-8") as fh:
            for plugin in json.load(fh).get("plugins") or []:
                if plugin.get("name") == "devflow" and semver(plugin.get("version")):
                    known.append(semver(plugin["version"]))
    except (OSError, ValueError):
        pass  # the cache is optional; the pinned versions still tell us plenty

    if known:
        out["latest"] = ".".join(str(n) for n in max(known))

    # How much `latest` is worth. The marketplace cache is a git clone that only
    # moves when Claude Code refreshes it, so a release can be tagged and public
    # while every local reading still says the old number — which is exactly how
    # 0.15.0 stayed invisible here after it shipped. Nothing below touches the
    # network (this scanner reads local state only), so the honest signal is not
    # "you are behind" but "this reading is N days old"; a stale cache means
    # `latest` is unproven, not that it is wrong.
    out["cache_commit"] = git(MARKETPLACE_CACHE, "rev-parse", "--short", "HEAD")
    fetch_head = os.path.join(MARKETPLACE_CACHE, ".git", "FETCH_HEAD")
    if os.path.isdir(MARKETPLACE_CACHE):
        try:
            age = (datetime.date.today()
                   - datetime.date.fromtimestamp(os.path.getmtime(fetch_head))).days
            out["cache_age_days"] = max(age, 0)
        except OSError:
            # Present but never fetched, or unreadable: not a fresh cache.
            out["cache_age_days"] = None
    return out


def scan(path, today, stale_days, versions=None):
    versions = versions if versions is not None else {"by_path": {}, "latest": None, "state": "absent"}
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

    # --- the structured halves: what is being asked, and whether the loop is moving
    p["gate"] = parse_gate(state)
    p["run"] = parse_run(state)

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

    branch = git(path, "rev-parse", "--abbrev-ref", "HEAD")
    p["branch"] = branch if branch else "?"
    status = git(path, "status", "--porcelain")
    # None means the check could not run — report that, never "0 dirty files".
    p["dirty"] = None if status is None else len([ln for ln in status.splitlines() if ln])
    common = git(path, "rev-parse", "--git-common-dir")
    gitdir = git(path, "rev-parse", "--git-dir")
    p["worktree"] = None if (common is None or gitdir is None) else (
        os.path.realpath(os.path.join(path, common))
        != os.path.realpath(os.path.join(path, gitdir)))
    origin = git(path, "remote", "get-url", "origin")
    m = re.search(r"[:/]([^/:]+/[^/]+?)(?:\.git)?$", origin) if origin else None
    p["repo"] = m.group(1) if m else p["name"]
    p["git_readable"] = branch is not None

    # --- flags: everything that means "a human should look"
    if not p["git_readable"]:
        # Unanswerable is a finding in its own right: this project's branch, dirty
        # state, and worktree status are all unknown, not clean.
        p["flags"].append("GIT-UNKNOWN")
    if p["flow"] == "unknown":
        # Same shape as GIT-UNKNOWN: no parseable FLOW state means the check did not
        # run, which is not the same as "nothing needs attention".
        p["flags"].append("FLOW-UNKNOWN")
    if p["run"] and p["run"].get("malformed"):
        p["flags"].append("RUN-UNKNOWN")
    if branch is not None and branch == base:
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

    p["devflow_version"] = versions["by_path"].get(os.path.realpath(path))
    if versions["state"] == "unreadable":
        p["flags"].append("VER-UNKNOWN")
    elif p["devflow_version"] and versions["latest"]:
        if semver(p["devflow_version"]) < semver(versions["latest"]):
            p["flags"].append("OLD-PLUGIN")

    p["needs_human"] = bool(
        p["flow"] in ATTENTION or p["blockers"]
        or any(f.startswith("STALE") for f in p["flags"])
        or "VER-UNKNOWN" in p["flags"]
        or not p["git_readable"]
        # A check that could not run never reports clean (conventions.md → Fail-closed
        # guards): an unreadable FLOW state or run counter is attention, not silence.
        or p["flow"] == "unknown"
        or (p["run"] or {}).get("malformed")
    )
    return p


# ---------------------------------------------------------------- render

def rank(p):
    """Attention first: unreadable, blocked, gated, stale, then in-flight, then done."""
    if not p.get("git_readable", True):
        return 0  # a check that could not run outranks one that ran and found a problem
    if p["flow"] == "unknown" or (p.get("run") or {}).get("malformed"):
        return 0  # same reason: unknown is not clean
    if p["flow"] == "BLOCKED" or p["blockers"]:
        return 0
    if p["flow"] == "GATE":
        return 1
    if any(f.startswith("STALE") for f in p["flags"]):
        return 2
    if p["flow"] == "DONE":
        return 4
    return 3


def render(projects, stale_days, versions=None):
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
            gate = p.get("gate")
            run = p.get("run") or {}
            if not p["git_readable"]:
                why = "git could not be read here — branch, dirty state and worktree status are UNKNOWN, not clean"
            elif run.get("malformed"):
                why = "STATE ## Run block is unreadable — the stuck rail is disarmed until it is fixed"
            elif p["flow"] == "unknown":
                why = "no parseable FLOW state in JOURNAL.md — this project's state is UNKNOWN, not clean"
            elif gate:
                why = "%s: %s" % (gate["type"] or "gate", gate["asked"])
            elif p["blockers"]:
                why = p["blockers"][0]
            elif stale:
                why = "no activity for %s while %s — %s" % (
                    stale.split(":")[1], p["status"], p["resume"] or p["last"] or "check the worktree")
            else:
                why = p["journal"] or p["last"] or p["flow"]
            # Two worktrees of one repo share `repo` — the branch is what tells them apart.
            label = trunc("%s [%s]" % (p["repo"], p["branch"]), 38)
            out.append("  %-38s %s" % (label, trunc(why, 76)))
            # The whole point of the structured gate: the choices reach the human here,
            # instead of only in the transcript of a session that has since scrolled away.
            for i, opt in enumerate((gate or {}).get("options", []), 1):
                out.append("  %-38s   %d. %s" % ("", i, trunc(opt, 72)))
            if run.get("repeats"):
                out.append("  %-38s   ↻ no progress for %d iteration(s) at %s"
                           % ("", run["repeats"], run.get("signature") or "?"))
            if p["next"]:
                out.append("  %-38s → cd %s && %s" % ("", tilde(p["path"]), p["next"]))

    idle = [p for p in projects if not p["needs_human"] and p["flow"] == "CONTINUE"]
    if idle:
        out.append("")
        out.append("Ready to advance (%d): %s" % (
            len(idle), ", ".join("%s [%s]" % (p["repo"], p["branch"]) for p in idle)))

    versions = versions or {}
    if versions.get("state") == "unreadable":
        out.append("")
        out.append("DevFlow build: could not read %s — version staleness NOT checked."
                   % tilde(INSTALLED_PLUGINS))
    elif versions.get("state") == "ok":
        pinned = sorted({p["devflow_version"] for p in projects if p.get("devflow_version")})
        if pinned:
            spread = ", ".join(
                "%s (%d)" % (v, sum(1 for p in projects if p.get("devflow_version") == v))
                for v in reversed(pinned))
            line = "DevFlow build: %s" % spread
            if versions.get("user"):
                line += " · user scope %s" % versions["user"]
            out.append("")
            out.append(line)
            behind = [p for p in projects if "OLD-PLUGIN" in p["flags"]]
            if behind:
                out.append("  %d project(s) behind %s: %s — each DevFlow repo carries its own "
                           "pinned install (conventions.md → Plugin self-bootstrap), so they drift "
                           "apart and none update on their own."
                           % (len(behind), versions["latest"],
                              ", ".join(p["repo"] for p in behind)))
            age = versions.get("cache_age_days")
            commit = versions.get("cache_commit") or "unknown"
            known = "  Newest build this machine knows of: %s (marketplace cache at %s" % (
                versions["latest"], commit)
            if age is None:
                out.append(known + ", never refreshed).")
                out.append("    That cache is the only local record of what has been published, and "
                           "it has no fetch on record — so %s is the newest build seen here, not the "
                           "newest that exists. Run `claude plugin marketplace update devflow`."
                           % versions["latest"])
            elif age >= stale_days:
                out.append(known + ", refreshed %dd ago)." % age)
                out.append("    A release published since then is invisible here, which is how a "
                           "merged version reaches nobody. Run `claude plugin marketplace update "
                           "devflow` before trusting this number.")
            else:
                out.append(known + ", refreshed %s)." % ("today" if age == 0 else "%dd ago" % age))

    out.append("")
    out.append("%d project(s) — stale threshold %dd. Flags: ON-BASE=committing to the base "
               "branch, WT=git worktree, NO-DECL=missing plugin self-bootstrap, "
               "OLD-PLUGIN=pinned DevFlow build behind the newest known, "
               "GIT-UNKNOWN/FLOW-UNKNOWN/RUN-UNKNOWN/VER-UNKNOWN=check could not run (not clean)."
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
    versions = plugin_versions()
    projects = [scan(p, today, stale_days, versions) for p in find_projects(roots, depth)]
    projects.sort(key=lambda p: (rank(p), p["repo"]))

    if args.as_json:
        print(json.dumps({"scanned": roots, "stale_days": stale_days,
                          "plugin_versions": versions, "projects": projects}, indent=2))
    else:
        print(render(projects, stale_days, versions))

    return 1 if any(p["needs_human"] for p in projects) else 0


if __name__ == "__main__":
    sys.exit(main())
