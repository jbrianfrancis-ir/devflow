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
0. Nothing else is accepted — no extra keys, no free text — so no prompt, message content
or secret can ride along in a record. A malformed record exits 2 naming the file.

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
recorded units never reads as the whole phase. A role with no unit at all (the executor of
a phase dir with no plans yet) renders `no unit`. Tokens are summed only within one
source (grouped by it); a sum over values where some are unknown renders
`partial: <sum of known> (<known>/<total> known)`, all unknown renders `unknown`. Duration
is summed per dispatch, so parallel work sums past wall-clock time.

Usage: flow-usage.py --repo PATH [--phase ID]        (ID: a phase dir prefix, or quick)
       flow-usage.py record --file ARTIFACT --record JSON [--content FILE]
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
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@\[\]-]{0,199}$")


class RecordError(Exception):
    pass


def bridge_roles() -> list[str]:
    """The role names the bridge dispatches — one source of truth, not a copy."""
    spec = importlib.util.spec_from_file_location(
        "flow_agent", Path(__file__).resolve().parent / "flow-agent.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return sorted(module.ALL_ROLES)


def enabled(planning: Path) -> bool:
    path = planning / "config.json"
    if not path.is_file():
        return False
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RecordError(f"{path}: unreadable config ({exc})")
    if not isinstance(config, dict) or "usage_report" not in config:
        return False
    if not isinstance(config["usage_report"], bool):
        raise RecordError(f"{path}: usage_report must be true or false, "
                          f"got {config['usage_report']!r}")
    return config["usage_report"]


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
    if not isinstance(model, str) or not (model == UNKNOWN or MODEL_RE.match(model)):
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


def main() -> int:
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
