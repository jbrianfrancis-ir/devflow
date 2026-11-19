#!/usr/bin/env python3
"""Opt-in usage report: transcribed tokens, duration and outcomes per role and phase.

Off unless `.planning/config.json` has `"usage_report": true`; off, the report prints one
line saying so and reads nothing else, and `record` refuses. Records live in the
frontmatter of the artifacts a run already writes, never in a separate log.

Provenance. Every value is TRANSCRIBED: the orchestrator copies it from host or bridge
output into frontmatter, and nothing here can check that the copy matches what the host
printed. Only `flow-agent.py` measures anything in code — a claude-cli dispatch's tokens,
and every bridge dispatch's duration_ms and outcome — and those still reach the artifact
through the orchestrator. Neither the Agent tool's `<usage>` nor a Codex native spawn is
measured by DevFlow at all.

Record shape — one JSON line in frontmatter, `usage: [{...}, ...]`, one object per agent
dispatch: executor dispatches in that plan's `NN-MM-SUMMARY.md` (phase dirs, and
`.planning/quick/` as phase `quick`), verifier dispatches in the phase's `VERIFICATION.md`.
Only those two roles are instrumented; every other bridge role renders `not instrumented`.

  role         "executor" in a SUMMARY, "verifier" in a VERIFICATION.md — nothing else
  n            1, 2, ... — this dispatch's ordinal for that unit; a unit's list is 1..k
  source       where the numbers came from; each defines tokens its own way:
                 agent-tool    Claude native Agent tool `<usage>`: `subagent_tokens`,
                               `duration_ms` as the host printed them
                 claude-cli    the bridge's `usage` object (modelUsage summed, all models)
                 codex-cli     the bridge's `usage` object (no tokens observed)
                 codex-native  Codex native spawn: nothing observed
  provider     "claude" | "codex" | "unknown"
  model        the model the dispatch REQUESTED, or "unknown" when none was passed; the
               tokens may include other models (nested agents, host-side helpers)
  tokens       int >= 0, or "unknown"
  duration_ms  int >= 0, or "unknown"
  outcome      the dispatch's result status as printed: "completed" | "checkpoint" |
               "failed" | "unknown" (bridge: its `usage.outcome`; Agent tool: the
               result block's status line). Retries are not labelled: a unit with more
               dispatches than one, after a failed or checkpoint outcome, is the signal.

A value that was not observed is "unknown" (an absent key means the same); a real 0 stays
0. Nothing else is accepted — no extra keys, no free text: every value is an enum or an
integer except `model`, which must be id-shaped (<= 64 chars, no segment over 16, at most
4 word-like segments), so no prompt sentence or credential-length token fits; a few
hyphenated words still would, which the outgoing-diff secret scan also covers. A
malformed record exits 2 naming the file.

Writing: `record` is the only writer. It validates the record, requires `n` to be the
unit's next ordinal (a repeat exits 2 and changes nothing, so re-running a step never
counts a dispatch twice), and rewrites the file atomically. `--content` replaces the
file's body with the given file (a re-verification's fresh VERIFICATION.md) and carries
the earlier records forward, so earlier verifier attempts are never dropped. Record a
dispatch at the first durable point after it returns (see the skills); a record held only
in conversation is lost on interruption or compaction, and is never rebuilt from memory.

Coverage. Units are found on disk: each phase dir's `NN-MM-PLAN.md`/`NN-MM-SUMMARY.md`
names are its executor units (a plan with no SUMMARY counts as not recorded), its
verification is one verifier unit, and each quick SUMMARY is one executor unit (quick
plans have no fixed name, and quick runs no verifier). A unit with no `usage` line is
`not recorded`: its dispatch count and every value are unknown, it is never folded into
a total, and every row for that role and phase shows `Coverage k/n` so a sum over the k
recorded units never reads as the whole phase. A role with no unit at all (executor and
verifier of a phase dir with no plans yet) renders `no unit`. Tokens are summed only within one
source (grouped by it); a sum over values where some are unknown renders
`partial: <sum of known> (<known>/<total> known)`, all unknown renders `unknown`. Duration
is summed per dispatch, so parallel work sums past wall-clock time.

Usage: flow-usage.py --repo PATH [--phase ID]        (ID: a phase dir prefix, or quick)
       flow-usage.py record --file ARTIFACT --record JSON [--content FILE]
       flow-usage.py trail --repo PATH --session JSONL_OR_ID   (see `trail --help`)
Stdlib only. Exit codes: 0 rendered, recorded, or disabled; 2 bad config, malformed or
refused record.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import sys
import tempfile

UNKNOWN = "unknown"
NOT_RECORDED = "not recorded"
NOT_INSTRUMENTED = "not instrumented"
NO_UNIT = "no unit"
OUTCOMES = ("completed", "checkpoint", "failed")
SOURCES = {"agent-tool", "claude-cli", "codex-cli", "codex-native"}
PROVIDERS = {"claude", "codex", UNKNOWN}
KEYS = ("role", "n", "source", "provider", "model", "tokens", "duration_ms", "outcome")
REQUIRED = {"role", "n", "source"}
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@\[\]-]{0,63}$")
SEGMENT_RE = re.compile(r"[._:/@\[\]-]+")


class RecordError(Exception):
    pass


def bridge_roles() -> list[str]:
    """The role names the bridge dispatches — one source of truth, not a copy."""
    spec = importlib.util.spec_from_file_location(
        "flow_agent", Path(__file__).resolve().parent / "flow-agent.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return sorted(module.ALL_ROLES)


def enabled(planning: Path, key: str = "usage_report") -> bool:
    path = planning / "config.json"
    if not path.is_file():
        return False
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecordError(f"{path}: unreadable config ({exc})")
    if not isinstance(config, dict) or key not in config:
        return False
    if not isinstance(config[key], bool):
        raise RecordError(f"{path}: {key} must be true or false, got {config[key]!r}")
    return config[key]


def role_for(path: Path) -> str | None:
    """The one role an artifact may carry records for."""
    if path.name.endswith("-SUMMARY.md"):
        return "executor"
    if path.name == "VERIFICATION.md":
        return "verifier"
    return None


def bounds(lines: list[str]) -> tuple[int, int] | None:
    """Line indices of the opening and closing `---` of the frontmatter."""
    start = next((i for i, line in enumerate(lines) if line.strip() == "---"), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() == "---"), None)
    return (start, end) if end is not None else None


def usage_line(lines: list[str]) -> int | None:
    span = bounds(lines)
    if span is None:
        return None
    return next((i for i in range(span[0] + 1, span[1]) if lines[i].startswith("usage:")),
                None)


def count(value: object, where: str, key: str) -> int | str:
    if value == UNKNOWN:
        return UNKNOWN
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RecordError(f"{where}: {key} must be an integer >= 0 or \"unknown\", "
                          f"got {value!r}")
    return value


def model_id(value: object) -> bool:
    """An id-shaped model name: <= 64 chars, no segment over 16 (no credential-length
    token), at most 4 word-like segments (no sentence). Real ids fit: `sonnet`,
    `claude-sonnet-4-5@20250929`, `us.anthropic.claude-sonnet-4-5-20250929-v1:0`."""
    if not isinstance(value, str) or not MODEL_RE.match(value):
        return False
    segments = [part for part in SEGMENT_RE.split(value) if part]
    words = [part for part in segments if part.isalpha() and len(part) >= 3]
    return all(len(part) <= 16 for part in segments) and len(words) <= 4


def check(record: object, where: str, role: str) -> dict:
    if not isinstance(record, dict):
        raise RecordError(f"{where}: a record must be an object")
    extra = set(record) - set(KEYS)
    if extra:
        raise RecordError(f"{where}: keys not allowed in a usage record: {sorted(extra)}")
    missing = REQUIRED - set(record)
    if missing:
        raise RecordError(f"{where}: missing {sorted(missing)}")
    n = record["n"]
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise RecordError(f"{where}: n must be an integer >= 1, got {n!r}")
    if record["role"] != role:
        raise RecordError(f"{where}: role {record['role']!r} does not belong here "
                          f"(this artifact carries {role} records only)")
    if record["source"] not in SOURCES:
        raise RecordError(f"{where}: unknown source {record['source']!r}")
    provider = record.get("provider", UNKNOWN)
    if provider not in PROVIDERS:
        raise RecordError(f"{where}: unknown provider {provider!r}")
    model = record.get("model", UNKNOWN)
    if model != UNKNOWN and not model_id(model):
        raise RecordError(f"{where}: model must be a model name or \"unknown\", got {model!r}")
    outcome = record.get("outcome", UNKNOWN)
    if outcome not in OUTCOMES + (UNKNOWN,):
        raise RecordError(f"{where}: outcome must be one of {list(OUTCOMES) + [UNKNOWN]}, "
                          f"got {outcome!r}")
    return {"role": role, "n": n, "source": record["source"], "provider": provider,
            "model": model, "tokens": count(record.get("tokens", UNKNOWN), where, "tokens"),
            "duration_ms": count(record.get("duration_ms", UNKNOWN), where, "duration_ms"),
            "outcome": outcome}


def parse_usage(path: Path, lines: list[str]) -> list[dict] | None:
    """The artifact's validated records, or None when it has no `usage` line."""
    role = role_for(path)
    index = usage_line(lines)
    if index is None or role is None:
        return None
    try:
        entries = json.loads(lines[index].partition(":")[2])
    except json.JSONDecodeError as exc:
        raise RecordError(f"{path}: usage is not one JSON list ({exc.msg})")
    if not isinstance(entries, list) or not entries:
        raise RecordError(f"{path}: usage must be a non-empty JSON list")
    records = [check(entry, f"{path} usage[{i}]", role) for i, entry in enumerate(entries)]
    ordinals = [r["n"] for r in records]
    if ordinals != list(range(1, len(records) + 1)):
        raise RecordError(f"{path}: usage ordinals must run 1..{len(records)} in order, got "
                          f"{ordinals} — a duplicate would be counted twice, a gap hides one")
    return records


# --- report ------------------------------------------------------------------

def units(planning: Path) -> dict[str, dict[str, list[tuple[str, Path | None]]]]:
    """{phase: {role: [(unit label, artifact or None when absent)]}} for every phase dir
    (planned-but-unexecuted ones included) and the quick tasks, in phase order."""
    found: dict[str, dict[str, list]] = {}
    phases = planning / "phases"
    if phases.is_dir():
        for directory in sorted(p for p in phases.iterdir() if p.is_dir()):
            phase = directory.name.split("-", 1)[0]
            plans = sorted({p.name.removesuffix("-PLAN.md")
                            for p in directory.glob("*-PLAN.md")}
                           | {p.name.removesuffix("-SUMMARY.md")
                              for p in directory.glob("*-SUMMARY.md")})
            entry = found.setdefault(phase, {"executor": [], "verifier": []})
            for plan in plans:
                summary = directory / f"{plan}-SUMMARY.md"
                entry["executor"].append((plan, summary if summary.is_file() else None))
            verification = directory / "VERIFICATION.md"
            if plans or verification.is_file():  # a phase with no plans expects no verify
                entry["verifier"].append(("VERIFICATION",
                                          verification if verification.is_file() else None))
    quick = planning / "quick"
    summaries = sorted(quick.glob("*-SUMMARY.md")) if quick.is_dir() else []
    if summaries:
        found["quick"] = {"executor": [(p.name.removesuffix("-SUMMARY.md"), p)
                                       for p in summaries], "verifier": []}
    return found


def collect(planning: Path, phase_filter: str | None):
    """(records, coverage, unrecorded): records tagged with their phase; coverage
    {(phase, role): (recorded units, expected units)}; unrecorded unit labels."""
    found = units(planning)
    if phase_filter is not None:
        if phase_filter not in found:
            raise RecordError(f"no phase {phase_filter!r} under .planning "
                              "(use the phase dir's prefix, e.g. 03, or quick)")
        found = {phase_filter: found[phase_filter]}
    records, coverage, unrecorded = [], {}, []
    for phase, roles in found.items():
        for role, entries in roles.items():
            recorded = 0
            for unit, path in entries:
                parsed = None
                if path is not None:
                    parsed = parse_usage(path, path.read_text(encoding="utf-8").splitlines())
                if parsed is None:
                    why = f"no {'SUMMARY' if role == 'executor' else 'VERIFICATION.md'}" \
                        if path is None else "no usage line"
                    unrecorded.append(f"{phase}/{unit} ({why})")
                    continue
                recorded += 1
                records += [{**r, "phase": phase} for r in parsed]
            coverage[(phase, role)] = (recorded, len(entries))
    return records, coverage, unrecorded, list(found)


def total(values: list) -> str:
    known = [v for v in values if v != UNKNOWN]
    if not known:
        return UNKNOWN
    if len(known) == len(values):
        return str(sum(known))
    return f"partial: {sum(known)} ({len(known)}/{len(values)} known)"


def outcomes(group: list[dict]) -> str:
    seen = [r["outcome"] for r in group]
    if all(o == UNKNOWN for o in seen):
        return UNKNOWN
    return ", ".join(f"{o} {seen.count(o)}" for o in OUTCOMES + (UNKNOWN,) if o in seen)


def cells(group: list[dict]) -> list[str]:
    return [str(len(group)), outcomes(group), total([r["tokens"] for r in group]),
            total([r["duration_ms"] for r in group])]


BLANK = [UNKNOWN] * 4


def coverage_cell(recorded: int, expected: int) -> str:
    return NO_UNIT if expected == 0 else f"{recorded}/{expected} recorded"


def rows_for(prefix: list[str], group_key, width: int, records: list[dict], recorded: int,
             expected: int) -> list[list[str]]:
    """Rows for one instrumented role: one per recorded group (`width` key cells, source
    last), then one for the units with no record. Every row carries the same coverage, so
    a sum over the recorded units never reads as the whole."""
    cov = coverage_cell(recorded, expected)
    groups: dict[tuple, list[dict]] = {}
    for record in records:
        groups.setdefault(group_key(record), []).append(record)
    out = [prefix + [cov] + list(key) + cells(group) for key, group in groups.items()]
    lead = prefix + [cov] + [UNKNOWN] * (width - 1)
    if expected > recorded:
        out.append(lead + [NOT_RECORDED, f"{UNKNOWN} ({expected - recorded} not recorded)"]
                   + BLANK[1:])
    elif expected == 0:
        out.append(lead + ["none"] + BLANK)
    return out


def markdown(headers: tuple[str, ...], rows: list[list[str]]) -> list[str]:
    return (["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
            + ["| " + " | ".join(row) + " |" for row in rows])


VALUES = ("Dispatches", "Outcomes", "Tokens", "Duration ms (sum)")
HEADER = (
    "Transcribed, not verified: every value was copied by the orchestrator from host "
    "output (the Agent tool's `<usage>`) or the bridge's `usage` object into artifact "
    "frontmatter; this report checks shape, not truth. Only `flow-agent.py` measures in "
    "code (claude-cli tokens; bridge duration and outcome), and those are transcribed too. "
    "`unknown` = not observed or not recorded; `0` = observed zero; `partial: N (k/n known)` "
    "sums the k known values of n. `Coverage k/n` = units with records; `not instrumented` "
    "= DevFlow records nothing for that role. Tokens are never summed across sources. "
    "Model = the model requested. Definitions: `flow-usage.py --help`.")


def render(records, coverage, unrecorded, phases, roles) -> str:
    out = ["## Usage (transcribed)", "", HEADER, ""]
    if not phases:
        return "\n".join(out + ["No phase dirs or quick SUMMARYs found."]) + "\n"
    by_phase = []
    for phase in phases:
        for role in roles:
            if (phase, role) not in coverage:
                by_phase.append([phase, role, NOT_INSTRUMENTED, "none"] + BLANK)
                continue
            mine = [r for r in records if r["phase"] == phase and r["role"] == role]
            by_phase += rows_for([phase, role], lambda r: (r["source"],), 1, mine,
                                 *coverage[(phase, role)])
    out += ["### By phase and role", ""]
    out += markdown(("Phase", "Role", "Coverage", "Source") + VALUES, by_phase)
    by_model = []
    for role in roles:
        keys = [k for k in coverage if k[1] == role]
        if not keys:
            by_model.append([role, NOT_INSTRUMENTED, UNKNOWN, UNKNOWN, "none"] + BLANK)
            continue
        mine = sorted((r for r in records if r["role"] == role),
                      key=lambda r: (r["provider"], r["model"], r["source"]))
        by_model += rows_for([role], lambda r: (r["provider"], r["model"], r["source"]), 3,
                             mine, sum(coverage[k][0] for k in keys),
                             sum(coverage[k][1] for k in keys))
    out += ["", "### By role and requested model", ""]
    out += markdown(("Role", "Coverage", "Provider", "Requested model", "Source") + VALUES,
                    by_model)
    if unrecorded:
        out += ["", "Not recorded (not in any total): " + ", ".join(unrecorded)]
    return "\n".join(out) + "\n"


# --- record ------------------------------------------------------------------

def planning_of(path: Path) -> Path:
    for parent in path.parents:
        if parent.name == ".planning":
            return parent
    raise RecordError(f"{path}: not under a .planning directory")


def write_atomic(path: Path, text: str) -> None:
    handle, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.remove(temp)
        raise


def record(path: Path, raw: str, content: Path | None) -> str:
    path = path.resolve()
    if not enabled(planning_of(path)):
        raise RecordError("usage_report is off in .planning/config.json; nothing recorded")
    role = role_for(path)
    if role is None:
        raise RecordError(f"{path}: records go in a *-SUMMARY.md or a VERIFICATION.md")
    try:
        new = check(json.loads(raw), "--record", role)
    except json.JSONDecodeError as exc:
        raise RecordError(f"--record is not JSON ({exc.msg})")
    existing = path.read_text(encoding="utf-8").splitlines() if path.is_file() else None
    if content is None and existing is None:
        raise RecordError(f"{path}: no such artifact to record into")
    carried = (parse_usage(path, existing) or []) if existing is not None else []
    lines = content.read_text(encoding="utf-8").splitlines() if content else existing
    if content is not None and usage_line(lines) is not None:
        raise RecordError(f"{content}: already has a usage line; an agent cannot observe "
                          "its own usage, and earlier records come from the file it replaces")
    if new["n"] != len(carried) + 1:
        raise RecordError(f"{path}: {role} n={new['n']} refused — this unit holds "
                          f"{len(carried)} record(s), so the next is n={len(carried) + 1}; "
                          "nothing written")
    span = bounds(lines)
    if span is None:
        raise RecordError(f"{content or path}: no frontmatter to record into")
    value = "usage: " + json.dumps(carried + [new])
    index = usage_line(lines)
    if index is None:
        lines = lines[:span[1]] + [value] + lines[span[1]:]
    else:
        lines[index] = value
    write_atomic(path, "\n".join(lines) + "\n")
    return f"recorded {role} n={new['n']} in {path}"


# --- trail -------------------------------------------------------------------

TRAIL_DOC = """Session trail: what one Claude Code session read, ran, edited and handed to helpers.

Opt-in twice: `.planning/config.json` needs "usage_report": true AND "usage_trail": true.
Otherwise it prints one line and reads nothing else (a non-boolean value exits 2).
Read-only: it reads the saved transcript and prints to stdout; it writes no file.

Input. --session is a transcript .jsonl path, or a session id resolved under
~/.claude/projects/*/<id>.jsonl. Helper transcripts are read from
<transcript dir>/<session id>/subagents/agent-<agentId>.jsonl and matched to their
Agent/Task call by the call result's `agentId`, or by `toolUseId` in agent-*.meta.json; a
helper matched by neither reads "transcript not found". The main transcript's
isSidechain lines are skipped (they belong to helpers). A line that is not a JSON object
is skipped and counted; unknown line types are ignored.

Output, in order:
  1. Summary, three lines: steps by kind across the session and its helpers; models
     seen and model changes; helpers with their own step counts, shell reads found as
     second evidence, and steps stopped by a rule.
  2. Step by step, one numbered row per tool call in transcript order: Read/Glob/Grep =
     read; Bash = command (first line, cut at 100 chars); Edit/Write/MultiEdit/
     NotebookEdit = edit; mcp__<server>__<tool> = MCP, opaque; Agent/Task = gave work to
     Helper N; any other tool is listed by name. A "model changed" row marks a step whose
     assistant message model differs from the previous step's (`<synthetic>` ignored).
     A step whose result carries toolDenialKind "permission-rule" (or, in older
     transcripts, an error saying permission was denied or the call was blocked) reads
     "stopped by a rule in your settings"; toolDenialKind "user-rejected" reads
     "declined at the permission prompt".
  3. Helper handoffs: per helper, its subagent_type and description, the models it ran
     on, the exact `prompt` it was given (verbatim, indented), and its own steps; a
     helper's helpers nest as N.1, N.2.
  4. Second evidence: each Bash command is split (shlex) on |, &&, ||, ;, & and newlines;
     a segment whose program is one of SHELL_READERS, or python/python3 -c with
     open('<literal path>'), adds "read (via shell, second evidence)" for each operand
     that is a regular file NOW, relative to that line's cwd or absolute. sed/awk/grep/rg
     skip their first operand (the script/pattern) unless -e/-f gave it. It only adds
     reads; a command it cannot tokenize adds none.
  5. Limits.

Every path is shown the same way; nothing is classified or scored.
"""

SHELL_READERS = {"cat", "head", "tail", "less", "more", "sed", "awk", "grep", "rg", "nl",
                 "bat", "wc", "cut", "sort", "uniq", "strings", "xxd", "od"}
SCRIPT_FIRST = {"sed", "awk", "grep", "rg"}
PYTHON_RE = re.compile(r"^python(3(\.\d+)?)?$")
HEREDOC_RE = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
OPEN_RE = re.compile(r"""open\(\s*(['"])([^'"]+)\1""")
READ_TOOLS = {"Read", "Glob", "Grep"}
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
HELPER_TOOLS = {"Agent", "Task"}
SEPARATORS = {"|", "||", "&&", ";", "&", ";;", "|&"}
RULE = "stopped by a rule in your settings"
DECLINED = "declined at the permission prompt"
DENIED_RE = re.compile(r"permission.*\b(denied|not granted|haven't granted)\b|\bblocked\b",
                       re.IGNORECASE | re.DOTALL)
LIMITS = ("Limits: this shows what was written and done, not the reasoning behind it; "
          "helpers that ran in parallel have no ordering between them; it cannot show "
          "which files an MCP tool opened.")


def load_lines(path: Path) -> tuple[list[dict], int]:
    """The transcript's JSON-object lines, and how many lines were skipped."""
    lines, skipped = [], 0
    with path.open(encoding="utf-8", errors="replace") as stream:
        for raw in stream:
            if not raw.strip():
                continue
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                value = None
            if isinstance(value, dict):
                lines.append(value)
            else:
                skipped += 1
    return lines, skipped


def result_text(block: dict) -> str:
    content = block.get("content")
    if isinstance(content, list):
        return " ".join(c.get("text", "") for c in content if isinstance(c, dict))
    return str(content or "")


def stop_reason(block: dict, denial: object) -> str | None:
    if denial == "permission-rule":
        return RULE
    if denial == "user-rejected":
        return DECLINED
    text = result_text(block)
    if block.get("is_error") and not text.startswith("Exit code") and DENIED_RE.search(text):
        return RULE
    return None


def parse_trace(path: Path, main: bool) -> dict:
    """{steps, skipped}: one step per tool_use, in order, with its model, result and
    the cwd recorded on its line (else the transcript's first)."""
    lines, skipped = load_lines(path)
    steps, seen, results, cwd = [], set(), {}, None
    model = None
    for line in lines:
        if main and line.get("isSidechain") is True:
            continue
        cwd = cwd or line.get("cwd")
        message = line.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        if line.get("type") == "assistant":
            if isinstance(message.get("model"), str) and message["model"] != "<synthetic>":
                model = message["model"]
            for block in content:
                if (isinstance(block, dict) and block.get("type") == "tool_use"
                        and block.get("id") not in seen):
                    seen.add(block.get("id"))
                    steps.append({"id": block.get("id"), "name": str(block.get("name")),
                                  "input": block.get("input") if isinstance(
                                      block.get("input"), dict) else {},
                                  "model": model, "cwd": line.get("cwd") or cwd})
        elif line.get("type") == "user":
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    results[block.get("tool_use_id")] = (
                        stop_reason(block, line.get("toolDenialKind")),
                        line.get("toolUseResult"))
    for step in steps:
        step["stopped"], step["result"] = results.get(step["id"], (None, None))
    return {"steps": steps, "skipped": skipped}


def kind(name: str) -> str:
    if name in READ_TOOLS:
        return "read"
    if name == "Bash":
        return "command"
    if name in EDIT_TOOLS:
        return "edit"
    if name.startswith("mcp__"):
        return "MCP"
    if name in HELPER_TOOLS:
        return "helper"
    return "other"


def first_line(text: str, width: int = 100) -> str:
    lines = text.strip().splitlines() or [""]
    line = lines[0]
    if len(line) > width:
        return line[:width - 1] + "…"
    return line + (" …" if len(lines) > 1 else "")


def describe(step: dict, label: str | None) -> str:
    name, args = step["name"], step["input"]
    k = kind(name)
    if k == "read":
        if name == "Read":
            return f"read      {args.get('file_path', '?')}"
        where = f" in {args['path']}" if args.get("path") else ""
        return f"read      {name.lower()} {args.get('pattern', '?')}{where}"
    if k == "command":
        return f"command   {first_line(str(args.get('command', '')))}"
    if k == "edit":
        return f"edit      {args.get('file_path') or args.get('notebook_path') or '?'}"
    if k == "MCP":
        server, _, tool = name[len("mcp__"):].partition("__")
        return f"MCP       {server}.{tool} — opaque: the transcript cannot show what this tool touched"
    if k == "helper":
        return f"gave work to Helper {label}"
    return f"other     {name}"


def operands(tokens: list[str]) -> list[str]:
    """File operands of one shell segment, or [] when it is not a known reader."""
    while tokens and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0]):
        tokens = tokens[1:]  # leading VAR=value assignments
    if not tokens:
        return []
    program = os.path.basename(tokens[0])
    if PYTHON_RE.match(program):
        if "-c" not in tokens[1:-1]:
            return []
        return [m.group(2) for m in OPEN_RE.finditer(tokens[tokens.index("-c") + 1])]
    if program not in SHELL_READERS:
        return []
    found, skip_next = [], False
    for token in tokens[1:]:
        if skip_next:
            skip_next = False
        elif set(token) <= set("<>&0123456789") and (">" in token or "<<" in token):
            skip_next = True  # a write target or heredoc delimiter, not a read
        elif not token.startswith("-") and token != "<":
            found.append(token)
    script_given = any(t in ("-e", "-f") or re.match(r"^-[a-zA-Z]*[ef]$", t)
                       for t in tokens[1:])
    if program in SCRIPT_FIRST and not script_given and found:
        found = found[1:]
    return found


def shell_reads(command: str, cwd: str | None) -> list[str]:
    kept, end = [], None
    for line in command.replace("\\\n", " ").splitlines():
        if end is not None:  # a heredoc body is data, not commands
            end = None if line.strip() == end else end
            continue
        kept.append(line)
        heredoc = HEREDOC_RE.search(line)
        end = heredoc.group(2) if heredoc else None
    try:
        lexer = shlex.shlex(" ; ".join(kept), posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return []
    reads, segment = [], []
    for token in tokens + [";"]:
        if token not in SEPARATORS:
            segment.append(token)
            continue
        for operand in operands(segment):
            path = Path(operand) if os.path.isabs(operand) or cwd is None \
                else Path(cwd) / operand
            if path.is_file() and operand not in reads:
                reads.append(operand)
        segment = []
    return reads


def helper_files(subagents: Path) -> dict[str, Path]:
    """{tool_use id or agentId: helper transcript} from the files on disk."""
    found: dict[str, Path] = {}
    if not subagents.is_dir():
        return found
    for transcript in subagents.glob("agent-*.jsonl"):
        found[transcript.stem.removeprefix("agent-")] = transcript
        meta = transcript.with_name(transcript.stem + ".meta.json")
        try:
            tool_use = json.loads(meta.read_text(encoding="utf-8")).get("toolUseId")
        except (OSError, json.JSONDecodeError, AttributeError):
            tool_use = None
        if isinstance(tool_use, str):
            found[tool_use] = transcript
    return found


def build(path: Path, files: dict[str, Path], label: str, main: bool, seen: set) -> dict:
    """A trace with its helpers attached recursively; `label` is "" for the session."""
    seen.add(path)
    trace = parse_trace(path, main)
    trace["label"], trace["helpers"] = label, []
    for step in trace["steps"]:
        step["evidence"] = shell_reads(str(step["input"].get("command", "")), step["cwd"]) \
            if step["name"] == "Bash" else []
        if kind(step["name"]) != "helper":
            continue
        number = f"{label}.{len(trace['helpers']) + 1}" if label else \
            str(len(trace["helpers"]) + 1)
        result = step["result"] if isinstance(step["result"], dict) else {}
        transcript = files.get(str(result.get("agentId"))) or files.get(step["id"])
        child = None
        if transcript is not None and transcript not in seen:
            child = build(transcript, files, number, False, seen)
        step["helper"] = number
        trace["helpers"].append({"label": number, "step": step, "trace": child})
    return trace


def walk(trace: dict):
    yield trace
    for helper in trace["helpers"]:
        if helper["trace"] is not None:
            yield from walk(helper["trace"])


def changes(trace: dict) -> list[tuple[str, str]]:
    models = [s["model"] for s in trace["steps"] if s["model"]]
    return [(a, b) for a, b in zip(models, models[1:]) if a != b]


def all_helpers(trace: dict):
    for helper in trace["helpers"]:
        yield helper
        if helper["trace"] is not None:
            yield from all_helpers(helper["trace"])


def helper_type(helper: dict) -> str:
    args = helper["step"]["input"]
    return str(args.get("subagent_type") or "general-purpose")


def summary(root: dict) -> list[str]:
    traces = list(walk(root))
    steps = [s for t in traces for s in t["steps"]]
    counts = {k: sum(1 for s in steps if kind(s["name"]) == k)
              for k in ("read", "command", "edit", "MCP", "helper", "other")}
    by_kind = (f"reads {counts['read']}, commands {counts['command']}, edits "
               f"{counts['edit']}, MCP calls {counts['MCP']}, helpers {counts['helper']}")
    if counts["other"]:
        by_kind += f", other tools {counts['other']}"
    models = list(dict.fromkeys(s["model"] for s in steps if s["model"]))
    helpers = [f"Helper {h['label']} ({helper_type(h)}) "
               + (f"{len(h['trace']['steps'])} steps" if h["trace"] else "transcript not found")
               for h in all_helpers(root)]
    evidence = sum(len(s["evidence"]) for s in steps)
    stopped = sum(1 for s in steps if s["stopped"] == RULE)
    return [f"Steps: {len(steps)} — {by_kind} (session and helpers)",
            f"Models: {', '.join(models) or 'unknown'}; model changes: "
            f"{sum(len(changes(t)) for t in traces)}",
            f"Helpers: {'; '.join(helpers) or 'none'}. Shell reads found as second "
            f"evidence: {evidence}. Steps stopped by a rule: {stopped}"]


def step_rows(trace: dict, indent: str) -> list[str]:
    steps = trace["steps"]
    first = next((s["model"] for s in steps if s["model"]), None)
    rows = [f"{indent}Model: {first or 'unknown'}"]
    previous = first
    for number, step in enumerate(steps, 1):
        if step["model"] and previous and step["model"] != previous:
            rows.append(f"{indent}     model changed: {previous} → {step['model']}")
        previous = step["model"] or previous
        row = f"{indent}{number:>3}. {describe(step, step.get('helper'))}"
        if step["stopped"]:
            row += f" — {step['stopped']}"
        rows.append(row)
    if not steps:
        rows.append(f"{indent}(no tool steps)")
    return rows


def handoffs(trace: dict, indent: str) -> list[str]:
    out = []
    for helper in trace["helpers"]:
        args = helper["step"]["input"]
        head = f"{indent}Helper {helper['label']} — {helper_type(helper)}"
        if args.get("description"):
            head += f": {args['description']}"
        out.append(head)
        child = helper["trace"]
        if child is not None:
            models = list(dict.fromkeys(s["model"] for s in child["steps"] if s["model"]))
            note = "; model changed while it worked" if changes(child) else ""
            out.append(f"{indent}  Models: {', '.join(models) or 'unknown'}{note}")
        out.append(f"{indent}  Task given (verbatim):")
        out += [f"{indent}      {line}" for line in str(args.get("prompt", "")).splitlines()]
        if child is None:
            out.append(f"{indent}  Steps: transcript not found")
        else:
            out.append(f"{indent}  Steps:")
            out += step_rows(child, indent + "    ")
            out += handoffs(child, indent + "    ")
        out.append("")
    return out


def trail(root: dict) -> str:
    out = ["## Session trail (read-only)", ""] + summary(root)
    out += ["", "### Step by step", ""] + step_rows(root, "")
    out += ["", "### Helper handoffs", ""] + (handoffs(root, "") or ["none", ""])
    out += ["### Second evidence (reads found inside shell commands)", ""]
    evidence = [f"read (via shell, second evidence)  {path}  — from "
                + (f"Helper {t['label']} " if t["label"] else "") + f"step {n}"
                for t in walk(root) for n, s in enumerate(t["steps"], 1)
                for path in s["evidence"]]
    out += evidence or ["none found"]
    skipped = sum(t["skipped"] for t in walk(root))
    out += ["", LIMITS + (f" Skipped {skipped} unreadable transcript line(s)."
                          if skipped else "")]
    return "\n".join(out) + "\n"


def resolve_session(value: str) -> Path:
    path = Path(value).expanduser()
    if value.endswith(".jsonl"):
        if not path.is_file():
            raise RecordError(f"{value}: no such transcript")
        return path.resolve()
    if not re.fullmatch(r"[A-Za-z0-9._-]+", value):
        raise RecordError(f"{value!r}: not a .jsonl path or a session id")
    matches = sorted((Path.home() / ".claude/projects").glob(f"*/{value}.jsonl"))
    if len(matches) != 1:
        raise RecordError(f"session {value}: {len(matches)} transcripts under "
                          "~/.claude/projects (need exactly 1; pass the .jsonl path)")
    return matches[0]


def trail_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="flow-usage.py trail", description=TRAIL_DOC,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True, help="repository root (holds .planning/)")
    parser.add_argument("--session", required=True,
                        help="transcript .jsonl path, or a session id")
    args = parser.parse_args(argv)
    planning = Path(args.repo).resolve() / ".planning"
    try:
        report_on, trail_on = enabled(planning), enabled(planning, "usage_trail")
        if not (report_on and trail_on):
            print("session trail: disabled — set \"usage_report\": true and "
                  "\"usage_trail\": true in .planning/config.json to enable it")
            return 0
        session = resolve_session(args.session)
        root = build(session, helper_files(session.parent / session.stem / "subagents"),
                     "", True, set())
    except (RecordError, OSError) as exc:
        print(f"flow-usage: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(trail(root))
    return 0


def main() -> int:
    if sys.argv[1:2] == ["trail"]:
        return trail_main(sys.argv[2:])
    if sys.argv[1:2] == ["record"]:
        parser = argparse.ArgumentParser(prog="flow-usage.py record")
        parser.add_argument("--file", required=True, help="the SUMMARY or VERIFICATION.md")
        parser.add_argument("--record", required=True, help="one record, as JSON")
        parser.add_argument("--content", help="replace the file's body with this file, "
                                              "carrying its earlier records forward")
        args = parser.parse_args(sys.argv[2:])
        try:
            print(record(Path(args.file), args.record,
                         Path(args.content) if args.content else None))
        except (RecordError, OSError) as exc:
            print(f"flow-usage: {exc}", file=sys.stderr)
            return 2
        return 0
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True, help="repository root (holds .planning/)")
    parser.add_argument("--phase", help="only this phase: a phase dir prefix, or quick")
    args = parser.parse_args()
    planning = Path(args.repo).resolve() / ".planning"
    try:
        if not enabled(planning):
            print("usage report: disabled — set \"usage_report\": true in "
                  ".planning/config.json to record and report usage")
            return 0
        records, coverage, unrecorded, phases = collect(planning, args.phase)
    except RecordError as exc:
        print(f"flow-usage: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(render(records, coverage, unrecorded, phases, bridge_roles()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
