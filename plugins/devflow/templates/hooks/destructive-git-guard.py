#!/usr/bin/env python3
"""PreToolUse (Bash) guard: block git commands that throw away work or rewrite shared history,
on any branch. It turns the rule "never force-push, and nothing destructive in git without a
human" (autonomy.md human gates, conventions.md) into a check that holds even if an agent
ignores its written instructions.

Blocked (exit 2, reason on stderr):
  git push --force | -f (also inside a short-flag group such as -uf) | --force-with-lease[=...]
  git push <remote> +<refspec>       a leading '+' force-updates that ref
  git reset --hard
  git clean -f | --force (also -fd, -xdf, ...), unless -n/--dry-run is present
  git branch -D | --delete --force | -d -f (also -df)
  git checkout . | -- . | <tree> -- .  any pathspec that is exactly `.` or `:/`
  git restore . | --worktree .         same pathspecs; --staged/-S alone (unstaging only) passes

`--force-with-lease` is blocked too. It only protects against overwriting commits you have not
fetched; it still rewrites the remote branch, and "never force-push" has no lease exception. A
human who needs any of these runs it in their own terminal, outside the agent.

How it reads the command: the Bash string is split into simple commands on `;`, `&`, `|`, `&&`,
`||`, newlines and `$(`/backtick boundaries, and each is tokenized with shlex. Leading
`VAR=value` assignments and the wrappers `sudo`, `command`, `env`, `exec`, `nice`, `time` are
skipped; `git` may be a path (`/usr/bin/git`). git's own global options (`-C <path>`,
`-c <k=v>`, `--git-dir=...`, `--no-pager`, ...) are skipped to find the subcommand. The text
after `bash -c`, `sh -c`, `zsh -c` and `eval` is scanned the same way. It cannot see through a
script file, a Makefile target or a git alias; docs/hooks.md lists those limits.

This guard needs no git repo and reads no config, so it has no infrastructure failure to fail
open on. On an unexpected internal error it fails open (exit 0) with a warning on stderr, the
same as the other DevFlow guards: it is a backstop, not the only control.

The idea of a destructive-git block list comes from Matt Pocock's git-guardrails-claude-code
skill (concept only; no code from it is used).

It also blocks `gh pr create` whose body has no line
`Merge Danger: LOW|MEDIUM|HIGH — one-way|two-way door; blast radius: ...` (flow-pr's section).
The body comes from the last `--body`/`-b`, or `--body-file`/`-F` <path> (the only file this
guard ever reads); with `-F -` it is searched for in the command text itself (a heredoc).
`--fill`, `--template`, `--web` or no body at all is blocked with the same message.
"""
import json
import os
import re
import shlex
import sys

NAME = "destructive-git-guard"

# Splits a command line into simple commands. Quotes are respected by tokenizing each piece
# afterwards; a separator inside quotes can over-split, which only ever adds a scan.
SEPARATOR_RE = re.compile(r"\|\||&&|[;&|\n]|\$\(|`|\)")

WRAPPERS = {"sudo", "command", "env", "exec", "nice", "time", "nohup"}
SHELLS = {"bash", "sh", "zsh", "dash"}
ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

# git global options that consume the next token as their value.
GIT_GLOBAL_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace",
                         "--exec-path", "--super-prefix", "--config-env"}

# push options that consume the next token as their value (so it is not read as a refspec).
PUSH_WITH_VALUE = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}

# A pathspec that covers the whole working tree: checkout/restore with it discards every
# uncommitted change at once.
WHOLE_TREE = {".", ":/"}
CHECKOUT_WITH_VALUE = {"-b", "-B", "--orphan"}
RESTORE_WITH_VALUE = {"-s", "--source"}


def warn(message):
    print(f"{NAME}: {message}", file=sys.stderr)


def tokenize(segment):
    try:
        return shlex.split(segment, comments=True)
    except ValueError:
        # Unbalanced quotes, usually from a separator split inside a quoted string. A plain
        # split with the quote characters dropped still finds the words.
        return [word.strip("\"'") for word in segment.split() if word.strip("\"'")]


def simple_commands(command):
    for piece in SEPARATOR_RE.split(command):
        tokens = tokenize(piece)
        if tokens:
            yield tokens


def strip_prefix(tokens):
    """Drop leading assignments and wrapper commands (with their own leading options)."""
    i = 0
    while i < len(tokens):
        word = tokens[i]
        if ASSIGNMENT_RE.match(word):
            i += 1
        elif os.path.basename(word) in WRAPPERS:
            i += 1
            while i < len(tokens) and tokens[i].startswith("-"):
                i += 1
        else:
            break
    return tokens[i:]


def git_subcommand(tokens):
    """(subcommand, args) when tokens run git, else None."""
    if not tokens or os.path.basename(tokens[0]) not in ("git", "git.exe"):
        return None
    i = 1
    while i < len(tokens):
        word = tokens[i]
        if word in GIT_GLOBAL_WITH_VALUE:
            i += 2
        elif word.startswith("-"):
            i += 1
        else:
            return word, tokens[i + 1:]
    return None


def short_flags(word):
    """The letters of a short-option group (`-uf` -> "uf"); empty for anything else."""
    if word.startswith("-") and not word.startswith("--") and len(word) > 1:
        return word[1:]
    return ""


def check_push(args):
    i = 0
    while i < len(args):
        word = args[i]
        if word == "--":
            positional = args[i + 1:]
            break
        if word in PUSH_WITH_VALUE:
            i += 2
            continue
        if word == "--force" or word.startswith("--force-with-lease"):
            return f"git push {word.split('=')[0]}"
        letters = short_flags(word)
        if letters:
            for letter in letters:
                if letter == "o":  # -o<value>: the rest is the option's value
                    break
                if letter == "f":
                    return f"git push {word}"
        elif not word.startswith("-") and word.startswith("+"):
            return f"git push with force refspec '{word}'"
        i += 1
    else:
        positional = []
    for word in positional:
        if word.startswith("+"):
            return f"git push with force refspec '{word}'"
    return None


def check_reset(args):
    return "git reset --hard" if "--hard" in args else None


def check_clean(args):
    options = [a for a in args if a.startswith("-")]
    letters = "".join(short_flags(a).split("e")[0] for a in options)
    if "--dry-run" in options or "n" in letters:
        return None
    if "--force" in options or "f" in letters:
        return "git clean -f"
    return None


def check_branch(args):
    letters = "".join(short_flags(a) for a in args)
    if "D" in letters:
        return "git branch -D"
    deleting = "--delete" in args or "d" in letters
    forcing = "--force" in args or "f" in letters
    if deleting and forcing:
        return "git branch --delete --force"
    return None


def pathspecs(args, with_value):
    """Non-option words, plus every word after `--`."""
    found = []
    i = 0
    while i < len(args):
        word = args[i]
        if word == "--":
            return found + args[i + 1:]
        if word in with_value:
            i += 2
            continue
        if not word.startswith("-"):
            found.append(word)
        i += 1
    return found


def check_checkout(args):
    if WHOLE_TREE & set(pathspecs(args, CHECKOUT_WITH_VALUE)):
        return "git checkout ."
    return None


def check_restore(args):
    if not WHOLE_TREE & set(pathspecs(args, RESTORE_WITH_VALUE)):
        return None
    staged = worktree = False
    for word in args:
        if word == "--":
            break
        if word == "--staged":
            staged = True
        elif word == "--worktree":
            worktree = True
        for letter in short_flags(word):
            if letter == "s":  # -s<tree>: the rest is the option's value
                break
            staged = staged or letter == "S"
            worktree = worktree or letter == "W"
    if staged and not worktree:
        return None
    return "git restore ."


CHECKS = {"push": check_push, "reset": check_reset, "clean": check_clean, "branch": check_branch,
          "checkout": check_checkout, "restore": check_restore}


def find_destructive(command, depth=0):
    """The first destructive git operation in a Bash command string, or None."""
    if depth > 3:
        return None
    for tokens in simple_commands(command):
        tokens = strip_prefix(tokens)
        if not tokens:
            continue
        head = os.path.basename(tokens[0])
        if head in SHELLS and "-c" in tokens[1:]:
            idx = tokens.index("-c", 1)
            if idx + 1 < len(tokens):
                # Everything after -c: the script, plus any $0/$1 words (harmless to scan).
                hit = find_destructive(" ".join(tokens[idx + 1:]), depth + 1)
                if hit:
                    return hit
            continue
        if head == "eval":
            hit = find_destructive(" ".join(tokens[1:]), depth + 1)
            if hit:
                return hit
            continue
        parsed = git_subcommand(tokens)
        if parsed is None:
            continue
        subcommand, args = parsed
        check = CHECKS.get(subcommand)
        hit = check(args) if check else None
        if hit:
            return hit
    return None


GH_PR_CREATE_RE = re.compile(r"\bgh\s+pr\s+create\b")
MERGE_DANGER_RE = re.compile(
    r"Merge Danger:\s*(LOW|MEDIUM|HIGH)(?=[^\n]*\b(one|two)-way\b)(?=[^\n]*blast radius)")
MERGE_DANGER_MSG = ("PR body needs: 'Merge Danger: LOW|MEDIUM|HIGH — one-way|two-way door; "
                    "blast radius: <what breaks>'")
BODY_FLAGS = {"--body": "text", "-b": "text", "--body-file": "file", "-F": "file"}


def gh_pr_create_args(command):
    """The argument list of each `gh pr create` in the command (quotes respected, so a body
    containing `;` or newlines stays one word)."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()\n")
    lexer.whitespace, lexer.whitespace_split, lexer.commenters = " \t\r", True, ""
    current = []
    for token in list(lexer) + [";"]:
        if token and set(token) <= set(";&|()\n"):
            tokens = strip_prefix(current)
            if tokens and os.path.basename(tokens[0]) == "gh" and tokens[1:3] == ["pr", "create"]:
                yield tokens[3:]
            current = []
        else:
            current.append(token)


def pr_body(args, cwd):
    """(kind, value) of the last body flag, or None. kind is "text", "file" or "stdin"."""
    found = None
    for i, word in enumerate(args):
        flag, sep, value = word.partition("=")
        if flag not in BODY_FLAGS and word[:2] in ("-b", "-F") and len(word) > 2:
            flag, sep, value = word[:2], "=", word[2:]  # -bTEXT / -Fpath
        if flag in BODY_FLAGS:
            if not sep:
                value = args[i + 1] if i + 1 < len(args) else ""
            found = (BODY_FLAGS[flag], value)
    if found and found == ("file", "-"):
        return ("stdin", "")
    if found and found[0] == "file":
        try:
            with open(os.path.join(cwd, found[1]), encoding="utf-8", errors="replace") as stream:
                return ("text", stream.read(1_000_000))
        except OSError:
            return ("text", "")
    return found


def merge_danger_missing(command, cwd):
    """True when a `gh pr create` in the command lacks a Merge Danger line in its body."""
    try:
        creates = list(gh_pr_create_args(command))
    except ValueError:  # unbalanced quotes, e.g. an apostrophe in an unquoted heredoc
        creates = [["-F", "-"]] if GH_PR_CREATE_RE.search(command) else []
    for args in creates:
        body = pr_body(args, cwd)
        text = command if body and body[0] == "stdin" else (body or ("", ""))[1]
        if not MERGE_DANGER_RE.search(text):
            return True
    return False


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as exc:
        warn(f"could not parse stdin JSON: {exc}")
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    if GH_PR_CREATE_RE.search(command) and merge_danger_missing(
            command, payload.get("cwd") or os.getcwd()):
        print(MERGE_DANGER_MSG, file=sys.stderr)
        return 2
    if "git" not in command:
        return 0
    hit = find_destructive(command)
    if hit:
        print(
            f"Blocked: {hit} discards work or rewrites history. DevFlow never runs it without a "
            "human: push normally, use `git revert` or a new commit instead, or ask the human to "
            "run it in their own terminal.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # fail open, loud — never a silent pass
        warn(f"unexpected error: {exc}")
        sys.exit(0)
