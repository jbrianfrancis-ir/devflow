# Findings — conventions

## Summary
0 blocking, 2 should-fix, 4 nit

## What was checked (all verified by command, not by reading)

**ARCHITECTURE.md Forbidden — all five hold:**
- No third-party Python package: `scripts/check-links.py` imports only `os, re, subprocess, sys, typing`; `tests/test_check_links.py` only `importlib.util, os, shutil, subprocess, tempfile, unittest, pathlib`. Proved by loading the module under `python3 -S -E` (no site-packages, no env) — imports clean.
- No `pip` in CI: only hit across `.github/workflows/` is `set -euo pipefail` in `release.yml`.
- No docs build system: nothing added.
- No `src/` at repo root: absent; `git ls-files` shows no `src/`, no `requirements.txt`, no `pyproject.toml`.
- No manifest version edits: `git diff main...HEAD --stat -- '*plugin.json' '*marketplace.json'` is empty.
- No restated requirements/versions/roadmap in `CLAUDE.md`/`AGENTS.md`: the DEVFLOW block is pure pointers (a table of "need → file"); the repo-specific note after `<!-- END DEVFLOW -->` states only how to load the working tree vs the published plugin — no requirement, version, or roadmap content.

**Layout override honored:** tooling in `scripts/check-links.py`, tests in `tests/test_check_links.py`, payload untouched except one line of `plugins/devflow/references/autonomy.md`. Nobody "corrected" toward `src/`.

**Pointer files:** `cmp CLAUDE.md AGENTS.md` → byte-identical. Both carry the `<!-- BEGIN DEVFLOW -->`/`<!-- END DEVFLOW -->` markers.

**Commit hygiene:** `git log main ^$(git merge-base main HEAD)` is empty — nothing landed on the base branch. All 13 commits on `flow/docs-restructure` carry a `DevFlow-Agent:` trailer that `git interpret-trailers --parse` extracts cleanly (verified per-commit). Author == committer == `jbrianfrancis-ir <brianf@informativeresearch.com>` on every one; the trailer is additive, not a substitute. Branch name `flow/docs-restructure` and `config.json` `git.base: "main"` are both correct (no `dev` branch exists locally or on any remote).

**Regex parseability of `flow-agent.py`:** untouched by this diff. Re-ran `validate-plugin.py`'s own extraction pattern independently — `READ_ONLY_ROLES` parses to 7 roles, `WRITE_ROLES` to 4. Validator exits 0.

**Smoke (the ARCHITECTURE `## Smoke` command, verbatim):** `Plugin OK: 20 shared skills, 11 Claude agents, both hosts valid.` / `Ran 49 tests … OK (skipped=2)` / `0 failures`. Exit 0 from all three.

**Python style vs the existing scripts:** consistent. `main(argv=None)` + `if __name__ == "__main__": sys.exit(main())` matches `flow-fleet.py`; `with open(path, encoding="utf-8") as stream` and the `stream` name match `validate-plugin.py`; `# --- section ---` banners match `flow-fleet.py`; `_private` helper naming, no docstring on trivial helpers, docstrings on the public seams (`check`, `main`'s module header) — all in register. The bare `except Exception` in `main()` is correct here, not sloppy: it is the fail-closed guard conventions.md demands ("could not check" is never silently clean), and it is commented as such at `scripts/check-links.py:57`.

**Test style:** `tests/test_check_links.py` follows the established `importlib.util.spec_from_file_location` idiom for hyphenated scripts (MAP.md → Conventions), `ROOT = Path(__file__).resolve().parents[1]`, `SPEC`/`MODULE` constant naming — matches `test_flow_fleet.py` and `test_flow_agent.py` exactly.

**Prose register:** the new markdown (`.planning/*`, phase artifacts, `CLAUDE.md`/`AGENTS.md`) is dense, terse, and load-bearing — every clause carries a fact or a reason. No filler, no hedging, no restated boilerplate. Matches the house style MAP.md records. The `autonomy.md` one-line fix (`../docs/status-contract.md` → `docs/status-contract.md`) also aligns that file with the repo's existing idiom for backticked repo-root-relative paths, which `references/conventions.md` already uses twice for `docs/blitzos.md`.

**Artifact shapes:** PLAN/SUMMARY/VERIFICATION frontmatter matches `plugins/devflow/templates/{plan,summary,verification}.md` field-for-field. JOURNAL is newest-first and 1043B against its 2KB cap. DECISIONS.md is append-only with one entry, correctly matching the one gate the branch actually raised (the phase-01 abstention) — `/flow-new` and `/flow-plan` both logged `CONTINUE`, not `GATE`, so no other entry is owed.

## Findings

### [should-fix] `DevFlow-Plan: 01` is a phase number in a field the convention defines as `NN-MM`
- `.planning/` bookkeeping commits `9fb0b35`, `d1dfd04`, `14d0f2c`
- conventions.md → Commit attribution defines the trailer as `DevFlow-Plan: NN-MM` and scopes it: "plan-scoped commits only; omit it for project-level ones." These three carry `DevFlow-Plan: 01` — a phase id, which is neither a plan id nor an omission. The six executor commits get it right (`01-01`, `01-02`, `01-03`).
- Consequence: `/flow-audit` reads this trailer with `%(trailers:key=DevFlow-Plan,valueonly)` and groups by it (`plugins/devflow/skills/flow-audit/SKILL.md:49`). A phase-01 audit therefore sees four groups — `01-01`, `01-02`, `01-03`, and a phantom `01` — so "attributed vs total per plan" is wrong for the phase, and any consumer doing `--grep='^DevFlow-Plan: 01-'` drops the phase-close commits entirely.
- Fix: these are skill-level bookkeeping commits for the phase, not for a plan — omit `DevFlow-Plan` on them (the `DevFlow-Agent: flow-execute/...` / `flow-plan/...` trailer already identifies them). If a phase-scoped variant is genuinely wanted, it needs a distinct key (`DevFlow-Phase:`) and a line in conventions.md, not an overloaded one. History is pushed, so fix forward — do not rewrite; the real change is in the emitting skills.

### [should-fix] `check-links.py:53` `main(argv=None)` accepts `argv` and silently discards it
- `scripts/check-links.py:53-63`
- The signature matches `plugins/devflow/scripts/flow-fleet.py:419`, where the identical `main(argv=None)` feeds `ap.parse_args(argv)` and is the tested programmatic seam (`tests/test_flow_fleet.py` drives `MODULE.main([...])`). Here the parameter is never read — no `argparse`, no positional handling, nothing.
- Consequence: a caller mirroring the sibling script's contract — `main([str(root), "--json"])`, which is exactly how `test_flow_fleet.py` invokes the fleet scanner — gets a full run against the ambient cwd with every argument silently dropped, and exit 0. Silent-ignore is the failure shape ARCHITECTURE's "Fail fast — no fallback values" and conventions' fail-closed rule both exist to prevent: the caller gets a clean result for a request that was never honored.
- Fix: either drop the parameter (`def main():`) so the misuse is a `TypeError`, or wire it through an `argparse` parser like `flow-fleet.py` does. Dropping it is the smaller change and matches `flow-agent.py:124` (`def main() -> int:`), which also takes no argv.

### [nit] MAP.md undercounts the templates directory
- `.planning/codebase/MAP.md:20` — "`templates/*.md` 17 output templates"
- `ls plugins/devflow/templates/*.md | wc -l` → 18. The neighbouring counts on the same lines (20 skills, 11 agents, 11 references) are all exact and two of them are CI-pinned in `validate-plugin.py:83-86`, so this one reads as authoritative and isn't.
- Fix: 17 → 18 on the next map refresh.

### [nit] `D-12` is listed before `D-11` in the PROJECT.md decision table
- `.planning/PROJECT.md:36-37`
- The table is otherwise strictly ordered `D-01`…`D-10`, then jumps to `D-12` and back to `D-11`. `D-11` (the accepted cap overruns) is cited by three separate header comments — `PROJECT.md:1`, `REQUIREMENTS.md:1`, `ARCHITECTURE.md:1` — so it is the entry a reader most often goes looking for, and it is the one out of place.
- Fix: swap the two rows.

### [nit] Two phase-01 SUMMARY files exceed the 1.5KB cap, and D-11 does not cover them
- `.planning/phases/01-link-safety-net/01-02-SUMMARY.md` (1721B), `01-01-SUMMARY.md` (1511B) — cap is stated in `plugins/devflow/templates/summary.md:1`
- D-11 accepts overruns for "REQUIREMENTS/PROJECT/ARCHITECTURE and the phase-01 **plans**". SUMMARYs are not in that list, so these two are unaccounted-for rather than accepted. `01-02` is ~15% over; `01-01` is 11 bytes over.
- Fix: trim `01-02-SUMMARY.md` by a line or two, or widen D-11's wording to name the summaries. Either closes the gap; leaving it silent is what makes the accepted-overrun record stop meaning anything.

### [nit] `%`-formatting introduced into a test file that used neither `%` nor f-strings
- `tests/test_flow_fleet.py:175`, `:224` — `"- %s | /flow-execute | phase 3 | CONTINUE" % TODAY`
- Before this change the file contained zero `%s` and zero f-strings (verified against `main`); the sibling `tests/test_flow_agent.py` uses f-strings throughout (8 occurrences). Defensible either way — `flow-fleet.py`, the script under test, uses `%` formatting — so this is a coin-flip, not an error.
- Fix: optional; f-strings would match the other test module. The fix itself (computing the fixture date at runtime) is correct and the comment at `:22-27` explaining why is exactly the right register.
