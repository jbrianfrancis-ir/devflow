#!/usr/bin/env python3
"""Render the opt-in observed usage report: tokens, duration and retries per role and phase.

Off unless `.planning/config.json` has `"usage_report": true`; off, this prints one line
saying so and reads nothing else. It only reads: records live in the frontmatter of the
artifacts a run already writes, never in a separate log.

Record shape — one JSON line in frontmatter, `usage: [{...}, ...]`, one object per agent
dispatch. Executor dispatches go in that plan's `NN-MM-SUMMARY.md` (phase dirs, and
`.planning/quick/` as phase `quick`); verifier dispatches in the phase's `VERIFICATION.md`.
The orchestrator writes them, never the agent: an agent cannot observe its own usage.

  role         a flow-agent.py role, e.g. "executor"
  n            1, 2, ... — this dispatch's ordinal for that plan (or phase) and role
  kind         "first" (n == 1), "retry" (redoing a failed or dead attempt, incl. the
               Haiku lane's sonnet escalation) or "continuation" (resumed after a
               checkpoint answer — more work, not a retry)
  source       where the numbers came from; each defines tokens its own way:
                 agent-tool    Claude native Agent tool `<usage>`: `subagent_tokens`,
                               `duration_ms` as the host reports them
                 claude-cli    the bridge's `usage` object (modelUsage summed, all models)
                 codex-cli     the bridge's `usage` object (no tokens observed)
                 codex-native  Codex native spawn: nothing observed
  provider     "claude" | "codex" | "unknown"
  model        the model the dispatch requested, or "unknown" when none was passed
  tokens       int >= 0, or "unknown"
  duration_ms  int >= 0, or "unknown"

A value that was not observed is "unknown" (an absent key means the same); a real 0 stays
0. Nothing else is accepted — no extra keys, no free text — so no prompt, message content
or secret can ride along in a record. A malformed record exits 2 naming the file.

Aggregation. Every dispatch counts once: retries and continuations are dispatches too, so
`Dispatches` includes them and `Retries` is the subset with kind "retry". A wrapper
subagent that ran the bridge is never recorded — its own usage is orchestration, and the
bridge's object already covers the peer. Nested agents a dispatch spawned are never
recorded separately; whether a source's figure includes them is that source's definition.
A duplicate (location, plan, role, n) exits 2 instead of being counted twice. Tokens are
summed only within one source (they are grouped by it). A sum over values where some are
unknown renders `partial: <sum of known> (<known>/<total> known)`; all unknown renders
`unknown`. Duration is summed per dispatch, so parallel work sums past wall-clock time.
A SUMMARY or VERIFICATION with no `usage` line is listed as not recorded, never as zero.

Usage: flow-usage.py --repo PATH [--phase ID]     (ID: a phase dir prefix, or quick)
Stdlib only. Exit codes: 0 rendered or disabled; 2 bad config or malformed record.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re
import sys

UNKNOWN = "unknown"
KINDS = {"first", "retry", "continuation"}
SOURCES = {"agent-tool", "claude-cli", "codex-cli", "codex-native"}
PROVIDERS = {"claude", "codex", UNKNOWN}
KEYS = {"role", "n", "kind", "source", "provider", "model", "tokens", "duration_ms"}
REQUIRED = {"role", "n", "kind", "source"}
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/\[\]-]{0,63}$")


class RecordError(Exception):
    pass


def bridge_roles() -> set[str]:
    """The role names the bridge dispatches — one source of truth, not a copy."""
    spec = importlib.util.spec_from_file_location(
        "flow_agent", Path(__file__).resolve().parent / "flow-agent.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module.ALL_ROLES)


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


def frontmatter(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next((i for i, line in enumerate(lines) if line.strip() == "---"), None)
    if start is None:
        return []
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() == "---"), None)
    return lines[start + 1:end] if end is not None else []


def count(value: object, where: str, key: str) -> int | str:
    if value == UNKNOWN:
        return UNKNOWN
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RecordError(f"{where}: {key} must be an integer >= 0 or \"unknown\", "
                          f"got {value!r}")
    return value


def check(record: object, where: str, roles: set[str]) -> dict:
    if not isinstance(record, dict):
        raise RecordError(f"{where}: a record must be an object")
    extra = set(record) - KEYS
    if extra:
        raise RecordError(f"{where}: keys not allowed in a usage record: {sorted(extra)}")
    missing = REQUIRED - set(record)
    if missing:
        raise RecordError(f"{where}: missing {sorted(missing)}")
    n = record["n"]
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise RecordError(f"{where}: n must be an integer >= 1, got {n!r}")
    if record["role"] not in roles:
        raise RecordError(f"{where}: unknown role {record['role']!r}")
    if record["kind"] not in KINDS or (record["kind"] == "first") != (n == 1):
        raise RecordError(f"{where}: kind {record['kind']!r} does not fit n={n} "
                          "(\"first\" exactly when n is 1, else retry or continuation)")
    if record["source"] not in SOURCES:
        raise RecordError(f"{where}: unknown source {record['source']!r}")
    provider = record.get("provider", UNKNOWN)
    if provider not in PROVIDERS:
        raise RecordError(f"{where}: unknown provider {provider!r}")
    model = record.get("model", UNKNOWN)
    if not isinstance(model, str) or not (model == UNKNOWN or MODEL_RE.match(model)):
        raise RecordError(f"{where}: model must be a model name or \"unknown\", got {model!r}")
    return {"role": record["role"], "n": n, "kind": record["kind"],
            "source": record["source"], "provider": provider, "model": model,
            "tokens": count(record.get("tokens", UNKNOWN), where, "tokens"),
            "duration_ms": count(record.get("duration_ms", UNKNOWN), where, "duration_ms")}


def artifacts(planning: Path) -> list[tuple[str, str, Path]]:
    """(phase, unit, path) for every artifact that can carry records, in phase order."""
    found = []
    phases = planning / "phases"
    if phases.is_dir():
        for directory in sorted(p for p in phases.iterdir() if p.is_dir()):
            phase = directory.name.split("-", 1)[0]
            for path in sorted(directory.glob("*-SUMMARY.md")):
                found.append((phase, path.name.removesuffix("-SUMMARY.md"), path))
            if (directory / "VERIFICATION.md").is_file():
                found.append((phase, "VERIFICATION", directory / "VERIFICATION.md"))
    quick = planning / "quick"
    if quick.is_dir():
        for path in sorted(quick.glob("*-SUMMARY.md")):
            found.append(("quick", path.name.removesuffix("-SUMMARY.md"), path))
    return found


def collect(planning: Path, phase_filter: str | None, roles: set[str]):
    records, unrecorded, seen = [], [], set()
    for phase, unit, path in artifacts(planning):
        if phase_filter is not None and phase != phase_filter:
            continue
        line = next((l for l in frontmatter(path) if l.startswith("usage:")), None)
        if line is None:
            unrecorded.append(f"{phase}/{unit}")
            continue
        try:
            entries = json.loads(line.partition(":")[2])
        except json.JSONDecodeError as exc:
            raise RecordError(f"{path}: usage is not one JSON list ({exc.msg})")
        if not isinstance(entries, list):
            raise RecordError(f"{path}: usage must be a JSON list")
        for index, entry in enumerate(entries):
            record = check(entry, f"{path} usage[{index}]", roles)
            key = (str(path.parent), unit, record["role"], record["n"])
            if key in seen:
                raise RecordError(f"{path} usage[{index}]: duplicate {record['role']} n="
                                  f"{record['n']} — it would be counted twice")
            seen.add(key)
            records.append({**record, "phase": phase})
    return records, unrecorded


def total(values: list) -> str:
    known = [v for v in values if v != UNKNOWN]
    if not known:
        return UNKNOWN
    if len(known) == len(values):
        return str(sum(known))
    return f"partial: {sum(known)} ({len(known)}/{len(values)} known)"


def table(records: list[dict], key_fields: tuple[str, ...], headers: tuple[str, ...]) -> list[str]:
    groups: dict[tuple, list[dict]] = {}
    for record in records:
        groups.setdefault(tuple(record[f] for f in key_fields), []).append(record)
    columns = headers + ("Dispatches", "Retries", "Tokens", "Duration ms (sum)")
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    for key, group in groups.items():
        cells = list(key) + [str(len(group)), str(sum(r["kind"] == "retry" for r in group)),
                             total([r["tokens"] for r in group]),
                             total([r["duration_ms"] for r in group])]
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def render(records: list[dict], unrecorded: list[str]) -> str:
    out = ["## Observed usage", "",
           "Observed values only: `unknown` = not observed, `0` = observed zero. "
           "`partial: N (k/n known)` sums the k known values of n. Tokens are never summed "
           "across sources. Definitions: `flow-usage.py --help`.", ""]
    if records:
        out += ["### By phase and role", ""]
        out += table(records, ("phase", "role", "source"), ("Phase", "Role", "Source"))
        out += ["", "### By role and model", ""]
        by_model = sorted(records, key=lambda r: (r["role"], r["provider"], r["model"]))
        out += table(by_model, ("role", "provider", "model", "source"),
                     ("Role", "Provider", "Model", "Source"))
    else:
        out.append("No usage records.")
    if unrecorded:
        out += ["", "Not recorded (no `usage` line; not in the totals): "
                + ", ".join(unrecorded)]
    return "\n".join(out) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True, help="repository root (holds .planning/)")
    parser.add_argument("--phase", help="only this phase: a phase dir prefix, or quick")
    args = parser.parse_args()
    planning = Path(args.repo).resolve() / ".planning"
    try:
        if not enabled(planning):
            print("usage report: disabled — set \"usage_report\": true in "
                  ".planning/config.json to record and report observed usage")
            return 0
        records, unrecorded = collect(planning, args.phase, bridge_roles())
    except RecordError as exc:
        print(f"flow-usage: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(render(records, unrecorded))
    return 0


if __name__ == "__main__":
    sys.exit(main())
