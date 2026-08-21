<!-- Written retroactively on 2026-08-20 (quick 003). The phase was verified when it ran —
     923cae8's message records that its truths were run directly rather than by a verifier
     agent — but no VERIFICATION.md was written, so ROADMAP's "verified" had nothing on disk
     backing it. Every result below is a fresh re-run at c663ca1+ on 2026-08-20, not a
     transcription of what the executing session reported. Where the two would disagree, the
     re-run wins and is marked. -->
---
phase: 03-rebuild-readme
status: pass
smoke: pass
gaps:
  - "CLOSED IN THIS COMMIT — docs/execution-model.md said `~220KB` of prompt content; re-measured 2026-08-20 as 234438 B = 228 KiB, floor-5 **225**. Corrected to `~225KB`. Listed rather than silently fixed: verification found it, and a gaps list that only ever reads `[]` is not a record."
  - "SUPERSEDED 2026-08-21 by the /flow-handsoff branch — two byte-identity truths below no longer hold and are not repairable by re-running. (a) L3s3: the reconstruction pinned the literal `20 shared Agent Skills` while substituting the agent count and size dynamically, so a 21st skill turns it red for a numeral that is now *correct*. Corrected command adds the same treatment for the skill count — `sed \"s/20 shared/$sk shared/; s/9 subagents/$n subagents/; s/~165KB/~${kb}KB/\"` where `sk=$(ls -d plugins/devflow/skills/*/ | wc -l)`; re-run against docs/execution-model.md at this commit it prints nothing (GREEN), reconstructing `21 shared Agent Skills and 11 subagents across ~240KB`. (b) L5s1+L5s2: the pinned sentence opens `No Node runtime and no hooks.`, which D-20 deliberately reversed — that truth is superseded by a recorded decision, not drifted, and byte-identity against the phase-start blob can never hold again. Both are recorded rather than quietly re-pinned: a truth edited to match the code it grades stops being a check."
unverified: []
---

## Provenance
Retroactive. Not an independent fresh-context check when it ran (923cae8 states this plainly), and not one now either — same caveat, stated rather than hidden. What makes it evidence is that every truth in this phase is a *command*: the commands are re-run here and their output recorded, so the record does not rest on anyone's report.

## Smoke
`python3 scripts/validate-plugin.py && python3 -m unittest discover -s tests && python3 scripts/check-links.py` → **exit 0**. `Plugin OK: 20 shared skills, 11 Claude agents, both hosts valid.`; `OK (skipped=2)` over 101 tests; `0 failures, 197 references checked`. *(As run on 2026-08-20. At 2026-08-21 the same command prints `21 shared skills` and 109 tests — see the supersession entry in `gaps`; the recorded output is what this pass actually saw, not what a re-run prints today.)*

## Truths — 03-01 (fence guard)
| must_have truth | result | evidence |
|---|---|---|
| guard exits 0, summary with F >= 10 and L > 0 | VERIFIED | `0 violations, 11 files scanned, 16 fenced lines`, exit 0. F=11, L=16 — counts present, not a guard that scanned nothing. |
| fence notion is check-links.py's: ```, `~~~`, tab-indented each a violation | VERIFIED | `test_real_path_inside_backtick_fence_is_a_violation`, `…_tilde_fence…`, `…_tab_indented_fence…` — 3 tests, all ok. |
| toggle-inversion right in both directions (assertion pair) | VERIFIED | `test_toggle_inversion_reports_the_fenced_path_and_skips_the_prose_path` ok. |
| unterminated fence is a violation naming the opener | VERIFIED | `test_unterminated_fence_is_a_violation_naming_the_opener_line` ok. |
| fail-closed when check-links.py is unloadable — never `0 violations` | VERIFIED | `test_scan_raises_when_the_checker_cannot_be_loaded` ok. |
| suite passes; smoke exit 0 with >= 179 refs | VERIFIED | `Ran 9 tests … OK` for this suite; full smoke exit 0 at **197** refs (>= 179). |

## Truths — 03-02 (docs index)
| must_have truth | result | evidence |
|---|---|---|
| tracked, exactly one `# ` heading | VERIFIED | `git ls-files --error-unmatch docs/README.md` exit 0; `grep -c '^# '` → 1. |
| link count == pages - 1, as arithmetic | VERIFIED | sibling-class links **11**; `ls docs/*.md \| wc -l` - 1 → **11**. Equal. |
| every page listed exactly once | VERIFIED | per-page `grep -q "]($b)"` loop over `docs/*.md` printed nothing. |
| index does not link itself | VERIFIED | `grep -c '](README.md)'` → 0. |
| every link sibling-form | VERIFIED | `grep -c '](docs/'` → 0. |
| each entry carries its one-liner | VERIFIED | `grep -cE '\]\([A-Za-z0-9_-]+\.md\) — .{20,}'` → 11 — all 11, not a subset. |
| no bare backticked `docs/` path | VERIFIED | `grep -c '`docs/'` → 0. |
| links resolve; ref count >= 190 | VERIFIED | `0 failures`, **197** references. |
| G1–G4: smoke, docs <= 250 lines, fence guard, NOTICE untouched | VERIFIED | smoke exit 0; longest page `docs/status-contract.md` **138** lines; guard exit 0; NOTICE unmodified since phase start. |

## Truths — 03-03 (displaced prose)
| must_have truth | result | evidence |
|---|---|---|
| opening is one paragraph, 346 bytes with newline | VERIFIED | `awk` extraction → `1 line, 346 bytes`. Exact, so nothing was added or reworded. |
| each of 3 chunks: 0 in README, exactly one docs page | VERIFIED | `nothing loads it all` → README 0, `docs/execution-model.md`; `azd on Azure` → README 0, `docs/execution-model.md`; `rather than replacing it` → README 0, `docs/providers.md`. |
| D-14 holds at **every** commit of the plan | VERIFIED | 3 commits carry `DevFlow-Plan: 03-03`; the per-SHA loop printed no `D-14 VIOLATION`. Non-vacuous: the `shas` guard was checked and found non-empty. |
| moved sentences byte-identical; numerals match the repo | **SUPERSEDED 2026-08-21** (was VERIFIED — one numeral had drifted, corrected in that pass) | `ls plugins/devflow/agents/*.md \| wc -l` → **11**, matches "11 subagents". The size numeral did **not**: measured 234438 B = 228 KiB → floor-5 **225**, against `~220KB` on the page. Corrected to `~225KB` in this commit. The sentence is otherwise byte-identical. |

## Truths — 03-04 (README shape)
| must_have truth | result | evidence |
|---|---|---|
| exactly six `##` sections, in order | VERIFIED | `Install, Quick start, Commands, Configuration, Documentation, License and acknowledgements`; `grep -c '^## '` → 6. |
| SC-01: <= 110 lines, <= 14000 bytes | VERIFIED | **101** lines, **5957** bytes — both well inside. |
| command table byte-identical, 20 data rows | VERIFIED | `diff` against `5ffe726:README.md`'s table printed nothing; row count **20**. |
| Quick start names flow-new → flow-plan 1 → flow-execute 1 in order, all in the table | VERIFIED | first mentions in that order; all five commands named in the section (`flow-new`, `flow-plan`, `flow-execute`, `flow-status`, `flow-pr`) each appear in the 20-row table. |
| ASCII diagram survived byte-identically **with its fence**, inside Quick start | VERIFIED | blob `38b2bc0` lines 52–55 all found via `grep -qxF`; blob reachable (guard checked); anchor at README:32, and lines 31/34 are the ``` fence pair. |

## Human checks
- [x] SC-04 — first-time reader reaches a running `/flow-new` without opening `docs/`. Answered **PASS** 2026-08-19; recorded in `.planning/DECISIONS.md`.

## Learnings
- A prose numeral measured from the repo (`~225KB` of prompt content) drifts on every plugin change and nothing re-measures it. Either automate the check or de-specify the number — this one went stale within two releases.
