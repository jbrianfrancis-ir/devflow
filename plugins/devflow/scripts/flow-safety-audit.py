#!/usr/bin/env python3
"""Heuristic safety checks over a repo's tree. Backs `/flow-audit --safety`.

    python3 flow-safety-audit.py [--root DIR] [--strict]

One finding per line, `file:line  CHECK-ID  message`, then a count line. Checks
(guard patterns and fixes: references/safety-checks.md):
  S1-TESTDB      test config whose DB host is not local or a container
  S2-RM-GUARD    recursive delete on a variable target without ${VAR:?}
  S2-SET-U       shell script that does that without `set -u`
  S2-REALPATH    recursive delete on a variable with no realpath / inside-root check
  S4-CI-AGENT    workflow runs an AI agent on an untrusted trigger with secrets or write token
  S5-NO-WARNING  script that drops/destroys/resets/deploys and prints no `WARNING:` line
S3 (prose-only rules) needs judgment and lives in the skill.

Heuristics, not proof: a hit is a lead to read, a miss proves nothing. Reports DB
host names only, never a connection string. `.env*` files are never opened and
nothing here looks for secrets. Read-only. Exit 0 (advisory); with --strict, 1
when anything was found; 2 when the root is not a directory. Stdlib only.
"""

import argparse
import os
import re
import sys

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", "bin", "obj", "dist"}
MAX_BYTES = 1_000_000

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0", "host.docker.internal", "(localdb)", "."}
URL_HOST = re.compile(r"\b(?:postgres(?:ql)?|mysql|mariadb|mongodb(?:\+srv)?|redis|sqlserver|mssql|cockroachdb)"
                      r"://(?:[^/\s'\"]*@)?(\[[^\]]+\]|[^@:/?\s'\",;]+)", re.I)
# ADO.NET-style keys only inside a string (after a quote or `;`), so `host = os.environ[...]` is not read.
ADO_HOST = re.compile(r"[;'\"]\s*(?:Server|Host|Data Source|Address|Addr)\s*=\s*(?:tcp:)?([^;,'\"\s]+)", re.I)
TEST_CONFIG = re.compile(r"(^|/)(appsettings\.Test\w*\.json|conftest\.py|pytest\.ini|"
                         r"(jest|vitest)\.(config|setup)\.\w+|(docker-)?compose[\w.-]*test[\w.-]*\.ya?ml|"
                         r"[\w.-]*(setup|global-setup|fixtures?)[\w.-]*\.(py|[cm]?[jt]s|json|ya?ml))$", re.I)
TEST_DIR = re.compile(r"(^|/)(tests?|__tests__|spec|fixtures?)/", re.I)

SHELL_EXT = (".sh", ".bash", ".zsh")
RM_SHELL = re.compile(r"\brm\s+(?:-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)\b[^\n;&|]*")
SHELL_VAR = re.compile(r"\$\{(\w+)(:\?)?[^}]*\}|\$(\w+)")
RM_OTHER = re.compile(r"\b(?:rmtree|rimraf(?:\.sync)?)\(\s*(?!['\"`])\S|Remove-Item\b[^\n]*-Recurse[^\n]*\$\w+", re.I)
SET_U = re.compile(r"^\s*set\s+-[a-z]*u|^\s*set\s+-o\s+nounset", re.M)
INSIDE_ROOT = re.compile(r"realpath|readlink -f|is_relative_to|commonpath|\.resolve\(|Resolve-Path|GetFullPath|path\.resolve")

HAZARD = re.compile(r"\b(DROP\s+(TABLE|DATABASE|SCHEMA)|TRUNCATE\s+(TABLE\s+)?\w|dropdb|terraform\s+destroy|"
                    r"(az|azd)\s+(group\s+delete|down)|migrate\s+reset|db\s+reset|database\s+drop|"
                    r"kubectl\s+delete|helm\s+uninstall|flushall)\b", re.I)
HAZARD_NAME = re.compile(r"(deploy|reset|teardown|destroy|drop|nuke)[\w.-]*\.(sh|bash|ps1|py)$", re.I)
SCRIPT_EXT = SHELL_EXT + (".ps1", ".py")

UNTRUSTED = ("pull_request_target", "issue_comment", "pull_request_review_comment", "issues",
             "discussion", "discussion_comment", "workflow_run")
AGENT = re.compile(r"uses:\s*['\"]?(anthropics/|openai/codex|[\w.-]+/[\w.-]*(claude|codex|copilot|aider|cursor))"
                   r"|\bclaude\s+(-p|--print)\b|\bcodex\s+exec\b|\baider\s+--", re.I)
WRITE_PERM = re.compile(r"write-all|^\s*[\w-]+:\s*write\b", re.M)
SECRET_EXPR = re.compile(r"secrets\.(\w+)")


def lineno(text, pos):
    return text.count("\n", 0, pos) + 1


def compose_services(files):
    names = set()
    for rel, text in files:
        if re.search(r"(^|/)(docker-)?compose[\w.-]*\.ya?ml$", rel):
            block = re.search(r"^services:\s*\n((?:[ \t]+.*\n|\s*\n)*)", text, re.M)
            if block:
                names |= set(re.findall(r"^ {2}([\w.-]+):", block.group(1), re.M))
    return names


def is_local(host, services):
    h = host.strip("[]").lower()
    return (h in LOCAL_HOSTS or h.startswith("127.") or h in services
            or "testcontainers" in h or h.startswith(("$", "{", "%")) or "memory" in h
            or h.endswith((".db", ".sqlite", ".sqlite3")))


def check_testdb(rel, text, services, out):
    if not (TEST_CONFIG.search(rel) or (TEST_DIR.search(rel) and rel.endswith((".json", ".yml", ".yaml", ".ini", ".toml")))):
        return
    for rx in (URL_HOST, ADO_HOST):
        for m in rx.finditer(text):
            if not is_local(m.group(1), services):
                out.append((rel, lineno(text, m.start()), "S1-TESTDB",
                            f"test DB host '{m.group(1)}' is not local or a container; point tests at a local/"
                            "container DB and abort test setup when the host is not local"))


def check_rm(rel, text, out):
    shell = rel.endswith(SHELL_EXT) or text.startswith(("#!/bin/sh", "#!/bin/bash", "#!/usr/bin/env bash", "#!/usr/bin/env sh"))
    hits = []
    if shell:
        for m in RM_SHELL.finditer(text):
            unguarded = [braced or bare for braced, guard, bare in SHELL_VAR.findall(m.group(0)) if not guard]
            if SHELL_VAR.search(m.group(0)):
                hits.append(m.start())
            if unguarded:
                out.append((rel, lineno(text, m.start()), "S2-RM-GUARD",
                            f"recursive rm on ${unguarded[0]} without ${{{unguarded[0]}:?}}; an empty value deletes the parent"))
        if hits and not SET_U.search(text):
            out.append((rel, lineno(text, hits[0]), "S2-SET-U", "recursive delete on a variable without `set -euo pipefail` (at least -u)"))
    elif rel.endswith((".py", ".js", ".mjs", ".cjs", ".ts", ".ps1")):
        hits = [m.start() for m in RM_OTHER.finditer(text)]
    if hits and not INSIDE_ROOT.search(text):
        out.append((rel, lineno(text, hits[0]), "S2-REALPATH",
                    "recursive delete on a variable target with no realpath check that it stays inside the repo root"))


def check_hazard(rel, text, out):
    if not rel.endswith(SCRIPT_EXT) or "WARNING:" in text:
        return
    m = HAZARD.search(text)
    if m or HAZARD_NAME.search(rel):
        what = m.group(0) if m else os.path.basename(rel)
        out.append((rel, lineno(text, m.start()) if m else 1, "S5-NO-WARNING",
                    f"'{what}' runs with no `WARNING:` line naming the target and what gets destroyed"))


def top_block(text, key):
    m = re.search(rf"^['\"]?{key}['\"]?:(.*)\n((?:[ \t]+.*\n|\s*\n)*)", text, re.M)
    return (m.group(1) + "\n" + m.group(2), m.start()) if m else ("", -1)


def check_ci(rel, text, out):
    on, _ = top_block(text, "on")
    if not on:
        on, _ = top_block(text, "true")  # YAML 1.1 reads a bare `on` key as true
    triggers = [t for t in UNTRUSTED if re.search(rf"(^|[\s\[,]){t}\s*(:|,|\]|$)", on, re.M)]
    if not triggers:
        return
    top_perms, _ = top_block(text, "permissions")
    jobs, start = top_block(text, "jobs")
    for m in re.finditer(r"^ {2}([\w-]+):[ \t]*\n((?:(?: {3,}|\t).*\n|\s*\n)*)", jobs, re.M):
        body = m.group(2)
        if not AGENT.search(body):
            continue
        reach = sorted({f"secrets.{s}" for s in SECRET_EXPR.findall(body + top_block(text, "env")[0])})
        perms = body if re.search(r"^\s+permissions:", body, re.M) else top_perms
        if WRITE_PERM.search(perms):
            reach.append("write permissions")
        elif not perms.strip():
            reach.append("default token (no permissions block)")
        if reach:
            out.append((rel, lineno(text, start) + lineno(jobs, m.start()) - 1, "S4-CI-AGENT",
                        f"job '{m.group(1)}' runs an AI agent on {', '.join(triggers)} and can reach {', '.join(reach)}; "
                        "use least-privilege permissions, no secrets in agent jobs, no pull_request_target"))


def scan(root):
    files = []
    for base, dirs, names in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(names):
            if name.startswith(".env"):
                continue
            path = os.path.join(base, name)
            try:
                if os.path.islink(path) or os.path.getsize(path) > MAX_BYTES:
                    continue
                with open(path, encoding="utf-8") as fh:
                    files.append((os.path.relpath(path, root).replace(os.sep, "/"), fh.read()))
            except (OSError, UnicodeDecodeError):
                continue
    services, out = compose_services(files), []
    for rel, text in files:
        check_testdb(rel, text, services, out)
        check_rm(rel, text, out)
        check_hazard(rel, text, out)
        if re.match(r"\.github/workflows/[^/]+\.ya?ml$", rel):
            check_ci(rel, text, out)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=".")
    ap.add_argument("--strict", action="store_true", help="exit 1 when anything was found")
    args = ap.parse_args(argv)
    if not os.path.isdir(args.root):
        print(f"flow-safety-audit: {args.root}: not a directory", file=sys.stderr)
        return 2
    findings = scan(args.root)
    for rel, line, check, msg in findings:
        print(f"{rel}:{line}  {check}  {msg}")
    print(f"{len(findings)} finding(s)")
    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    sys.exit(main())
