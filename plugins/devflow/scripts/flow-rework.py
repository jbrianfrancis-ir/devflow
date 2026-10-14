#!/usr/bin/env python3
"""Rework rate: how much recently written code is changed or removed again soon after.

A line counts as reworked when a later commit modifies or deletes it within --window days
(author date) of the commit that added it. Lines are split by whether the adding commit
carries a `DevFlow-Agent:` trailer (conventions.md -> Attribution), so agent work is
measured against the repo's own non-agent baseline rather than an absolute bar.

  flow-rework.py [--repo <path>] [--since <date|tag|sha>] [--window <days>] [--json]

Method, kept simple so every figure can be reproduced by hand:
  1. `git log -p -M -U0 --no-merges <range>` lists every non-merge commit in range with its
     added lines and the old-side line ranges it deleted or modified.
  2. For each commit D with old-side ranges, `git blame --porcelain D^ -- <old path>` over
     those ranges names the commit that wrote each line D removed. When that origin is a
     commit in range and D came within --window days of it, the line is reworked.

Limits it reports rather than hides: merge commits are skipped on both sides (a conflict
resolution edit is not counted); renames are detected (-M), so a moved file is not read as
deleted and re-added, but code moved between files is; lines written less than --window
days before the newest commit have not had their full window yet. A class with fewer than
MIN_LINES added lines gets a small-sample note instead of a confident rate.

A signal, not a gate: read-only (git log and git blame only), exit 0 whenever it ran.
Exit 2 when git could not be read. Stdlib only (ARCHITECTURE.md: Python 3.9+).
"""

from __future__ import annotations

import argparse
import codecs
import json
import os
import re
import subprocess
import sys
from collections import Counter

MIN_LINES = 100
TOP_FILES = 10
COMMIT_MARK = "\x00commit "
HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+\d+(?:,(\d+))? @@")
BLAME_RE = re.compile(r"^([0-9a-f]{40}) \d+ \d+")


class CouldNotRun(Exception):
    """git could not be read. Reported on stderr with exit 2, never as a zero rate."""


def git(repo, *args):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(["git", "-C", repo, "-c", "core.quotePath=false", *args],
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", env=env)
    if result.returncode != 0:
        raise CouldNotRun(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def range_args(repo, since):
    """A tag or sha means `<since>..HEAD`; anything else is a date handed to `--since`."""
    probe = subprocess.run(["git", "-C", repo, "rev-parse", "--verify", "-q",
                            f"{since}^{{commit}}"], capture_output=True, text=True)
    if probe.returncode == 0:
        return [f"{probe.stdout.strip()}..HEAD"]
    return [f"--since={since}", "HEAD"]


def diff_path(raw):
    """The path from a `--- a/x` / `+++ b/x` line, or None for /dev/null."""
    raw = raw.rstrip("\n")
    if raw == "/dev/null":
        return None
    if raw.startswith('"') and raw.endswith('"'):
        raw = codecs.escape_decode(raw[1:-1].encode("latin-1", "replace"))[0].decode(
            "utf-8", "replace")
    return raw[2:]


def read_commits(repo, rng):
    """Every non-merge commit in range, oldest first: sha, author time, agent flag, lines
    added, and {old path: [(start, count)]} for the old-side lines it deleted or modified."""
    fmt = "%x00commit %H %at %(trailers:key=DevFlow-Agent,valueonly,separator=%x2C)"
    text = git(repo, "log", "-p", "-M", "-U0", "--no-merges", "--reverse", "--no-color",
               "--no-ext-diff", f"--format={fmt}", *rng)
    commits, current, old_path, pending = [], None, None, 0
    for line in text.split("\n"):
        if pending:  # inside a hunk: content lines, counted by the header, never parsed
            if line.startswith("\\"):  # "\ No newline at end of file" is not a line
                continue
            if line.startswith("+"):
                current["added"] += 1
            pending -= 1
            continue
        if line.startswith(COMMIT_MARK):
            sha, at, agent = (line[len(COMMIT_MARK):].split(" ", 2) + [""])[:3]
            current = {"sha": sha, "time": int(at), "agent": bool(agent.strip()),
                       "added": 0, "deleted": {}}
            commits.append(current)
        elif current is None:
            continue
        elif line.startswith("--- "):
            old_path = diff_path(line[4:])
        else:
            match = HUNK_RE.match(line)
            if match:
                start = int(match.group(1))
                old_n = 1 if match.group(2) is None else int(match.group(2))
                new_n = 1 if match.group(3) is None else int(match.group(3))
                if old_n and old_path:
                    current["deleted"].setdefault(old_path, []).append((start, old_n))
                pending = old_n + new_n
    return commits


def blame_origins(repo, sha, path, ranges):
    """{origin sha: line count} for the given old-side ranges of <path> at <sha>^."""
    spans = [arg for start, count in ranges for arg in ("-L", f"{start},+{count}")]
    text = git(repo, "blame", "--porcelain", *spans, f"{sha}^", "--", path)
    origins = Counter()
    for line in text.split("\n"):
        if line.startswith("\t"):
            continue
        match = BLAME_RE.match(line)
        if match:
            origins[match.group(1)] += 1
    return origins


def figures(added, reworked, commits):
    rate = round(100.0 * reworked / added, 1) if added else None
    return {"commits": commits, "lines_added": added, "lines_reworked": reworked,
            "rework_rate_pct": rate, "small_sample": added < MIN_LINES}


def measure(repo, since, window_days):
    head = git(repo, "rev-parse", "HEAD").strip()
    commits = read_commits(repo, range_args(repo, since))
    window = window_days * 86400
    by_sha = {c["sha"]: c for c in commits}
    reworked = Counter()   # "agent" / "baseline" -> lines
    files = Counter()      # agent-reworked lines per path (path as the reworking commit saw it)
    for commit in commits:
        for path, ranges in commit["deleted"].items():
            for origin_sha, count in blame_origins(repo, commit["sha"], path, ranges).items():
                origin = by_sha.get(origin_sha)
                if origin is None or commit["time"] - origin["time"] > window:
                    continue
                kind = "agent" if origin["agent"] else "baseline"
                reworked[kind] += count
                if origin["agent"]:
                    files[path] += count

    result = {"range": {"since": since, "head": head, "window_days": window_days}}
    for kind, is_agent in (("agent", True), ("baseline", False)):
        group = [c for c in commits if c["agent"] is is_agent]
        result[kind] = figures(sum(c["added"] for c in group), reworked[kind], len(group))
    result["top_files"] = [{"path": p, "lines_reworked": n}
                           for p, n in sorted(files.items(), key=lambda kv: (-kv[1], kv[0]))
                           [:TOP_FILES]]

    notes = []
    for kind, label in (("agent", "agent"), ("baseline", "non-agent baseline")):
        if result[kind]["small_sample"]:
            notes.append(f"{label}: {result[kind]['lines_added']} lines added (< {MIN_LINES}); "
                         "sample too small for a meaningful rate")
    if commits:
        newest = max(c["time"] for c in commits)
        open_lines = sum(c["added"] for c in commits if newest - c["time"] < window)
        if open_lines:
            notes.append(f"{open_lines} lines were added less than {window_days} days before the "
                         "newest commit; their rework window is still open, so the rates can "
                         "only rise")
    notes.append("merge commits are skipped on both sides; renames are followed (-M), code "
                 "moved between files is not")
    result["notes"] = notes
    return result


def render(result):
    rng = result["range"]
    lines = [f"Rework rate — window {rng['window_days']}d, since {rng['since']} "
             f"(HEAD {rng['head'][:7]})"]
    for kind, label in (("agent", "agent    "), ("baseline", "baseline ")):
        f = result[kind]
        rate = "n/a" if f["rework_rate_pct"] is None else f"{f['rework_rate_pct']}%"
        lines.append(f"  {label} {f['lines_added']} lines added, {f['lines_reworked']} reworked, "
                     f"rate {rate} ({f['commits']} commits)")
    if result["top_files"]:
        lines.append("Top files by agent rework:")
        lines += [f"  {t['lines_reworked']:>6}  {t['path']}" for t in result["top_files"]]
    lines.append("Notes:")
    lines += [f"  - {n}" for n in result["notes"]]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Age-weighted rework rate, agent vs baseline.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--since", default="30.days.ago",
                        help="date, tag or sha (default: 30.days.ago)")
    parser.add_argument("--window", type=int, default=14,
                        help="days after a line is written in which a change counts (default 14)")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.window < 1:
        parser.error("--window must be at least 1 day")
    try:
        result = measure(args.repo, args.since, args.window)
    except CouldNotRun as exc:
        print(f"flow-rework: could not run: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2) if args.json else render(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
