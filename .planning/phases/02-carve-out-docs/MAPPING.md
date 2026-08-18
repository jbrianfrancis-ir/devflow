# Phase 02 — section → file mapping (D-16)

Authoritative and reviewable **before any prose moves**. Every line of `README.md` at phase start
appears exactly once below. Source: `README.md` at `e23403c` (blob `f547d49`), 167 lines.

> **Line numbers are phase-start coordinates only.** README shrinks as each plan lands, so an
> executor must locate a section by its **heading or its anchor phrase**, never by line number.

## Disposition of every README line

| README lines | Section | Destination | Plan |
|---|---|---|---|
| 1–7 | Title + 3 positioning paragraphs | **STAYS** — phase 03 (REQ-03) | — |
| 9 | `## Install` | **STAYS** | — |
| 11–16 | `### Claude Code` + install block | **STAYS** (REQ-03: both blocks above the fold) | — |
| 18–23 | `### Codex CLI, app, or IDE` + install block | **STAYS** | — |
| 25–27 | Codex thread restart, `$flow-*` names, cloud not in scope | `docs/installation.md` | 02-01 |
| 29–36 | `### Provider selection` + body | `docs/providers.md` | 02-01 |
| 38–40 | `### Model tiers` + body | `docs/providers.md` | 02-01 |
| 42 | Self-bootstrap, `CLAUDE.md`/`AGENTS.md` pointer files | `docs/installation.md` | 02-01 |
| 44 | Context repos (BlitzOS-style) | `docs/installation.md` | 02-01 |
| 46–69 | `## Commands` + 20-row table | **STAYS** (REQ-02, content unchanged) | — |
| 71 | `## Flow` | **STAYS** — phase 03 renames/reshapes | — |
| 73–76 | ASCII flow diagram | **STAYS** (REQUIREMENTS → Assumptions) | — |
| 78 | Graph execution — waves, fake-edge test, fan-in guard, verifier, frozen must_haves | `docs/execution-model.md` | 02-02 |
| 80 | Provenance — trailers, `DECISIONS.md`, `/flow-audit --export` | `docs/provenance.md` | 02-02 |
| 82 | Smoke gate | `docs/execution-model.md` | 02-02 |
| 84 | State lives in `.planning/`; `JOURNAL.md` | `docs/execution-model.md` | 02-02 |
| 86 | Conventions — layout, git workflow, secret scan, Environment manifest | `docs/execution-model.md` | 02-02 |
| 88 | Architecture constraints — `ARCHITECTURE.md` as law | `docs/execution-model.md` | 02-02 |
| 90 | Second opinions (`/flow-oracle`) | `docs/review.md` | 02-03 |
| 92 | Design constraints (`/flow-design`) | `docs/execution-model.md` | 02-02 |
| 94 | `## Saying "unknown" out loud` | `docs/requirements-clarity.md` | 02-03 |
| 96 | Why agents write confident sentences | `docs/requirements-clarity.md` | 02-03 |
| 98 | `[NEEDS CLARIFICATION]` markers → backstop truths | `docs/requirements-clarity.md` | 02-03 |
| 100 | `## Assumptions` and `SC-NN` success criteria | `docs/requirements-clarity.md` | 02-03 |
| 102 | `/flow-audit` cross-artifact check | `docs/requirements-clarity.md` | 02-03 |
| 104 | `## Many streams at once` | `docs/parallel-work.md` | 02-04 |
| 106 | Section intro | `docs/parallel-work.md` — **lead sentence only**; see "Deliberate deletion" | 02-04 |
| 108 | Fleet board | `docs/parallel-work.md` | 02-04 |
| 110 | Workstreams | `docs/parallel-work.md` | 02-04 |
| 112 | PR to green (`/flow-ci`) | `docs/review.md` | 02-04 |
| 114 | Review before the code exists (`--panel`) | `docs/review.md` | 02-03 |
| 116 | Docs that don't quietly rot — `mapped_sha`, librarian pass | `docs/execution-model.md` | 02-02 |
| 118 | Adversarial review — peer-provider dispatch | `docs/review.md` | 02-04 |
| 120 | Adjudication in a third context — verdict + disposition | `docs/review.md` | 02-04 |
| 122 | Three ledger rules | `docs/review.md` | 02-04 |
| 124 | Review that isn't self-review (`/flow-pr` lenses) | `docs/review.md` | 02-03 |
| 126–128 | `## Autonomous operation` + status line | `docs/autonomy.md` | 02-05 |
| 130–134 | The five recipes | `docs/autonomy.md` | 02-05 |
| 136 | Loop rails | `docs/autonomy.md` | 02-05 |
| 138 | Structured `## Gate` block | `docs/autonomy.md` | 02-05 |
| 140 | Human gate list + cost note | `docs/autonomy.md` | 02-05 |
| 142–147 | `## Session hygiene (/clear)` + body | `docs/autonomy.md` | 02-05 |
| 149 | `## Acknowledgements` heading | **STAYS** (REQ-01 keeps License/Acknowledgements) | — |
| 151–165 | 8 acknowledgement paragraphs | `docs/acknowledgements.md` — **VERBATIM** (REQ-07) | 02-05 |
| — | *(new)* one-line pointer to the page and `NOTICE` | **ADDED to README** (REQ-07) | 02-05 |
| 167 | `MIT licensed — see LICENSE.` | **STAYS** | — |

Nine new files; `docs/blitzos.md` and `docs/status-contract.md` are untouched (out of scope).

## D-16 fold-ins — the five topics REQ-05 does not name

| Topic | README | Folds into | Why that page |
|---|---|---|---|
| Conventions | 86 | `execution-model` | CONTEXT.md D-16, verbatim |
| Architecture constraints | 88 | `execution-model` | CONTEXT.md D-16, verbatim |
| Smoke gate | 82 | `execution-model` | CONTEXT.md D-16, verbatim |
| Second opinions (`/flow-oracle`) | 90 | `review` | It is external judgment on work in progress — the same page already carries plan review, diff review, and adversarial review, and `/flow-oracle` is the escalation those reach for |
| Design constraints (`/flow-design`) | 92 | `execution-model` | Nearest topical home is architecture constraints (88), which D-16 already sends there: both are pins the planner and executor treat as law, and both make a violation a verification gap |
| *(also unnamed)* Docs that don't rot | 116 | `execution-model` | Not parallelism despite sitting in that section: `mapped_sha` staleness is the phase-close step of the execute → verify loop this page describes |
| *(also unnamed)* Session hygiene | 142–147 | `autonomy` | Its operative half is the `/goal`,`/loop` rule ("do **not** `/clear` mid-run"); REQ-12b names it a docs-owned topic, D-16 places it |

## Deliberate deletion (one, recorded for phase 04's REQ-06 audit)

Line 106 reads: *"The bottleneck in agent-assisted work isn't decomposition — it's losing track of
what each session is doing, and reading its output cold at the end. Four pieces address that:"*

The first sentence moves intact and leads `docs/parallel-work.md`. The connector **"Four pieces
address that:"** is dropped: it is already false in today's README (seven bolded pieces follow it),
and it is section scaffolding for a section being dissolved across three pages. No claim is lost.

## REQ-12 / D-10 — which reference each page must link as source of truth

| Page | Links (as `../plugins/devflow/references/…`) | Normative detail that stays there |
|---|---|---|
| `installation.md` | `hosts.md`, `conventions.md` | Host capability matrix; `## Plugin self-bootstrap` JSON; `## Agent pointer files` merge semantics |
| `providers.md` | `hosts.md` | `## Provider selection and dispatch`, `## Model tiers`, `## Cross-provider safety` — see the REQ-12b note below |
| `execution-model.md` | `plan-format.md`, `verification.md`, `conventions.md` | Wave arithmetic, must_haves field lists, split signals; anchor rules and the smoke-gate procedure; layout, git workflow, secret-scan pattern |
| `provenance.md` | `conventions.md`, `autonomy.md` | Exact trailer syntax and field rules; the authoritative human-gate list |
| `requirements-clarity.md` | `plan-format.md`, `verification.md`, `questioning.md` | `backstop_truths` semantics and tagging rule; abstention procedure |
| `parallel-work.md` | `conventions.md` | `## Parallel workstreams` reconciliation table and non-file hidden edges |
| `review.md` | `adjudication.md`, `oracle.md`, `plan-format.md` | Verdict/disposition vocabularies and ledger rules; bundle and consult mechanics; the revision-gate budget |
| `autonomy.md` | `autonomy.md`, `checkpoints.md` | Status-line grammar, rail semantics, gate-record fields, the gate list |
| `acknowledgements.md` | — (owned outright, REQ-12b) | `NOTICE` remains the legal artifact |

**REQ-12b, corrected at the source (D-17).** REQ-12b listed "providers/model tiers" among topics with
*no reference counterpart*. That was a factual error, not an open choice: `plugins/devflow/references/hosts.md`
carries `## Provider selection and dispatch` (:27) and `## Model tiers` (:60) — it is a counterpart. REQ-12's
rule is conditional ("where a topic has an authoritative contract"), so it fires, and owning provider dispatch
outright would restate normative detail, which REQ-12a calls a defect. REQUIREMENTS.md now records the
correction and PROJECT.md carries it as D-17. Settled, not deferred: `docs/providers.md` summarizes and links
`hosts.md`, and no plan in this phase carries a backstop truth for it.

## Link forms inside `docs/` — measured, not assumed

`check-links.py` resolves a **markdown link against the referring file's own directory only**
(ARCHITECTURE.md → Link checking). Probed on this repo at `e23403c`:

- `[x](../plugins/devflow/references/plan-format.md)` — resolves ✅
- `` `plugins/devflow/references/conventions.md` `` (backticked, multi-base) — resolves ✅
- `[x](blitzos.md)` sibling — resolves ✅
- `[x](plugins/devflow/references/oracle.md)` from `docs/` — **fails**, "target does not exist" ❌

So line 44's `[docs/blitzos.md](docs/blitzos.md)` must become a sibling link when it lands in
`docs/installation.md`. A new page is also invisible to the checker until it is **tracked**
(`git ls-files`), so `git add` the page before treating a green smoke as evidence.

## Gate commands (G1–G4) — run after every commit

```
# G1  smoke (ARCHITECTURE.md ## Smoke) + coverage floor
python3 scripts/validate-plugin.py && python3 -m unittest discover -s tests -v && python3 scripts/check-links.py
# last line must read "0 failures, N references checked" with N >= 140 (162 at phase start)

# G2  SC-03 line cap
wc -l docs/*.md | awk '$2 != "total" && $1 > 250'          # must print nothing

# G3  D-15 no repo path inside a fence on a page this phase writes
ls docs/*.md | grep -vE '/(blitzos|status-contract)\.md$' | xargs -r \
  awk 'FNR==1{f=0} /^[ \t]*(```|~~~)/{f=!f; next} f' \
  | grep -oE '[A-Za-z0-9_.{}-]+(/[A-Za-z0-9_.{}-]+)+\.(md|py|json|yml)' \
  | grep -vE '^(\.planning/|~/)' | sed 's|^{devflow_root}|plugins/devflow|' | sort -u \
  | while read p; do [ -e "$p" ] && echo "D-15 VIOLATION: $p"; done   # must print nothing

# G4  NOTICE byte-identical
git diff --exit-code $(git merge-base main HEAD) -- NOTICE       # must exit 0, print nothing
# no `HEAD` in that command on purpose: `<base> HEAD` compares two commits and is blind to the worktree,
# so an uncommitted edit to NOTICE passes (probed). Omitting HEAD compares the base to the working tree.
```

G3 excludes `blitzos.md` and `status-contract.md` deliberately: `status-contract.md:90` already
carries `{devflow_root}/scripts/flow-fleet.py` inside a fence, and that file must not change.
The fence pattern matches `~~~` as well as ` ``` ` because `check-links.py`'s `_code_fence_mask` masks both
(`^(`{3,}|~{3,})`). Matching only backticks left a proven evasion: a real repo path inside a `~~~` fence lost
checker coverage (reference count unchanged) while G3 printed nothing. Re-probed after the fix — G3 now prints
`D-15 VIOLATION: plugins/devflow/references/conventions.md` for that page, and nothing for the real tree.
The indent class is `[ \t]` rather than ` ` because `_code_fence_mask` matches against the **stripped** line
(`scripts/check-links.py:385`), so a tab-indented fence is masked by the checker; with `^ *` it was invisible
to G3 — re-probed, G3 now flags a repo path inside a tab-indented `~~~` fence.

**Known limit — G3 is not full parity with `_code_fence_mask`.** The checker requires the closing fence to use
the *same* character as the opener; G3's awk toggles on any fence-shaped line, so a `~~~` line appearing inside
a ` ``` ` block inverts the state and every fence boundary after it is backwards — prose gets scanned (noisy)
and fenced content gets skipped (fail-open). No page this phase writes contains a fence of either character, so
it is unreachable from this content. Do not read a clean G3 as proof of parity: if a later phase adds fenced
blocks to `docs/`, port `_code_fence_mask`'s same-character rule into the awk rather than trusting this form.

G3 tests for paths that **exist** in the repo — a fenced path that resolves is coverage this phase
silently removed; an illustrative fake path would have failed the checker in prose anyway.

## Anchor phrases (move completeness)

One distinctive phrase per carved section. Each must end at **0 hits in `README.md`** and **exactly
one file under `docs/`**. All are the paragraph's identifying framing — what it is / why it exists —
which REQ-12a keeps, so REQ-12 compression never legitimately removes one. Verified at `e23403c`:
one hit each in README, none in `docs/`.

| Section | Anchor | Page |
|---|---|---|
| 25–27 | `Codex cloud is not` | installation |
| 42 | `self-bootstrapping` | installation |
| 44 | `company-brain rendering` | installation |
| 29–36 | `bounded repository context` | providers |
| 38–40 | `cost is a property of the plugin` | providers |
| 78 | `fresh-context executor per plan per wave` | execution-model |
| 82 | `phase 5 silently breaks phase 2` | execution-model |
| 84 | `hard size caps` | execution-model |
| 86 | `Environment manifest` | execution-model |
| 88 | `pins your exact stack` | execution-model |
| 92 | `invented styles` | execution-model |
| 116 | `mapped_sha` | execution-model |
| 80 | `unreconstructable` | provenance |
| 96 | `confident sentences` | requirements-clarity |
| 98 | `asked at each cheap moment` | requirements-clarity |
| 100 | `too load-bearing to be wrong` | requirements-clarity |
| 102 | `work nobody asked for` | requirements-clarity |
| 106 | `isn't decomposition` | parallel-work |
| 108 | `never screens` | parallel-work |
| 110 | `fighting over one checkout` | parallel-work |
| 90 | `high-stakes decision` | review |
| 112 | `never force-pushes` | review |
| 114 | `cheapest moment in the whole workflow` | review |
| 118 | `same-model review reports identically` | review |
| 120 | `doesn't also get to rule` | review |
| 122 | `give the ledger its weight` | review |
| 124 | `grades its own homework` | review |
| 128 | `machine-checkable status line` | autonomy |
| 130–134 | `Sweep the fleet` | autonomy |
| 136 | `honor it all night` | autonomy |
| 138 | `answer from anywhere` | autonomy |
| 140 | `never auto-proceed` | autonomy |
| 144–147 | `cheap convenience` | autonomy |
| 151 | `exogenous abstention` | acknowledgements |
| 153 | `oracle source files` | acknowledgements |
| 155 | `graph-engineering framing` | acknowledgements |
| 157 | `specification discipline` | acknowledgements |
| 159 | `foreman and crew` | acknowledgements |
| 161 | `four-session manual relay` | acknowledgements |
| 163 | `AgentOS blueprint` | acknowledgements |
| 165 | `readiness-over-sleeps` | acknowledgements |

Check form: `grep -c '<anchor>' README.md` → `0`, and `grep -rl '<anchor>' docs/` → exactly the one page.

## Waves — why this phase is strictly serial

Every plan modifies `README.md`. Under `plan-format.md` a shared mutable file is a **hidden edge**:
same-wave plans must have disjoint `files_modified`, and two executors carving different sections of
one README concurrently would collide on the file and, worse, could each leave a commit where the
same prose lives in README and a `docs/` page — the exact state D-14 forbids. There is no safe
parallel wave here. Plans run 02-01 → 02-05, one per wave, each depending on the last; page contents
are independent, `README.md` is not, and correctness wins.
