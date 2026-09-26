#!/usr/bin/env python3
"""Inventory the mechanically checkable claims in a project's Markdown docs and
check each one against the working tree. Backs `/flow-audit --docs`.

    python3 flow-docs-audit.py [--root DIR] [PATH ...]

PATH is a Markdown file or a directory (its `*.md`, recursively). With no PATH
the scope is README.md, docs/**/*.md, AGENTS.md, CLAUDE.md and
.planning/ARCHITECTURE.md, each only if present. --root defaults to the git
top-level of the current directory; outside a repo it is an error, never a
guess.

Rules, one per claim kind:
  D1  repo-relative path in a backtick span or a Markdown link  -> exists?
  D2  script invoked in a shell fence (`python3 x.py`, `./run.sh`) -> file exists?
  D3  `npm run s` / `pnpm s` / `yarn s` -> key in the nearest package.json scripts?
  D4  `make t` -> target in the Makefile?
  D5  env var named in an environment/config table -> referenced in any non-doc file?

Every claim is `verified`, `contradicted`, or `could-not-check` — the third is
never folded into the first (references/conventions.md -> Fail-closed guards):
an unreadable doc, a missing package.json or Makefile, a path outside the root
are all could-not-check. Output is JSON on stdout. Exit 0 = no contradictions,
1 = at least one contradicted claim, 2 = could not run at all.

Read-only. `.env*` files are never opened; D5 reports names only.
Stdlib only; stands alone (no import from the repo's own scripts/).
"""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from urllib.parse import unquote

VERIFIED, CONTRADICTED, NOT_CHECKED = "verified", "contradicted", "could-not-check"

DEFAULT_SCOPE = ("README.md", "AGENTS.md", "CLAUDE.md", ".planning/ARCHITECTURE.md")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache"}
DOC_EXTS = (".md", ".markdown", ".mdx", ".rst", ".txt")

# Fence info strings whose lines are commands. An untagged fence counts too:
# D2-D4 only fire on specific command shapes, so prose in one matches nothing.
SHELL_INFO = {"", "sh", "bash", "shell", "zsh", "console", "terminal", "powershell", "pwsh", "ps1"}
INTERPRETERS = {"python", "python3", "bash", "sh", "zsh", "node", "ruby", "perl", "pwsh", "deno", "bun", "tsx"}
SCRIPT_EXT = re.compile(r"\.(py|sh|bash|zsh|js|mjs|cjs|ts|ps1|rb|pl)$")
# Not package scripts: pnpm/yarn verbs that are the tool's own commands.
PM_BUILTINS = {
    "add", "audit", "bin", "cache", "config", "create", "dedupe", "dlx", "exec", "global",
    "help", "i", "import", "info", "init", "install", "link", "list", "login", "logout", "ls",
    "outdated", "pack", "patch", "prune", "publish", "rebuild", "remove", "rm", "root", "set",
    "setup", "store", "un", "uninstall", "unlink", "up", "update", "upgrade", "version", "why",
    "workspace", "workspaces", "x", "env", "node", "self-update", "run",
}
NPM_LIFECYCLE = {"test", "start", "stop", "restart"}

PATH_TOKEN = re.compile(r"^[A-Za-z0-9_.@-]+(?:/[A-Za-z0-9_.@-]+)+/?$")
HAS_EXT = re.compile(r"\.[A-Za-z0-9]{1,8}$")
# A template segment: `NN-slug`, `run-N`, `YYYY-MM-DD.md`, `X`.
PLACEHOLDER_SEG = re.compile(r"(^|[-_.])(N{1,3}|M{1,2}|X{1,3}|YYYY|MM|DD)([-_.]|$)")
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
LINK = re.compile(r"!?\[[^\]]*\]\(\s*([^)\s]+)(?:\s+[\"'(][^)]*)?\)")
CODE_SPAN = re.compile(r"(`+)([^`]+?)\1")
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
ENV_HEADING = re.compile(r"env|environment|config", re.I)
ENV_NAME = re.compile(r"^[A-Z][A-Z0-9_]{2,}$")
QUICKSTART = re.compile(r"quick ?start|getting started|install|setup|set up|usage", re.I)
MAKE_TARGET = re.compile(r"^([^\s:=#][^:=#]*?)\s*::?(?![=])")


class Unreadable(Exception):
    pass


def _read(path):
    try:
        with open(path, encoding="utf-8") as stream:
            return stream.read()
    except (OSError, UnicodeDecodeError) as exc:
        raise Unreadable(str(exc)) from exc


def _inside(root, path):
    return path == root or path.startswith(root + os.sep)


def _exists(root, rel_base, target):
    """(status, detail) for `target` resolved against `rel_base` (abs dir).

    A path that normalizes above the root, or whose realpath escapes it, is
    could-not-check: the tree under audit says nothing about it.
    """
    joined = os.path.normpath(os.path.join(rel_base, target))
    if not _inside(root, joined):
        return NOT_CHECKED, "resolves outside the audited root"
    try:
        os.stat(joined)
    except (FileNotFoundError, NotADirectoryError):
        return CONTRADICTED, f"no such path: {os.path.relpath(joined, root)}"
    except OSError as exc:
        return NOT_CHECKED, f"stat failed: {exc.strerror}"
    if not _inside(os.path.realpath(root), os.path.realpath(joined)):
        return NOT_CHECKED, "symlink escapes the audited root"
    return VERIFIED, os.path.relpath(joined, root)


def _is_placeholder(token):
    if re.search(r"[<>{}$*?\[\]|]", token) or "..." in token:
        return True
    return any(PLACEHOLDER_SEG.search(seg) for seg in token.strip("/").split("/"))


# --- markdown structure -------------------------------------------------------

def _frontmatter_end(lines):
    """Index after a genuine YAML frontmatter block, else 0 (a lone leading
    `---` with no closer is a thematic break, not frontmatter)."""
    if not lines or lines[0].strip() != "---":
        return 0
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return i + 1
    return 0


def _blocks(lines):
    """Per-line fence info: None outside a fence, else (info, is_delimiter).
    Returns (per_line, unterminated_at) with unterminated_at 1-indexed or None."""
    per_line = [None] * len(lines)
    start = _frontmatter_end(lines)
    fence = None
    opened = None
    for i in range(start, len(lines)):
        stripped = lines[i].strip()
        if fence:
            char, length, info = fence
            closing = re.match(rf"^{re.escape(char)}{{{length},}}\s*$", stripped)
            per_line[i] = (info, bool(closing))
            if closing:
                fence = None
            continue
        match = re.match(r"^(`{3,}|~{3,})\s*([^\s`]*)", stripped)
        if match:
            fence = (stripped[0], len(match.group(1)), match.group(2).lower())
            opened = i + 1
            per_line[i] = (fence[2], True)
    return per_line, (opened if fence else None)


# --- claims -------------------------------------------------------------------

class Audit:
    def __init__(self, root):
        self.root = os.path.realpath(root)
        self.claims = []
        self._seen = set()
        self._env_index = None

    def add(self, rule, doc, line, claim, status, detail, section):
        key = (rule, doc, line, claim)
        if key in self._seen:
            return
        self._seen.add(key)
        entry = {"rule": rule, "file": doc, "line": line, "claim": claim,
                 "status": status, "detail": detail, "section": section}
        if status == CONTRADICTED:
            quick = doc == "README.md" and rule in ("D1", "D2", "D3", "D4") and QUICKSTART.search(section or "")
            entry["severity"] = "HIGH" if quick else "MEDIUM"
        self.claims.append(entry)

    # D1 --------------------------------------------------------------------
    def check_backtick_path(self, doc, doc_dir, line, token, section):
        if not PATH_TOKEN.match(token) or _is_placeholder(token) or SCHEME.match(token):
            return
        if not (token.endswith("/") or HAS_EXT.search(token.rsplit("/", 1)[-1])):
            return  # `origin/main`, `owner/repo`: slash-words, not paths
        if token.startswith(("~/", "/")):
            return
        # Base-ambiguous prose: the root first, then the doc's own directory.
        results = [_exists(self.root, base, token) for base in (self.root, doc_dir)]
        best = next((r for r in results if r[0] == VERIFIED), None)
        if best is None:
            best = next((r for r in results if r[0] == NOT_CHECKED), results[0])
        self.add("D1", doc, line, token, best[0], best[1], section)

    def check_link(self, doc, doc_dir, line, target, section):
        if target.startswith("<") or SCHEME.match(target) or target.startswith(("//", "www.", "#")):
            return
        path = unquote(target.split("#", 1)[0].split("?", 1)[0])
        if not path or _is_placeholder(path):
            return
        if path.startswith("/"):
            base, path = self.root, path.lstrip("/")
        else:
            base = doc_dir  # a link resolves against its own file's directory (GitHub's rule)
        status, detail = _exists(self.root, base, path)
        self.add("D1", doc, line, target, status, detail, section)

    # D2-D4 -----------------------------------------------------------------
    def check_command(self, doc, doc_dir, line, text, cwd, section):
        """Check one shell line. `cwd` is a root-relative dir or None when an
        earlier `cd` went somewhere uncheckable. Returns the new cwd."""
        for part in re.split(r"&&|\|\||;|\|", text):
            try:
                words = shlex.split(part, comments=True)
            except ValueError:
                words = part.split()
            while words and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", words[0]) or words[0] in ("sudo", "exec", "time")):
                words = words[1:]
            if not words:
                continue
            cmd, args = words[0], words[1:]
            if cmd == "cd":
                cwd = self._cd(cwd, args[0] if args else None)
                continue
            if cmd in INTERPRETERS:
                self._script(doc, line, cmd, args, cwd, section)
            elif cmd.startswith(("./", "../")) or ("/" in cmd and not cmd.startswith(("/", "~"))):
                if not _is_placeholder(cmd):
                    self._path_claim("D2", doc, line, cmd, cwd, section)
            elif cmd in ("npm", "pnpm", "yarn"):
                self._package_script(doc, doc_dir, line, cmd, args, cwd, section)
            elif cmd == "make":
                self._make(doc, line, args, cwd, section)
        return cwd

    def _cd(self, cwd, target):
        if cwd is None or not target or _is_placeholder(target) or target.startswith(("/", "~", "-")):
            return None
        joined = os.path.normpath(os.path.join(self.root, cwd, target))
        if not _inside(self.root, joined) or not os.path.isdir(joined):
            return None
        return os.path.relpath(joined, self.root)

    def _path_claim(self, rule, doc, line, path, cwd, section, claim=None):
        claim = claim or path
        if cwd is None:
            self.add(rule, doc, line, claim, NOT_CHECKED, "working directory unknown after `cd`", section)
            return
        status, detail = _exists(self.root, os.path.join(self.root, cwd), path)
        self.add(rule, doc, line, claim, status, detail, section)

    def _script(self, doc, line, cmd, args, cwd, section):
        for i, arg in enumerate(args):
            if arg in ("-m", "-c", "-e", "--eval", "-"):
                return  # a module or inline code, not a file
            if arg.startswith("-"):
                continue
            if _is_placeholder(arg) or not (SCRIPT_EXT.search(arg) or "/" in arg):
                return
            if arg.startswith(("/", "~")):
                return
            self._path_claim("D2", doc, line, arg, cwd, section, claim=f"{cmd} {arg}")
            return

    def _package_script(self, doc, doc_dir, line, cmd, args, cwd, section):
        if cmd == "npm":
            if args[:1] in (["run"], ["run-script"]) and len(args) > 1:
                name = args[1]
            elif args[:1] and args[0] in NPM_LIFECYCLE:
                name = args[0]
            else:
                return
        else:
            rest = args[1:] if args[:1] == ["run"] else args
            if not rest or rest[0] in PM_BUILTINS and args[:1] != ["run"]:
                return
            if rest[0].startswith("-"):
                self.add("D3", doc, line, f"{cmd} {' '.join(args)}", NOT_CHECKED,
                         "flags before the script name (workspace filter?) — not resolved", section)
                return
            name = rest[0]
        if _is_placeholder(name):
            return
        claim = f"{cmd} {'run ' if 'run' in args[:1] else ''}{name}"
        start = os.path.join(self.root, cwd) if cwd is not None else None
        if start is None:
            self.add("D3", doc, line, claim, NOT_CHECKED, "working directory unknown after `cd`", section)
            return
        pkg = self._nearest(start, "package.json")
        if pkg is None:
            self.add("D3", doc, line, claim, NOT_CHECKED, "no package.json at or above the working directory", section)
            return
        rel = os.path.relpath(pkg, self.root)
        try:
            scripts = json.loads(_read(pkg)).get("scripts")
        except (Unreadable, ValueError, AttributeError) as exc:
            self.add("D3", doc, line, claim, NOT_CHECKED, f"{rel} unreadable: {exc}", section)
            return
        if isinstance(scripts, dict) and name in scripts:
            self.add("D3", doc, line, claim, VERIFIED, f"{rel} scripts.{name}", section)
        else:
            self.add("D3", doc, line, claim, CONTRADICTED, f"{rel} has no scripts.{name}", section)

    def _nearest(self, start, name):
        current = os.path.normpath(start)
        while _inside(self.root, current):
            candidate = os.path.join(current, name)
            if os.path.isfile(candidate):
                return candidate
            if current == self.root:
                break
            current = os.path.dirname(current)
        return None

    def _make(self, doc, line, args, cwd, section):
        targets = []
        skip = False
        for arg in args:
            if skip:
                if cwd is not None:
                    cwd = self._cd(cwd, arg)
                skip = False
            elif arg == "-C":
                skip = True
            elif arg.startswith("-") or "=" in arg:
                continue
            else:
                targets.append(arg)
        targets = [t for t in targets if not _is_placeholder(t)]
        if not targets:
            return  # bare `make`: the default goal, no named claim
        makefile = None
        if cwd is not None:
            for name in ("GNUmakefile", "makefile", "Makefile"):
                candidate = os.path.join(self.root, cwd, name)
                if os.path.isfile(candidate):
                    makefile = candidate
                    break
        for target in targets:
            claim = f"make {target}"
            if makefile is None:
                why = "working directory unknown after `cd`" if cwd is None else "no Makefile in the working directory"
                self.add("D4", doc, line, claim, NOT_CHECKED, why, section)
                continue
            rel = os.path.relpath(makefile, self.root)
            try:
                text = _read(makefile)
            except Unreadable as exc:
                self.add("D4", doc, line, claim, NOT_CHECKED, f"{rel} unreadable: {exc}", section)
                continue
            found, includes, patterns = set(), False, False
            for mline in text.splitlines():
                if re.match(r"^-?s?include\s", mline):
                    includes = True
                m = MAKE_TARGET.match(mline)
                if m and not mline.startswith("\t"):
                    for name in m.group(1).split():
                        found.add(name)
                        patterns = patterns or "%" in name
            if target in found:
                self.add("D4", doc, line, claim, VERIFIED, f"{rel} defines {target}", section)
            elif includes or patterns:
                self.add("D4", doc, line, claim, NOT_CHECKED,
                         f"{rel} has includes or pattern rules — target may be defined elsewhere", section)
            else:
                self.add("D4", doc, line, claim, CONTRADICTED, f"{rel} has no target {target}", section)

    # D5 --------------------------------------------------------------------
    def check_env(self, doc, line, name, section):
        index = self._env_files()
        if index is None:
            self.add("D5", doc, line, name, NOT_CHECKED, "no readable non-doc file in the tree", section)
            return
        files, unreadable = index
        pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(name)}(?![A-Za-z0-9_])")
        for rel, text in files:
            for n, fline in enumerate(text.splitlines(), 1):
                if pattern.search(fline):
                    self.add("D5", doc, line, name, VERIFIED, f"referenced at {rel}:{n}", section)
                    return
        if unreadable:
            self.add("D5", doc, line, name, NOT_CHECKED,
                     f"not found, but {unreadable} file(s) could not be read", section)
        else:
            self.add("D5", doc, line, name, CONTRADICTED, "not referenced in any non-doc file", section)

    def _env_files(self):
        """(files, unreadable_count) of every non-doc text file, or None if none.
        `.env*` files are skipped by name and never opened."""
        if self._env_index is None:
            files, unreadable = [], 0
            for dirpath, dirnames, filenames in os.walk(self.root):
                dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
                for fname in sorted(filenames):
                    if fname.startswith(".env") or fname.lower().endswith(DOC_EXTS):
                        continue
                    full = os.path.join(dirpath, fname)
                    try:
                        if os.path.getsize(full) > 1_000_000:
                            continue
                        files.append((os.path.relpath(full, self.root), _read(full)))
                    except Unreadable:
                        unreadable += 1  # binary or unreadable
                    except OSError:
                        unreadable += 1
            self._env_index = (files, unreadable) if files else None
        return self._env_index

    # per document ----------------------------------------------------------
    def audit_doc(self, rel):
        full = os.path.join(self.root, rel)
        try:
            text = _read(full)
        except Unreadable as exc:
            self.add("DOC", rel, 0, rel, NOT_CHECKED, f"unreadable: {exc}", "")
            return
        doc_dir = os.path.dirname(full)
        lines = text.splitlines()
        per_line, unterminated = _blocks(lines)
        if unterminated is not None:
            self.add("DOC", rel, unterminated, rel, NOT_CHECKED,
                     "unterminated code fence — the rest of the file was not checked", "")
            lines = lines[:unterminated - 1]
        section, env_section, table_header = "", False, False
        cwd = ""
        for i in range(_frontmatter_end(lines), len(lines)):
            n, raw = i + 1, lines[i]
            block = per_line[i]
            if block is not None:
                info, delimiter = block
                if delimiter:
                    cwd = ""  # each fence starts at the repo root
                    continue
                if info in SHELL_INFO:
                    cmd = raw.strip()
                    if info == "console" or info == "terminal":
                        if not cmd.startswith(("$ ", "> ")):
                            continue  # output line
                    cmd = re.sub(r"^(\$|>|PS>)\s+", "", cmd)
                    if cmd:
                        cwd = self.check_command(rel, doc_dir, n, cmd, cwd, section)
                continue
            heading = HEADING.match(raw)
            if heading:
                section = heading.group(2)
                env_section = bool(ENV_HEADING.search(section))
                continue
            # D5: first cell of a table row under an env/config heading.
            if env_section and raw.lstrip().startswith("|"):
                first = raw.strip().strip("|").split("|")[0].strip()
                span = re.fullmatch(r"`([^`]+)`", first)
                if span and ENV_NAME.match(span.group(1)):
                    self.check_env(rel, n, span.group(1), section)
            spans = list(CODE_SPAN.finditer(raw))
            for span in spans:
                content = span.group(2).strip()
                if PATH_TOKEN.match(content):
                    self.check_backtick_path(rel, doc_dir, n, content, section)
                elif re.match(r"^(npm|pnpm|yarn|make)\s", content):
                    # Inline spans feed D3/D4 only: a `bash x.sh` in prose is
                    # as often an illustration as an instruction.
                    self.check_command(rel, doc_dir, n, content, "", section)
            prose = CODE_SPAN.sub("", raw)
            for link in LINK.finditer(prose):
                self.check_link(rel, doc_dir, n, link.group(1), section)


def _scope(root, paths):
    if not paths:
        found = [p for p in DEFAULT_SCOPE if os.path.isfile(os.path.join(root, p))]
        paths = found + (["docs"] if os.path.isdir(os.path.join(root, "docs")) else [])
    docs, missing = [], []
    for p in paths:
        full = os.path.normpath(os.path.join(root, p))
        rel = os.path.relpath(full, root)
        if os.path.isdir(full):
            for dirpath, dirnames, filenames in os.walk(full):
                dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
                docs += [os.path.relpath(os.path.join(dirpath, f), root)
                         for f in sorted(filenames) if f.lower().endswith(".md")]
        elif os.path.isfile(full):
            docs.append(rel)
        else:
            missing.append(rel)
    return sorted(dict.fromkeys(docs)), missing


def run(root, paths=()):
    audit = Audit(root)
    docs, missing = _scope(audit.root, list(paths))
    for rel in missing:
        audit.add("DOC", rel, 0, rel, NOT_CHECKED, "requested path does not exist", "")
    for rel in docs:
        audit.audit_doc(rel)
    summary = {s: 0 for s in (VERIFIED, CONTRADICTED, NOT_CHECKED)}
    by_rule = {}
    for claim in audit.claims:
        summary[claim["status"]] += 1
        by_rule.setdefault(claim["rule"], {s: 0 for s in summary})[claim["status"]] += 1
    return {"root": audit.root, "files": docs, "summary": summary,
            "by_rule": by_rule, "claims": audit.claims}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", help="audited tree (default: git top-level of the cwd)")
    parser.add_argument("paths", nargs="*", help="Markdown files or directories, relative to --root")
    args = parser.parse_args(argv)
    root = args.root
    if root is None:
        result = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
        if result.returncode != 0:
            print("could not run: not inside a git repository and no --root given", file=sys.stderr)
            return 2
        root = result.stdout.strip()
    if not os.path.isdir(root):
        print(f"could not run: --root {root} is not a directory", file=sys.stderr)
        return 2
    report = run(root, args.paths)
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 1 if report["summary"][CONTRADICTED] else 0


if __name__ == "__main__":
    sys.exit(main())
