#!/usr/bin/env python3
"""PreToolUse (Bash) guard: block a `git commit`/`git push` whose diff contains an added line
matching conventions.md's secret-pattern class, hardening the "secret scan every commit and
push" hard rule so it holds even if an agent ignores its written instructions.

This is a best-effort backstop layered on top of the still-primary agent-instruction control,
not the sole safety net — so it follows two different rules depending on WHY a check didn't
happen:

- Environmental failure (no git repo, no HEAD, unreadable config, the `git` call itself
  failed) — the guard could not run at all, and the primary agent-instruction control still
  stands. These cases fail open (exit 0) with a clear warning on stderr, never a silent pass.
- A diff git DID produce but this parser could NOT read into file chunks — the guard ran,
  examined the outgoing change, and understood none of it. That is different in kind: it is
  "could not check", and conventions.md's fail-closed guard rule means could-not-check must
  never read as clean. This case fails CLOSED (exit 2/BLOCK), same as a real hit.

Only a human clears a real hit or a could-not-check block; this script never does more than
block and name the pattern class (or the parse failure).
"""
import fnmatch
import json
import os
import re
import signal
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _hook_common as common  # noqa: E402

# Kept byte-identical to the pattern in conventions.md's "Secret scan (fail-closed)" section —
# tests/test_flow_hooks.py asserts this constant matches that file's fenced pattern, so the two
# copies cannot drift silently.
SECRET_PATTERN = r"""-----BEGIN [A-Z ]*PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{20,}|xox[baprs]-[A-Za-z0-9-]{10,}|eyJhbGciOi[A-Za-z0-9_-]{20,}|(password|passwd|secret|token|api[_-]?key|connection[_-]?string)["' ]*[=:] *["'][^"']{8,}["']|(password|passwd|secret|token|api[_-]?key|connection[_-]?string)["' ]*[=:] *[A-Za-z0-9+/=_-]{16,} *$"""

SECRET_RE = re.compile(SECRET_PATTERN)

# Any added line in one of these is a hit regardless of content (except the two named exceptions).
CREDENTIAL_FILE_GLOBS = (".env*", "*.pem", "*.pfx", "*.key", "id_rsa*")
CREDENTIAL_FILE_EXCEPTIONS = {".env.example", ".env.template"}

# Splits a `git diff` into per-file sections — the delimiter git emits for every file in a
# diff, text or binary, added, modified, renamed, or deleted.
DIFF_GIT_HEADER_RE = re.compile(r"^diff --git a/.* b/(.*)$")

# Config overrides and diff-shape flags applied to EVERY `git diff` invocation in this file
# (there are three: HEAD, --cached fallback, and the push range), via run_git_diff() below —
# the only way any of them should ever be invoked. Without this, a user's
# `diff.mnemonicPrefix`/`diff.noprefix` config (or an external diff driver) silently changes
# the output shape DIFF_GIT_HEADER_RE depends on, iter_file_chunks yields zero chunks, and the
# guard used to exit 0 (allow) with no warning — reproduced live, this was the actual bug.
# Belt and braces, deliberately: the `-c` overrides neutralise the config regardless of what
# set it, and the explicit `--src-prefix`/`--dst-prefix` pin the output shape independent of
# any future git default change.
#
# The rest close the *other* ways config and `.gitattributes` defeat this scan. They split
# into two kinds that fail in opposite directions, both verified live:
#   fail-OPEN (a real secret passes) — `--no-ext-diff` (an external driver replaces the
#   output wholesale), `--text` (a path marked `-diff` renders as "Binary files differ", so
#   the chunk parses fine and its added lines are simply never scanned), `--no-textconv` (a
#   textconv filter rewrites content before the scan sees it), `--no-relative`
#   (`diff.relative` with a subdirectory cwd hides files above it).
#   fail-CLOSED-wrongly (every commit blocked) — `--no-color` (`color.ui=always` wraps the
#   header in escapes, nothing matches, COULD_NOT_PARSE fires on a clean tree: this bricked
#   commits outright), `--submodule=short` (`diff.submodule=log` renders a pointer bump with
#   no `diff --git` header at all).
# A guard that blocks everything is not safer than one that blocks nothing — it just gets
# turned off. Both directions belong here.
#
# `--text` makes git emit raw bytes for a binary file, so every `git` call below decodes with
# errors="replace": strict UTF-8 raised UnicodeDecodeError on any real .pfx/.pem, which landed
# in the "could not compute diff" path and FAILED OPEN — a worse hole than the one --text
# closes. Replacement characters cost nothing here: the credential-filename rule keys off the
# path, and a credential worth catching is ASCII where it matters.
GIT_DIFF_FORMAT_ARGS = (
    "-c", "diff.mnemonicPrefix=false",
    "-c", "diff.noprefix=false",
    "diff",
    "--no-ext-diff",
    "--no-color",
    "--no-textconv",
    "--no-relative",
    "--text",
    "--submodule=short",
    "--src-prefix=a/",
    "--dst-prefix=b/",
)

# Sentinel distinct from None: diff_text was non-empty but iter_file_chunks() found no file
# chunks in it — the guard could not read what git gave it. main() must treat this as
# could-not-check (BLOCK), never collapse it into "nothing found" (clean).
COULD_NOT_PARSE = object()

# `.planning/ARCHITECTURE.md`'s `## Forbidden` section (syntax: templates/architecture.md) —
# a bullet may end with " <dash> pattern: `<regex>`". Matched with a plain string for the
# dash rather than a literal em-dash in source, so the character survives any editor/encoding
# round-trip untouched.
FORBIDDEN_DASH = "—"
FORBIDDEN_SECTION_RE = re.compile(r"^##\s+Forbidden\s*$")
FORBIDDEN_HEADER_RE = re.compile(r"^##\s+")
FORBIDDEN_BULLET_RE = re.compile(r"^\s*[-*]\s+(.*)$")  # indented sub-bullets count too
FORBIDDEN_SUFFIX_RE = re.compile(
    r"^(?P<prose>.*?)\s+" + re.escape(FORBIDDEN_DASH) + r"\s*pattern:\s*(?P<raw>.+)$"
)


def iter_forbidden_entries(text):
    """Yield (prose, raw_pattern) for each bullet under ARCHITECTURE.md's `## Forbidden`
    section. raw_pattern is None for a bullet with no `pattern:` suffix — prose-only, and
    correctly left unenforced by the caller."""
    in_section = False
    for line in text.splitlines():
        if FORBIDDEN_HEADER_RE.match(line):
            in_section = bool(FORBIDDEN_SECTION_RE.match(line.strip()))
            continue
        if not in_section:
            continue
        bullet = FORBIDDEN_BULLET_RE.match(line)
        if not bullet:
            continue
        body = bullet.group(1)
        suffix = FORBIDDEN_SUFFIX_RE.match(body)
        if not suffix:
            yield body.strip(), None
            continue
        raw = suffix.group("raw").strip()
        if len(raw) >= 2 and raw[0] == "`" and raw[-1] == "`":
            raw = raw[1:-1]
        yield suffix.group("prose").strip(), raw


# The file that DECLARES the patterns. Its own Forbidden bullets contain the literals they
# forbid, so matching declared patterns against it makes any plain-literal entry match its own
# declaration and block every commit in the repo — verified, and the only escape is deleting
# the entry, i.e. turning the control off. Excluded from the Forbidden pass only; the credential
# scan still applies to it in full.
FORBIDDEN_DECL_PATH = os.path.join(".planning", "ARCHITECTURE.md")

# A declared regex is repo-controlled text and Python `re` has no timeout, so a nested-quantifier
# pattern like `(a+)+$` hangs the guard on every commit forever. Bound the whole Forbidden pass
# with a wall-clock deadline and treat expiry as could-not-check (BLOCK) — a guard that hangs is
# not fail-closed, it is a guard nobody can commit past and therefore one that gets removed.
FORBIDDEN_MATCH_BUDGET_SECONDS = 2.0


class ForbiddenBudgetExceeded(Exception):
    pass


class forbidden_budget:
    """SIGALRM-based deadline around the Forbidden matching. Unix-only by design: these hooks
    run under a POSIX shell. Where setitimer is unavailable the budget is simply not applied —
    reported to the caller so it is never mistaken for having been enforced."""

    def __init__(self, seconds):
        self.seconds = seconds
        self.armed = False

    def __enter__(self):
        if not hasattr(signal, "SIGALRM") or not hasattr(signal, "setitimer"):
            return self
        def fire(_signum, _frame):
            raise ForbiddenBudgetExceeded()
        self.previous = signal.signal(signal.SIGALRM, fire)
        signal.setitimer(signal.ITIMER_REAL, self.seconds)
        self.armed = True
        return self

    def __exit__(self, *exc):
        if self.armed:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, self.previous)
        return False


def repo_root(cwd, warn):
    """The repo root, not the hook's cwd.

    `.planning/ARCHITECTURE.md` lives at the root. Reading it relative to cwd meant running git
    from any subdirectory silently disabled the entire Forbidden check while the credential scan
    still fired — the same cwd-relative bypass class `--no-relative` closes for the diff.
    Returns None when the root cannot be resolved; the caller treats that as could-not-check.
    """
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, errors="replace", timeout=30,
        )
    except OSError as exc:
        warn(f"could not resolve repo root from {cwd}: {exc}")
        return None
    if result.returncode != 0:
        return None
    root = result.stdout.strip()
    return root or None


def load_forbidden_patterns(cwd, warn):
    """Read `.planning/ARCHITECTURE.md`'s Forbidden bullets and compile each declared regex
    as DATA (`re.compile`) — never interpolated into a shell command.

    Returns (patterns, could_not_check):
    - patterns: [(prose, compiled_re), ...] for entries that carry a valid regex. A bullet
      with no `pattern:` suffix is excluded here — silently, by design, since it stays
      prose-only guidance and is not enforced.
    - could_not_check: None on success. Otherwise a human-readable reason naming what could
      not be read or compiled — the caller must BLOCK on this, never fall back to treating it
      as "no patterns declared". A missing ARCHITECTURE.md is NOT this case: most repos have
      none, and that means "no patterns declared", not "could not read the ones that exist".
    """
    root = repo_root(cwd, warn)
    if root is None:
        # Not a git repo at all is handled by the caller's existing fail-open path; a repo
        # whose root cannot be resolved is could-not-check.
        if os.path.isdir(os.path.join(cwd, ".git")):
            return [], f"could not resolve the repo root from {cwd}"
        return [], None
    path = os.path.join(root, FORBIDDEN_DECL_PATH)
    if not os.path.isfile(path):
        return [], None
    try:
        with open(path, "r", encoding="utf-8") as stream:
            text = stream.read()
    except OSError as exc:
        return [], f"could not read {path}: {exc}"

    patterns = []
    for prose, raw in iter_forbidden_entries(text):
        if raw is None:
            continue
        try:
            patterns.append((prose, re.compile(raw)))
        except re.error as exc:
            return [], f"malformed regex on Forbidden entry {prose!r} in {path}: {exc}"
    return patterns, None


def run_git_diff(cwd, *extra_args):
    """Run `git diff` with GIT_DIFF_FORMAT_ARGS pinned ahead of whatever this call site needs
    (a revision range, -U0, --cached, ...). The only way any `git diff` call in this file
    should be built — a fourth call site that assembles its own argv reopens the
    config-dependent-output bug GIT_DIFF_FORMAT_ARGS exists to close."""
    return subprocess.run(
        ["git", "-C", cwd, *GIT_DIFF_FORMAT_ARGS, *extra_args],
        capture_output=True, text=True, errors="replace", timeout=30,
    )

# Git always emits this line for a deletion (text or binary) — used to tell "this file's
# content is going away" apart from "this file's content is arriving", so a credential-shaped
# file's deletion (remediation) never trips the same rule that catches its arrival.
DELETED_FILE_RE = re.compile(r"^deleted file mode\b")

# `@@ -a,b +c,d @@` — group 1 is the first line number in the NEW file, which is what a
# reader needs to find the hit. Only the new-side number matters here.
HUNK_HEADER_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")

GIT_ADD_RE = re.compile(r"\bgit\s+add\b")


def warn(message):
    print(f"secret-scan-guard: {message}", file=sys.stderr)


def is_forbidden_declaration_file(path):
    """True for the ARCHITECTURE.md that declares the patterns — see FORBIDDEN_DECL_PATH."""
    return os.path.normpath(path) == os.path.normpath(FORBIDDEN_DECL_PATH)


def is_credential_file(path):
    name = os.path.basename(path)
    if name in CREDENTIAL_FILE_EXCEPTIONS:
        return False
    return any(fnmatch.fnmatch(name, pattern) for pattern in CREDENTIAL_FILE_GLOBS)


def diff_for(command, cwd, warn):
    if re.search(r"\bgit\s+commit\b", command):
        # `git diff HEAD` (working tree vs HEAD) covers staged AND unstaged changes to
        # tracked files in one shot — unlike `--cached` alone, it still sees what `git
        # commit -a`/`-am`/`--all` would commit even though nothing is staged yet.
        result = run_git_diff(cwd, "HEAD", "-U0")
        if result.returncode != 0:
            # No HEAD yet (first commit in the repo) — HEAD doesn't exist, fall back to
            # the index-vs-empty-tree diff, which works with zero commits.
            result = run_git_diff(cwd, "--cached", "-U0")
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or "git diff failed")
        return result.stdout
    if re.search(r"\bgit\s+push\b", command):
        base = common.resolve_diff_base(cwd, warn)
        if base is None:
            return None
        result = run_git_diff(cwd, f"{base}...HEAD", "-U0")
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "git diff failed")
        return result.stdout
    return None


def iter_file_chunks(diff_text):
    """Yield (file_path, chunk_lines) per file section of a `git diff` — everything from one
    `diff --git` header up to (not including) the next, or EOF. One pass over line-tracking
    state, so the per-file rules below don't have to reconstruct it themselves."""
    chunk_path = None
    chunk_lines = []
    for line in diff_text.splitlines():
        header = DIFF_GIT_HEADER_RE.match(line)
        if header:
            if chunk_path is not None:
                yield chunk_path, chunk_lines
            chunk_path = header.group(1)
            chunk_lines = []
            continue
        chunk_lines.append(line)
    if chunk_path is not None:
        yield chunk_path, chunk_lines


def scan(diff_text, forbidden_patterns=()):
    """Return (file, pattern_class) for the first hit, COULD_NOT_PARSE if diff_text is
    non-empty but yielded no file chunks, or None if the diff is genuinely clean.

    `forbidden_patterns` is the compiled `[(prose, regex), ...]` list from
    load_forbidden_patterns() — applied to the same added lines the secret pattern already
    scans, via the same per-line loop, so a Forbidden-regex hit is reported through the exact
    same (file, pattern_class) hit path as a credential hit. pattern_class for a Forbidden
    hit is the entry's prose text, never the matched literal.

    The credential-filename rule ("any added line in one of these is a hit regardless of
    content") is evaluated per file, not per line: a credential-shaped file being added or
    modified is a hit even with zero `+`/`+++` lines to inspect (a binary file, or a newly
    added empty one) — but a credential-shaped file being *deleted* is remediation, not a
    hit, regardless of how its removal happens to render in the diff.
    """
    chunks = list(iter_file_chunks(diff_text))
    if not chunks:
        # A non-empty diff that produced zero file chunks means this parser did not
        # understand what git gave it — could-not-check, never clean. An actually-empty
        # diff (nothing changed) has no chunks either, and IS genuinely clean.
        return COULD_NOT_PARSE if diff_text.strip() else None
    for file_path, lines in chunks:
        is_deletion = any(DELETED_FILE_RE.match(line) for line in lines)
        if not is_deletion and is_credential_file(file_path):
            # No line number: the rule is about the path, not a line in it.
            return file_path, None, "credential-shaped filename"
        # Track the line number in the NEW file so a hit can be reported as file:line,
        # which conventions.md's reporting rule has always specified. `@@ -a,b +c,d @@`
        # gives the starting line; every `+` line advances it, every context line too.
        line_no = 0
        for line in lines:
            hunk = HUNK_HEADER_RE.match(line)
            if hunk:
                line_no = int(hunk.group(1))
                continue
            if line.startswith("\\ "):
                continue  # `\ No newline at end of file` is not a line of the file
            if line.startswith("-"):
                continue
            if not line.startswith("+"):
                line_no += 1
                continue
            if line.startswith("+++"):
                continue
            content = line[1:]
            if SECRET_RE.search(content):
                return file_path, line_no, "secret pattern"
            if forbidden_patterns and not is_forbidden_declaration_file(file_path):
                for prose, pattern in forbidden_patterns:
                    if pattern.search(content):
                        return file_path, line_no, prose
            line_no += 1
    return None


def untracked_files(cwd):
    result = subprocess.run(
        ["git", "-C", cwd, "ls-files", "--others", "--exclude-standard"],
        capture_output=True, text=True, errors="replace", timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git ls-files failed")
    return [line for line in result.stdout.splitlines() if line]


def scan_untracked_candidate(cwd, rel_path, forbidden_patterns=()):
    if is_credential_file(rel_path):
        return rel_path, None, "credential-shaped filename"
    try:
        with open(os.path.join(cwd, rel_path), "rb") as stream:
            data = stream.read(1_000_000)  # cap — a secret worth catching is near the top
    except OSError:
        return None
    if b"\x00" in data:
        return None  # binary content with no credential-shaped name; nothing safe to regex
    for number, line in enumerate(data.decode("utf-8", errors="ignore").splitlines(), 1):
        if SECRET_RE.search(line):
            return rel_path, number, "secret pattern"
        for prose, pattern in forbidden_patterns:
            if pattern.search(line):
                return rel_path, number, prose
    return None


def scan_new_untracked_files(command, cwd, warn, forbidden_patterns=()):
    """Hit for a not-yet-tracked file this exact chained command might stage and commit in
    one Bash call (`git add newfile && git commit ...`) — a diff against HEAD or the index
    can never see this, since the file has no history to diff against yet.

    Deliberately conservative: rather than compute exactly which untracked files a `git add`
    invocation would stage — defeated, verified live, by a glob (`git add *.pem`), a shell
    variable (`git add $F`), `-C`/an env-var prefix, or the add and commit landing in separate
    newline-separated statements of the same command — scan every currently untracked file
    whenever the command contains `git add` at all. A false positive (flagging an untracked
    file this particular add wouldn't actually stage) costs less than the bypass a narrower,
    cleverer match kept reopening.
    """
    if not GIT_ADD_RE.search(command):
        return None
    try:
        untracked = untracked_files(cwd)
    except Exception as exc:
        warn(f"could not list untracked files in {cwd}: {exc}")
        return None
    for rel_path in sorted(untracked):
        hit = scan_untracked_candidate(cwd, rel_path, forbidden_patterns)
        if hit:
            return hit
    return None


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

    # ARCHITECTURE.md's Forbidden-regex entries are could-not-check, not clean, when they
    # can't be read or compiled — checked before either scan path below, since neither one
    # can prove the outgoing change is safe while a declared pattern is unknown.
    forbidden_patterns, forbidden_could_not_check = load_forbidden_patterns(cwd, warn)
    if forbidden_could_not_check is not None:
        print(
            "Blocked: could-not-check — .planning/ARCHITECTURE.md's Forbidden entries could "
            f"not be read: {forbidden_could_not_check}. could-not-check never reads as safe "
            "to commit or push; fix the entry (or the file's readability) and rerun.",
            file=sys.stderr,
        )
        return 2

    hit = None
    if re.search(r"\bgit\s+commit\b", command):
        try:
            hit = scan_new_untracked_files(command, cwd, warn, forbidden_patterns)
        except Exception as exc:
            warn(f"could not scan untracked files in {cwd}: {exc}")
            hit = None

    if hit is None:
        try:
            diff_text = diff_for(command, cwd, warn)
        except Exception as exc:
            warn(f"could not compute diff in {cwd}: {exc}")
            return 0

        if diff_text is None:
            return 0

        try:
            with forbidden_budget(FORBIDDEN_MATCH_BUDGET_SECONDS):
                hit = scan(diff_text, forbidden_patterns)
        except ForbiddenBudgetExceeded:
            print(
                "Blocked: an ARCHITECTURE.md Forbidden regex did not finish within "
                f"{FORBIDDEN_MATCH_BUDGET_SECONDS:g}s — could-not-check, which never reads as "
                "safe. A pattern with nested quantifiers (e.g. `(a+)+`) backtracks "
                "catastrophically; simplify the declared regex.",
                file=sys.stderr,
            )
            return 2

    if hit is None:
        return 0

    if hit is COULD_NOT_PARSE:
        print(
            "Blocked: could not parse the outgoing diff into file chunks — this is "
            "could-not-check, not clean, and could-not-check never reads as safe to commit "
            "or push. Inspect `git diff` yourself before proceeding. The prefix, color, "
            "textconv, ext-diff and submodule config that used to cause this are all pinned "
            "by this guard, so the likely remaining cause is a path git C-quotes in the "
            "header (non-ASCII or control characters in a filename).",
            file=sys.stderr,
        )
        return 2

    file_name, line_no, pattern_class = hit
    where = f"{file_name}:{line_no}" if line_no else file_name
    print(
        f"Blocked: possible secret in {where} (pattern: {pattern_class}) — "
        "remove/rotate before committing.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail open, loud — never a silent pass
        warn(f"unexpected error: {exc}")
        sys.exit(0)
