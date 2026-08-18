# Phase 03 — opening disposition, index inventory, and gate commands

Authoritative and reviewable **before any prose moves**, the same contract
`.planning/phases/02-carve-out-docs/MAPPING.md` served for phase 02. Phase-start source:
`README.md` at `5ffe726` (blob `38b2bc0`), **61 lines / 4386 bytes**, four `##` sections.

> **Blob vs. worktree.** Phase 02's PR review corrected line 3's two numerals at `e08ff1c`, so the
> worktree README is **61 lines / 4387 bytes** and the whole-file diff against `38b2bc0` is that one
> line (measured). Every check that *reconstructs* prose from phase start pins the **blob** by object id
> rather than reaching it through `5ffe726` — which is reachable only from this branch and its remote —
> and re-applies the two substitutions where needed (§4). The `diff`-shaped checks (G6, 03-03 truth #7)
> keep the commit-ish: an empty left-hand side makes a `diff` loud, where it makes a `grep -qF` silent.

> **Locate by anchor phrase, never by line number.** README changes as each plan lands.

## 1. Disposition of every phase-start README line

| Lines | Content | Disposition | Plan |
|---|---|---|---|
| 1 | `# DevFlow` | **STAYS** | — |
| 3 | positioning paragraph (3 sentences) | split — see §2 | 03-03 |
| 5 | runtime/ship paragraph (3 sentences) | split — see §2 | 03-03 |
| 7 | orchestrator-agnostic paragraph (5 sentences) | split — see §2 | 03-03 |
| 9–23 | `## Install` + both install blocks | **STAYS**, untouched (REQ-03) | — |
| 25–48 | `## Commands` + 20-row table | **STAYS, byte-identical** (REQ-02, gate G6) | — |
| 50 | `## Flow` heading | **REMOVED** — not one of REQ-01's six sections | 03-04 |
| 52–55 | ASCII flow diagram (fenced) | **STAYS**, byte-identical, relocated under `## Quick start` | 03-04 |
| 57 | `## Acknowledgements` heading | **RENAMED** `## License and acknowledgements` (REQ-01 slot six) | 03-04 |
| 59 | acknowledgements pointer line (page + `NOTICE`) | **STAYS** byte-identical (REQ-07) | 03-04 |
| 61 | `MIT licensed — see LICENSE.` | **STAYS** byte-identical, still last | 03-04 |
| — | *(new)* `## Quick start`, `## Configuration`, `## Documentation` | **ADDED**, written fresh (D-18) | 03-04 |

## 2. The three opening paragraphs, sentence by sentence (D-20)

**The rule: a sentence that stays, stays byte-identical.** The condensed opening is built from three
sentences of the phase-start README, unreworded — so "condense to 2–3 sentences" never becomes a
licence to rewrite. Everything displaced either **MOVES** intact to the `docs/` page that owns the
topic, or is **RECORDED** in §3 against a destination that already carries the claim.

| # | Sentence (identifying phrase) | Disposition | Lands as |
|---|---|---|---|
| L3s1 | `Token-efficient spec-driven development for Claude Code and local Codex clients.` | **STAYS** — opening sentence 1 | — |
| L3s2 | ``Fresh-context subagents, wave-parallel execution, plan checking, independent diff review, goal-backward verification that abstains rather than guessing, and durable `.planning/` state.`` | **STAYS** — opening sentence 2 | — |
| L3s3 | `20 shared Agent Skills and 11 subagents across ~220KB… nothing loads it all…` | **MOVES** → `docs/execution-model.md` | new `## Context economy`, first H2 on the page. Moves **verbatim** — the numerals are already correct in the worktree; see §4 |
| L5s1 | `No Node runtime and no hooks.` | **MOVES** → `docs/execution-model.md` | with L5s2 |
| L5s2 | `"Ship" is a real pipeline: harden → UAT → human sign-off → production, orchestrated with [Aspire](https://aspire.dev) + azd on Azure.` | **MOVES** → `docs/execution-model.md` | new `## Ship pipeline`, last H2 on the page |
| L5s3 | ``Claude invokes skills as `/flow-*`; Codex invokes the same skills as `$flow-*`.`` | **STAYS** — opening sentence 3 | — |
| L7s1 | `**Orchestrator-agnostic.** DevFlow runs as skills inside the interactive host rather than replacing it.` | **MOVES** → `docs/providers.md` | new `## Orchestrator-agnostic`, first H2 on the page; the bold run-in label becomes the heading (phase-02 precedent), the sentence body moves intact |
| L7s2 | `Native subagents are the default.` | **RECORDED** (§3) | — |
| L7s3 | ``Cross-provider work is opt-in via `--provider claude|codex` … `claude -p` or `codex exec` only for that bounded peer role.`` | **RECORDED** (§3) | — |
| L7s4 | `What DevFlow adds is *legibility*: … without screen-scraping.` | **RECORDED** (§3) | — |
| L7s5 | ``Contract: [`docs/status-contract.md`](docs/status-contract.md).`` | **RECORDED** (§3) | — |

Resulting opening — exactly L3s1 + L3s2 + L5s3, one paragraph, above `## Install`.

## 3. Recorded, not moved — four sentences whose claims already live in `docs/`

D-20 says the displaced prose is not deleted. These four are not: **every claim they carry is already
stated on a `docs/` page**, and moving the sentences too would put one fact in two files — which
`ARCHITECTURE.md` → Principles calls a defect ("docs are pointers, never copies") and D-14 forbids as
a state. The sentences are dropped; the claims have destinations, cited here for phase 04's REQ-06
audit. Same mechanism as phase 02's one deliberate deletion, and each row is checkable:

| Sentence | Claim already stated at | Check (must exit 0) |
|---|---|---|
| L7s2 | `docs/providers.md` `## Provider selection` — "Native workers are used unless a delegating skill receives `--provider claude|codex`"; `docs/status-contract.md:137` — "uses native subagents by default" | `grep -q 'Native workers are used unless' docs/providers.md` |
| L7s3 | `docs/providers.md` `## Provider selection` (flag, saved `agents.provider`, flag wins, both CLIs authenticated); `docs/status-contract.md:137` (`claude -p` / `codex exec` reserved for a bounded cross-provider role); dispatch mechanics stay in `hosts.md`, which the page links (REQ-12a) | `grep -q 'the command flag wins' docs/providers.md && grep -q 'codex exec' docs/status-contract.md` |
| L7s4 | `FLOW:` line → `docs/autonomy.md` lead paragraph; state in files → `docs/execution-model.md` `## State`; boards without screens → `docs/parallel-work.md` `## Fleet board` ("It reads files, never screens") | `grep -q 'machine-checkable status line' docs/autonomy.md && grep -q 'never screens' docs/parallel-work.md` |
| L7s5 | `docs/parallel-work.md` `## Fleet board` links `status-contract.md`; `docs/README.md` indexes it (REQ-04) | `grep -q 'status-contract.md' docs/parallel-work.md` |

## 4. The two numerals in L3s3 — already corrected upstream; L3s3 moves verbatim

At blob `38b2bc0` L3s3 said "20 shared Agent Skills and 9 subagents across ~165KB of prompt content",
and both of those were false. **Phase 02's PR review already fixed them at `e08ff1c`**: the worktree
README now reads `11 subagents` / `~220KB`, which is what the repo measures — **20** skill dirs,
**11** agent files (`ls plugins/devflow/agents/*.md | wc -l`), and **221 KiB** of prompt content
(`find plugins/devflow/{agents,skills,references,templates} -name '*.md' -type f -exec cat {} + | wc -c`
→ 227016 bytes ÷ 1024, floored to the nearest 5 → `~220KB`).

So there is **nothing to correct on the move and no deviation to log**. L3s3 moves verbatim like every
other moved sentence. The executor still re-runs both commands and confirms they agree with what README
says (`11`, `220`); a disagreement is a real finding to stop and report, not a licence to edit a sentence
this phase is only moving. A SUMMARY that recorded a deviation here would tell phase 04's REQ-06 audit
that phase 03 edited a moved sentence when it did not.

The `sed "s/9 subagents/$n subagents/; s/~165KB/~${kb}KB/"` in 03-03's reconstruction checks is not a
licence either: it exists solely because the pinned blob `38b2bc0` predates `e08ff1c`. Verified — blob
line 3 with exactly those two substitutions is byte-identical to the worktree's line 3.

## 5. Anchor phrases (move completeness)

Each must end at **0 hits in `README.md`** and **exactly one file under `docs/`**. Verified at
`5ffe726`: one hit each in README, none in `docs/`.

| Chunk | Anchor | Page |
|---|---|---|
| L3s3 | `nothing loads it all` | `docs/execution-model.md` |
| L5s1+L5s2 | `azd on Azure` | `docs/execution-model.md` |
| L7s1 | `rather than replacing it` | `docs/providers.md` |

Check form: `grep -cF '<anchor>' README.md` → `0`, and `grep -rlF '<anchor>' docs/` → exactly one page.
Recorded sentences (§3) have their own anchors — `without screen-scraping`, `bounded peer role` — which
must reach **0 hits in README and 0 in `docs/`**: they are dropped sentences, not moved ones, and a hit
in `docs/` would mean the executor duplicated a fact instead of recording it.

## 6. Target README shape (REQ-01) — exactly six `##`, in this order

```
# DevFlow            + the 3-sentence opening (L3s1, L3s2, L5s3)
## Install           unchanged: ### Claude Code, ### Codex CLI, app, or IDE (### is not ##)
## Quick start       fresh (D-18) — the first-run walkthrough + the ASCII diagram
## Commands          byte-identical 20-row table (REQ-02)
## Configuration     fresh (D-18) — --provider + .planning/config.json keys, links out
## Documentation     links docs/README.md (the index)
## License and acknowledgements   the phase-02 pointer line + the MIT line, both byte-identical
```

`## License and acknowledgements` is REQ-01's "License/Acknowledgements" slot, in the repo's
sentence-case heading style. The six headings are enumerated in 03-04's truths, so the name is pinned
rather than left to a grep for a slash.

## 7. `docs/README.md` inventory (REQ-04)

After this phase `ls docs/*.md` lists **12** files, so the index carries **11** links — every page
except itself, `12 − 1`. Sibling link form (`[providers.md](providers.md)`), never `docs/providers.md`,
because a markdown link resolves against the referring file's own directory only. Every entry is a
clickable markdown link with a one-line *what it answers* on the same line — never a bare backticked
path (phase-02 house rule).

`installation.md`, `providers.md`, `execution-model.md`, `requirements-clarity.md`, `review.md`,
`parallel-work.md`, `autonomy.md`, `provenance.md`, `acknowledgements.md`, `blitzos.md`,
`status-contract.md`. Ordering and grouping are the executor's discretion (CONTEXT.md).

## 8. Gate commands (G1–G7) — run after every commit

G1–G4 are phase 02's, unchanged in meaning; **G3 is now a committed script instead of the awk**, per
D-19. G5–G7 are new to this phase.

```
# G1  smoke (ARCHITECTURE.md ## Smoke) + coverage floor
python3 scripts/validate-plugin.py && python3 -m unittest discover -s tests -v && python3 scripts/check-links.py
# last line "0 failures, N references checked", N >= 179 at EVERY commit of this phase (179 at start)

# G2  SC-03 line cap
wc -l docs/*.md | awk '$2 != "total" && $1 > 250'          # must print nothing

# G3  D-15 fence guard — parity with check-links.py's _code_fence_mask (D-19), from 03-01 onward
python3 scripts/check-fenced-paths.py                      # exit 0, "0 violations, F files scanned, L fenced lines"

# G4  NOTICE byte-identical (no HEAD in the command on purpose — it must see the worktree)
git diff --exit-code $(git merge-base main HEAD) -- NOTICE

# G5  README shape + SC-01, from 03-04 onward
grep -c '^## ' README.md                                   # 6
grep '^## ' README.md                                      # the six of §6, in that order
[ "$(wc -l < README.md)" -le 110 ] && [ "$(wc -c < README.md)" -le 14000 ] && echo SC-01-OK

# G6  REQ-02 command table byte-identical to phase start
diff <(git show 5ffe726:README.md | sed -n '/^| Loop | Command | Does |$/,/^$/p') \
     <(sed -n '/^| Loop | Command | Does |$/,/^$/p' README.md)          # must print nothing
sed -n '/^| Loop | Command | Does |$/,/^$/p' README.md | tail -n +3 | grep -c '^| '   # 20

# G7  D-20 move completeness (§5), per anchor
grep -cF '<anchor>' README.md        # 0
grep -rlF '<anchor>' docs/           # exactly the one page named in §5
```

All seven were run against the phase-start tree while writing this file: G1 `0 failures, 179
references checked`; G2, G4, G6, G7 silent/clean; G5 reports the pre-rebuild shape (4 headings) as
expected. G3's script does not exist yet — 03-01 creates it, which is why 03-01 is wave 1.

## 9. Waves — strictly serial, and why

Four plans, four waves, `03-01 → 03-02 → 03-03 → 03-04`. Two of the edges are the obvious kind and
two are worth stating, since `plan-format.md` says never to sequence plans by the order they were
written:

- **03-01 → everything.** D-19 requires the fence guard at parity *before* any fenced block lands
  under `docs/`, and every later plan runs it as gate G3. Later plans consume the script.
- **03-02 → 03-03.** Their `files_modified` are disjoint (`docs/README.md` vs `README.md` +
  two pages), so this is not a file collision — it is the **reference-count invariant**. G1 requires
  `N >= 179` at every commit; 03-03 removes two counted references from README (the
  `docs/status-contract.md` link and its backticked token) and adds none, so run before the index it
  would drop the count to 177 and either break its own gate or force a weaker floor. Landing the
  index first (+11) makes `N >= 179` true at every commit of the phase and keeps "a falling count
  means something was dropped" a usable signal. Parallelising these two buys one wave and costs the
  phase's sharpest anchor.
- **03-03 → 03-04.** Both write `README.md`. A shared mutable file is a hidden edge; same-wave plans
  must have disjoint `files_modified`.

## 10. SC-04 — honestly, a human check with one mechanical proxy

"A first-time reader goes from the top of README to a running `/flow-new` without opening `docs/`" is
not command-provable: no command reads like a first-time reader. What *is* provable is the necessary
condition — that Quick start names the whole first-run sequence in order, in commands that exist, with
no `docs/` link needed to know what to type. 03-04 carries that as a truth **and** carries the reader
half as a batched `<human-check>`. The proxy does not establish SC-04 on its own and is not written as
if it does; do not let a green proxy close the human check.
