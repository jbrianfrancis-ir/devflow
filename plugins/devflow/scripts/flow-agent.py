#!/usr/bin/env python3
"""Run one bounded DevFlow role through an authenticated Claude or Codex CLI."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

READ_ONLY_ROLES = {"mapper", "researcher", "plan-checker", "reviewer", "verifier"}
WRITE_ROLES = {"planner", "executor", "migrator", "consultant"}
ALL_ROLES = READ_ONLY_ROLES | WRITE_ROLES
FIELDS = {"status", "summary", "artifacts", "completed", "checkpoint", "error"}
RESULT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "status": {"type": "string", "enum": ["COMPLETED", "CHECKPOINT", "FAILED"]},
        "summary": {"type": "string"},
        "artifacts": {"type": "array", "items": {"type": "string"}},
        "completed": {"type": "array", "items": {"type": "string"}},
        "checkpoint": {"type": ["string", "null"]},
        "error": {"type": ["string", "null"]},
    },
    "required": sorted(FIELDS),
}


def failure(message: str) -> dict:
    return {"status": "FAILED", "summary": "", "artifacts": [], "completed": [],
            "checkpoint": None, "error": message}


def resolve_provider(requested: str | None, configured: str | None, host: str) -> str:
    """Apply command > project > native precedence and resolve native to host."""
    selected = requested or configured or "native"
    if selected not in {"native", "claude", "codex"}:
        raise ValueError(f"unsupported provider: {selected}")
    if host not in {"claude", "codex"}:
        raise ValueError(f"unsupported host: {host}")
    return host if selected == "native" else selected


def configured_provider(repo: Path) -> str | None:
    """Read `agents.provider` from the project config; absent or unreadable is None."""
    try:
        config = json.loads((repo / ".planning" / "config.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    agents = config.get("agents") if isinstance(config, dict) else None
    provider = agents.get("provider") if isinstance(agents, dict) else None
    return provider if isinstance(provider, str) else None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=("claude", "codex"), required=True,
                        help="the CLI this bridge is being called from")
    parser.add_argument("--provider", choices=("native", "claude", "codex"),
                        help="omit to fall back to project config, then native")
    parser.add_argument("--role", choices=sorted(ALL_ROLES), required=True)
    parser.add_argument("--model", help="model for the peer CLI; names are "
                                        "provider-specific, so pass one valid for --provider")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--timeout", type=int, default=1800)
    return parser.parse_args()


def validate_result(value: object) -> dict | None:
    if not isinstance(value, dict) or set(value) != FIELDS:
        return None
    if value["status"] not in {"COMPLETED", "CHECKPOINT", "FAILED"}:
        return None
    if not isinstance(value["summary"], str):
        return None
    for key in ("artifacts", "completed"):
        if not isinstance(value[key], list) or not all(isinstance(x, str) for x in value[key]):
            return None
    for key in ("checkpoint", "error"):
        if value[key] is not None and not isinstance(value[key], str):
            return None
    return value


def build_command(provider: str, role: str, repo: Path, prompt: str,
                  schema_path: Path, model: str | None = None) -> list[str]:
    access = "read-only" if role in READ_ONLY_ROLES else "workspace-write"
    instruction = (f"You are the DevFlow {role} peer. Work only in {repo}. "
                   f"Access class: {access}. Do not start another provider CLI. "
                   "Never bypass permissions. Return only the requested structured result.\n\n"
                   + prompt)
    # Model names are provider-specific, so the caller passes one it knows is
    # valid for `provider`; absent, the peer CLI picks its own default.
    if provider == "codex":
        return (["codex", "exec", "--cd", str(repo), "--sandbox", access,
                 "--output-schema", str(schema_path), "--color", "never"]
                + (["--model", model] if model else []) + [instruction])
    permission = "plan" if access == "read-only" else "acceptEdits"
    return (["claude", "-p", "--permission-mode", permission, "--output-format", "json",
             "--json-schema", json.dumps(RESULT_SCHEMA)]
            + (["--model", model] if model else []) + [instruction])


def extract_result(provider: str, stdout: str) -> dict | None:
    try:
        outer = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    candidate = outer.get("structured_output") if provider == "claude" and isinstance(outer, dict) else outer
    return validate_result(candidate)


def emit(value: dict, code: int) -> int:
    print(json.dumps(value, separators=(",", ":")))
    return code


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    prompt_path = Path(args.prompt_file).resolve()
    if not repo.is_dir() or not (repo / ".git").exists():
        return emit(failure("repository is missing or is not a git checkout"), 2)
    if not prompt_path.is_file():
        return emit(failure("prompt file is missing"), 2)
    try:
        provider = resolve_provider(args.provider, configured_provider(repo), args.host)
    except ValueError as exc:
        return emit(failure(str(exc)), 2)
    if provider == args.host:
        # hosts.md: native means the current host and must never start a second CLI.
        return emit(failure(f"native provider resolved to the {args.host} host; "
                            "spawn an in-host agent instead of the bridge"), 2)
    if shutil.which(provider) is None:
        return emit(failure(f"{provider} CLI is not installed or not on PATH"), 2)

    with tempfile.TemporaryDirectory(prefix="devflow-agent-") as temporary:
        schema_path = Path(temporary) / "result.schema.json"
        schema_path.write_text(json.dumps(RESULT_SCHEMA), encoding="utf-8")
        command = build_command(provider, args.role, repo,
                                prompt_path.read_text(encoding="utf-8"), schema_path,
                                args.model)
        try:
            # stdin must be closed: codex exec reads a non-TTY stdin and would
            # otherwise block on an inherited pipe until --timeout expires.
            run = subprocess.run(command, cwd=repo, text=True, capture_output=True,
                                 stdin=subprocess.DEVNULL, timeout=args.timeout,
                                 env=os.environ.copy())
        except subprocess.TimeoutExpired:
            return emit(failure(f"{provider} peer timed out"), 124)
        except OSError as exc:
            return emit(failure(f"could not start {provider} peer: {exc.strerror}"), 2)

    if run.returncode != 0:
        # Provider stderr can contain repository context; expose only the status.
        return emit(failure(f"{provider} peer exited with status {run.returncode}"), 2)
    result = extract_result(provider, run.stdout)
    if result is None:
        return emit(failure(f"{provider} peer returned malformed structured output"), 2)
    return emit(result, 0 if result["status"] != "FAILED" else 2)


if __name__ == "__main__":
    sys.exit(main())
