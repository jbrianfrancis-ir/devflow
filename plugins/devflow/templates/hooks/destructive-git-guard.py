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


CHECKS = {"push": check_push, "reset": check_reset, "clean": check_clean, "branch": check_branch}


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


def main():
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError) as exc:
        warn(f"could not parse stdin JSON: {exc}")
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
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
