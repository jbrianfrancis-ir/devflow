---
phase: 01-link-safety-net
status: pass
smoke: pass
gaps: []
unverified:
  - "GitHub anchor slugging for duplicate headings (`-1`), inline-code/link/punctuation headings, and setext headings — the repo contains none of these cases, so nothing grades it."
---

## Smoke
`python3 scripts/validate-plugin.py && python3 -m unittest discover -s tests -v && python3 scripts/check-links.py` → **exit 0**. Validator `Plugin OK: 20 shared skills, 11 Claude agents, both hosts valid.` (no error lines); `Ran 49 tests … OK (skipped=2)`; checker `0 failures`. Meets "Pass looks like" as written.

REQ-11 across the phase: each commit's **own** Smoke line, run in a detached worktree — 0208304, 84e6eb7, de9e446, 9206aed (2-step) and 4f1a251, 915460b (3-step) all exit 0. The 3-step line first appears at 4f1a251, after 0208304 made the script runnable.

## Truths — 01-01 (checker)
| must_have truth | result | evidence |
|---|---|---|
| exits 0 on the repo, no failure lines | VERIFIED | `python3 scripts/check-links.py` → `0 failures`, exit 0. Not vacuous — instrumented run: **162 path refs actually resolved** on disk (174 skipped by R1–R5) over 50 scoped `.md`. |
| 4 broken kinds in README.md each fail naming file/line/target; revert restores 0 | VERIFIED | Appended one at a time, run, reverted. `[x](docs/nope.md)` → `README.md:169: docs/nope.md — target does not exist`; backticked `scripts/nope.py` → `README.md:169: scripts/nope.py — …`; backticked `{devflow_root}/references/nope.md` → `README.md:169: plugins/devflow/references/nope.md — …` (resolved under `plugins/devflow/`); `[x](#no-such-heading)` → `README.md:169: #no-such-heading — no such heading #no-such-heading`. All exit 1; each revert → exit 0, `git status -- README.md` empty. |
| `[x](#install)` (real heading) exits 0 | VERIFIED | Appended → `0 failures`, exit 0; reverted clean. README `## Install` at line 9. |
| plants under `plugins/devflow/templates/plan.md` and `.planning/PROJECT.md` leave exit 0 | VERIFIED | Both planted (`git status` showed both `M`) → `0 failures`, exit 0; `git checkout` on exactly those two paths restored both. STATE.md / JOURNAL.md never touched. |
| `python3 -S -E scripts/check-links.py` exits 0 (SC-05) | VERIFIED | → `0 failures`, exit 0. Imports: `os, re, subprocess, sys, typing`. |
| **backstop:** anchor slugging for duplicate / inline-code / setext headings | HUMAN (non-inferable) | Abstained. Nothing in the repo or the suite exercises these cases; reading the slugger would be circular. |

Key links: `_all_tracked` shells `git -C <root> ls-files` (check-links.py:79), no hardcoded list; `def check(root)` (:35) returns failures, prints nothing; sole top-level execution `if __name__ == "__main__"` (:333) — importing prints nothing, `callable(m.check)` → `True`.

## Truths — 01-02 (tests)
| must_have truth | result | evidence |
|---|---|---|
| `unittest tests.test_check_links -v` → OK | VERIFIED | `Ran 13 tests … OK`, 0 failures/errors. |
| `discover -s tests -v` OK, names `test_check_links` beside both existing suites | VERIFIED | `Ran 49 tests … OK (skipped=2)`; output lists `test_check_links.*`, `test_flow_agent.*`, `test_flow_fleet.*`. |
| one failing case per kind asserting file, line, target | VERIFIED | `test_markdown_link_…`, `test_anchor_to_no_such_heading_fails`, `test_backticked_path_…`, `test_devflow_root_reference_…` (:63–119) each assert `len==1` plus `.file`, `.line`, `.target`. |
| negative direction: all-resolving fixture returns `[]` | VERIFIED | `test_fixture_with_only_resolving_references_has_no_failures` (:50). **Mutation-proved**: making `check()` append one constant failure → 13/13 tests fail. |
| R5 pinned per-base in both directions | VERIFIED | `test_r5_is_per_base_checks_other_base_and_skips_no_base` (:177): (a) `sub/a.md` → `helpers/missing.py` (with `sub/helpers/present.py`) asserts a failure naming file, line 3, target; (b) `codebase/MAP.md` yields none. **Mutation-proved**: forcing `_r5_skip` → always `True` (the wrong root-only-ish widening) fails this test `1 != 0`. A skip-only suite would not catch that. |
| scope: plants under `templates/` and `.planning/` leave `[]` | VERIFIED | `test_broken_reference_under_templates_is_not_checked`, `…_under_planning_…` (:125–139), each planting a real top-level `sub/` so the token would otherwise be checked. |
| `-S -E` discover → OK (SC-05) | VERIFIED | `Ran 49 tests … OK (skipped=2)`. |
| `git status --porcelain -- scripts tests docs plugins README.md` empty after the run | VERIFIED | Empty. |

Key links: loads the hyphenated script via `importlib.util.spec_from_file_location("check_links", …)` (:19–21), root from `Path(__file__).resolve().parents[1]`; every test drives `MODULE.check(root)` on a `mkdtemp` git fixture with `GIT_CONFIG_GLOBAL/SYSTEM=/dev/null` — never the CLI, never this repo.

## Truths — 01-03 (standing gate)
| must_have truth | result | evidence |
|---|---|---|
| Smoke run verbatim exits 0, unittest OK incl. `test_check_links`, checker silent | VERIFIED | See `## Smoke`; that run's output includes the `test_check_links` cases. |
| Smoke names three steps | VERIFIED | ARCHITECTURE.md:24. |
| lint.yml runs `python3 scripts/check-links.py`; 0 at HEAD, non-zero with a planted `scripts/nope.py`, revert restores 0 | VERIFIED | lint.yml:20–21 `- name: Check internal links`, inside the existing `validate` job. HEAD → exit 0; plant → `README.md:169: scripts/nope.py — target does not exist`, exit 1; `git checkout README.md` → exit 0. |
| `grep -c 'uses:' lint.yml` = 1 (SC-05) | VERIFIED | Returns `1`; only `actions/checkout@v4` (:15). |
| still triggers on push to `main` and pull_request (REQ-10) | VERIFIED | lint.yml:3–6, unchanged by 915460b. |
| no install/pip/setup-python in lint.yml | VERIFIED | `grep -nE 'pip|install|setup-python'` → no output. |

`git show 4f1a251 -- .planning/ARCHITECTURE.md` touches only the `## Smoke` Command line, "Pass looks like", and the deleted reservation comment — no hunk in `## Link checking`.

## Human checks
- [x] **Backstop, anchor slugging** — ANSWERED 2026-08-18 (D-12): abstention **accepted**. The rule stays unproven and unasserted; revisit only if `docs/` introduces duplicate, inline-code, or setext headings. Deliberately NOT resolved by reading the slugger. Logged in DECISIONS.md at d1dfd04.
- [~] **CARRIED TO /flow-pr — GREEN HALF PROVEN 2026-08-18 on PR #20.** CI log (run 32169132542): step `Check internal links` executed and printed `0 failures, 162 references checked`; `validate` = pass; `Ran 92 tests`. REMAINING for a human: confirm `lint` ran the `Check internal links` step and passed; then push a commit with a deliberately broken internal reference, confirm `lint` turns red on that step, and revert. Carried from 01-03's SUMMARY — only observable on a real PR, not a gap.

Phase verdict after the gate: **pass**, with one check carried forward. The carried check is
not a gap — it is unobservable before a PR exists.

## Learnings
- The checker ignores everything inside fenced code blocks — a rule beyond REQ-09e's documented R1–R5. It hides nothing today (measured: 0 otherwise-checkable backticked refs sit inside fences), but phases 02–04 moving examples into fences would lose that coverage with no signal.
- `main()` resolves the root with `git rev-parse --show-toplevel` from the **cwd**, not the script's location; smoke and CI are correct only because both run from the repo root. `check(root)` takes an explicit root and is the safe seam.
- R5's blind spot is load-bearing for the clean baseline: a first-segment typo matching no top-level entry of any base (`docz/x.md`) goes unreported. A later phase renaming a top-level directory should expect refs to it to go quiet, not red.
