# Phase 03 plan check — round 2

## Verdict

ISSUES (4)

All five round-1 issues are resolved, each confirmed by running the revised command rather than reading
it. The revision introduced four new defects, two of them substantive: 03-04's config resolver now reds
on the exact key its own action tells the executor to write, and 03-03's sentence reconstructions green
vacuously if the pinned blob is ever unreachable — the precise failure mode the plan guards against
elsewhere and forgot here.

## Round 1 issues

### 1. 03-02 link-count arithmetic — **RESOLVED**

Truth #2 and task 1's verify now use the sibling-only class `\]\([A-Za-z0-9_-]+\.md\)`. Built a mock
index in a scratch tree — 11 sibling entries plus the required `[repo README](../README.md)`
back-pointer, 12 files in `docs/`:

```
ls docs/*.md | wc -l                                       => 12
sibling-only  '\]\([A-Za-z0-9_-]+\.md\)' | sort -u | wc -l  => 11   <- truth #2
permissive    '\]\([^)]+\.md\)'          | sort -u | wc -l  => 12   <- round-1 defect, reproduced
arithmetic target $(( $(ls docs/*.md | wc -l) - 1 ))        => 11
grep -c '](README.md)'   => 0    grep -c '](docs/'  => 0    grep -c '`docs/' => 0
grep -cE '\]\([A-Za-z0-9_-]+\.md\) — .{20,}'                => 11   <- truth #6, same class
per-page loop                                               => prints nothing
```

The two truths that must count the same set (#2, #6) now do. `](../README.md)` cannot match either
class (`](` is never followed by a character in `[A-Za-z0-9_-]`), and it also cannot match truth #4's
literal `](README.md)`. The contradiction is gone.

### 2. 03-04 config-key verify — **RESOLVED** (but see New finding 1)

The dotted `grep -rF` is gone, replaced by a Python resolver that checks `.planning/config.json` first
(presence, not truthiness — `deploy.tool` and `git.upstream` are both `null` and both resolve) then
falls back to a line naming the block *and* the leaf in key form. Run verbatim against this tree it
**prints nothing**: eleven real keys resolve, all four `PROBES` are rejected. Falsifiability confirmed
by construction, not by assertion.

`.planning/config.json` exists and is tracked (254 bytes; `mode`, `commit_docs`, `agents.provider`,
`deploy.tool`, `git.{base,origin,upstream,branch}`). The keys not in the file resolve through the doc
fallback against real lines — `autonomy.{max_iterations,max_repeats,max_hours}` at
`plugins/devflow/references/autonomy.md:53` and `docs/status-contract.md:34`, `agents.models` at
`plugins/devflow/references/hosts.md:69`. The round-1 complaint that a correct implementation failed
its own verify no longer holds.

### 3. 03-03 byte-identity ungraded — **RESOLVED** (but see New finding 2)

All three reconstructions were extracted from the YAML, unescaped, and executed. Each produces a
**non-empty** string, each is the exact sentence §2 names, and each discriminates correctly today —
found in `README.md`, **not** found on the destination page, which is the right answer before the move:

```
n=11  kb=220
L3s3  len 273  "20 shared Agent Skills and 11 subagents across ~220KB of prompt content — but nothing
               loads it all: skills load progressively at ~1–5k tokens each, and heavy work runs in
               bounded native subagents or, when explicitly selected, through the other provider's
               authenticated CLI."
               in README: YES    on docs/execution-model.md: NO
L5    len 163  "No Node runtime and no hooks. \"Ship\" is a real pipeline: harden → UAT → human
               sign-off → production, orchestrated with [Aspire](https://aspire.dev) + azd on Azure."
               in README: YES    on docs/execution-model.md: NO
L7s1  len  76  "DevFlow runs as skills inside the interactive host rather than replacing it."
               in README: YES    on docs/providers.md: NO
```

`No Node runtime and no hooks.` — the sentence round 1 showed could be dropped with every truth still
green — is now inside the L5 reconstruction and cannot be dropped silently. The two `sed` extractions
that could plausibly mis-fire (`s/^.*\(20 shared Agent Skills\)/\1/` and
`s/^\*\*Orchestrator-agnostic\.\*\* //`) both hit; a non-matching `sed` returns the whole line, so no
`sed` path yields an empty pattern. The only empty path is the blob itself — New finding 2.

Also re-ran: the D-14 per-commit loop (`D-14 UNPROVEN: no commit carries DevFlow-Plan: 03-03` — the
`shas` guard works), the `## Install`-down diff (silent), and §3's four recorded-claim commands (all
exit 0).

### 4. 03-01 frontmatter REQ-03 — **RESOLVED**

`requirements: [REQ-04]`. Coverage still closes both directions: the union across the four plans is
`{REQ-01, REQ-02, REQ-03, REQ-04, SC-01, SC-04}` — exactly ROADMAP row 03, nothing more, nothing less.
REQ-03 is still carried by 03-03 and 03-04. `requirements` is non-empty in all four, as the format
demands.

### 5. 03-01 subdirectory verify — **RESOLVED**

Now two commands, and both cwd cases are genuine — verified directly:

```
(cd docs && git rev-parse --show-toplevel)  => /home/brianf/dev/devflow      <- real subdirectory case
d=$(mktemp -d); (cd "$d" && git rev-parse --show-toplevel)
    => fatal: not a git repository ... exit 128                             <- real outside-any-repo case
```

The third fixture (`mktemp -d` + `git init -q .` + copy only the guard) is the right shape for the
fail-closed case: it isolates the *loader* failing from the *root resolution* failing, which an empty
dir alone would not.

## Gate command results

Run against the working tree at `flow/phase-02-docs-carve`, HEAD `c8a5d3c`.

**G1 — smoke + coverage floor** — exit 0

```
Plugin OK: 20 shared skills, 11 Claude agents, both hosts valid.
Ran 92 tests in 1.628s
OK (skipped=2)
0 failures, 179 references checked
```

N = 179, unchanged by the phase-02 PR fixes — §8's baseline is still correct.

**G2 — SC-03 line cap** — exit 0, printed nothing.

**G3 — fence guard** — exit 2, still cannot run (`scripts/check-fenced-paths.py` does not exist; §8
says so, 03-01 creates it). Ran its *logic* instead by importing `_frontmatter_mask` / `_code_fence_mask`
from `scripts/check-links.py` and applying 03-01's stated `SCOPE`, `FROZEN` and token regex:

```
SCOPE files=10  fenced lines=12  violations=0
scope: README.md docs/acknowledgements.md docs/autonomy.md docs/execution-model.md
       docs/installation.md docs/parallel-work.md docs/provenance.md docs/providers.md
       docs/requirements-clarity.md docs/review.md
```

**F = 10, L = 12, 0 violations** — 03-01 task 1's predicted summary line survives the phase-02 PR fixes
(`installation.md` grew but added no fence). 03-02's "now covering 11 files" is also right: 12 pages in
`docs/` minus 2 frozen, plus `README.md`.

**G4 — NOTICE byte-identical** — exit 0, printed nothing.

**G5 — README shape + SC-01** — reports the pre-rebuild shape, as §8 predicts:

```
4
## Install
## Commands
## Flow
## Acknowledgements
SC-01-OK
```

**G6 — command table byte-identical** — diff exit 0, printed nothing; row count `20`.

**G7 — move completeness (all six anchors)** — every anchor 1 hit in `README.md`, 0 files under `docs/`:

```
nothing loads it all             :: README=1 :: docs=[]
azd on Azure                     :: README=1 :: docs=[]
rather than replacing it         :: README=1 :: docs=[]
without screen-scraping          :: README=1 :: docs=[]
bounded peer role                :: README=1 :: docs=[]
Native subagents are the default :: README=1 :: docs=[]
```

**Reference-count arithmetic, measured rather than argued.** Cloned the repo to a scratch tree, dropped
in an eleven-entry index with the mandated `../README.md` back-pointer, and ran the checker:

```
baseline                                  0 failures, 179 references checked
+ docs/README.md (11 siblings + backlink) 0 failures, 191 references checked
+ 03-03 deleting README line 7            0 failures, 189 references checked
```

So 03-02's `N >= 190` floor clears at 191, 03-03's "lands near 188" is 189, and 03-04's `N >= 190` needs
its own new links to recover the two 03-03 drops — which `## Documentation` (+1) and `## Configuration`
(+2) supply. The §9 wave argument holds as arithmetic.

## Staleness against the phase-02 PR fixes

**One real staleness, narrative only — every check still passes.** `README.md` changed at `e08ff1c`:
line 3 now reads `11 subagents` / `~220KB`. The worktree README is no longer `5ffe726:README.md`
(4387 bytes vs 4386; 61 lines both). What is now false:

- OPENING-MAP header — "**61 lines / 4386 bytes**" is off by one byte.
- OPENING-MAP §2, L3s3 row — quotes the sentence as `9 subagents across ~165KB…`.
- OPENING-MAP §4 — "L3s3 says … 9 subagents across ~165KB", and "Moving the sentence unchanged would
  make a `docs/` page the authority on two false numbers". It would not; phase 02's PR already fixed it.
- 03-03 truth #4 — "(11 at phase start, README said 9)" and "(~220KB at phase start, README said ~165KB)".
- 03-03 truth #4 / task 1 — "both outputs are logged as a deviation in the SUMMARY". There is no longer
  a deviation to log: moving current README's L3s3 verbatim needs no numeral change. A SUMMARY recording
  one would tell phase 04's REQ-06 audit that phase 03 edited a moved sentence when it did not.

**Why no check breaks.** Verified directly: `5ffe726:README.md` line 3, with exactly the two §4
substitutions applied, is **byte-identical** to the current line 3; and the whole-file diff between
`5ffe726:README.md` and the worktree is that one line. So the three reconstructions still resolve to
what the executor will move, the 345/346-byte opening pin still measures 345 (the three kept sentences
are untouched by the numeral fix), the `## Install`-down diff is silent, G6 is clean, and 03-04's
`sed -n '53,54p'` and `sed -n '59p;61p'` line pins all still `grep -qxF` present.

**Everything else survived the PR fixes.** §3's four recorded-claim commands all still exit 0 —
`providers.md` kept "Native workers are used unless" and "the command flag wins" despite dropping the
role enumeration; `autonomy.md` kept "machine-checkable status line" despite dropping the gate list.
Destination heading positions are unchanged (`execution-model.md`: `## Graph execution` first,
`## Design constraints` last; `providers.md`: `## Provider selection` first), so 03-03's "above/after"
placements are still accurate. `ls docs/*.md` is 11, matching §7. G1's N is still 179 —
`installation.md`'s new back-link did not move it.

## New findings

1. **03-04 | task 2 action vs. verify — the resolver reds on the key the action tells you to write.**
   The action says to name `agents.models.<role>`; the verify says "Set `KEYS` to exactly the keys you
   wrote". Run with that key, the resolver prints `INVENTED KEY: agents.models.<role>` — yet it is real
   and documented at `plugins/devflow/references/hosts.md:69` and `docs/status-contract.md:34`. This is
   round-1 issue 2 in miniature: a correct implementation fails its own verify. The cause is the
   three-segment branch — `leaf_re` builds `parts[0] + '.' + parts[-1]`, i.e. `agents.<role>`, a string
   that appears nowhere. Measured:
   ```
   agents.models            True     agents.models.<role>     False   <- action tells you to write this
   agents.models.executor   True     agents.models.planner    False
   git.branch               True     agents.models.reviewer   False
   ```
   `agents.models.executor` passes only by luck — `hosts.md:74` happens to carry
   `"agents": { "provider": "native", "models": { "executor": "opus" } }` on one line, so the leaf and
   the block co-occur. **Fix:** either have the action name `agents.models` (two segments, which
   resolves) and say so, or join all but the last segment in `leaf_re`.

2. **03-03 | truth #5 and both move verifies — an unreachable blob greens all three checks.**
   There is no non-empty guard on `$exp`. If `git show 5ffe726:README.md` ever fails, every
   reconstruction is `""` and `grep -qF ""` matches any non-empty file. Demonstrated against a dead SHA:
   ```
   exp length: 0
   grep -qF "$exp" docs/execution-model.md || echo 'L5s1+L5s2 NOT BYTE-IDENTICAL'
       => printed nothing, on a page where grep -cF 'No Node runtime and no hooks.' is 0
   ```
   This is not hypothetical: `5ffe726` is reachable only from `flow/phase-02-docs-carve` and its remote,
   and truth #5 is a `must_have` the **verifier** re-runs — including after this branch is squash-merged
   and deleted, which is exactly when the fix for round-1 issue 3 stops grading anything. The plan
   already reasons about this defect class one truth earlier ("The `shas` guard is not decoration: a
   zero-iteration loop prints nothing, which this truth would otherwise read as a pass") and then omits
   the same guard here. **Fix:** `[ -n "$exp" ] || echo 'RECONSTRUCTION EMPTY'` before each `grep -qF`,
   in truth #5 and in both task verifies; and pin blob `38b2bc0` alongside the commit-ish, as round 1
   already recommended and no plan yet does (`grep -c 38b2bc0` is 0 in all four plans).

3. **03-04 | task 2 `PROBES` does not probe the branch it was written to defend.** All four probes are
   dotted, but the single-segment branch skips the parent check entirely — so bare `models` and
   `provider` both resolve as "defined" (measured), on nothing more than a backticked word somewhere in
   `docs/`. That is the same unfalsifiability round 1 named for `grep -rqF mode`, surviving in the one
   branch the probes never exercise, while the plan claims "the `PROBES` half is the point". Low impact
   — the only bare keys the action tells the executor to write are `mode` and `commit_docs`, both real —
   but the claim is stronger than the check. **Fix:** add one single-segment invention (e.g. `verbose`,
   which correctly returns False today) to `PROBES`.

4. **03-04 | truth #5 and task 1 grade the diagram's content but not its fence.** The check is
   `sed -n '53,54p'` — the two ASCII lines — while the fence delimiters live on 52 and 55. An executor
   who relocates the diagram unfenced passes truth #5, passes G3 (the diagram contains no repo path, so
   the guard stays silent either way), and ships a broken render. **Fix:** widen the range to
   `sed -n '52,55p'`, which grades all four lines with the same `grep -qxF` loop.

## Notes

- Re-verified from round 1 and still clean: serial graph 1→2→3→4 with `wave = max(dep)+1` and no shared
  wave; `backstop_truths: []` present and correctly empty (zero `[NEEDS CLARIFICATION]` markers in
  REQUIREMENTS.md); tasks 3/2/3/3 all `type="auto"` with `autonomous: true` and the single SC-04
  `<human-check>` correctly inside 03-04 task 3's `<verify>`; four size notes naming D-11.
- 03-04 truth #6 now says out loud that the SC-04 proxy does not close the human check — round 1's note
  is addressed.
- All four frontmatters were escape-scanned for invalid YAML double-quote escapes (the embedded code
  fence in 03-03 truth #5 is the risk): **0 candidates** in all four. PyYAML is unavailable here, so
  this is a hand-rolled scan, not a full parse.
- Importing `scripts/check-links.py` via importlib executes nothing — AST shows only a docstring, nine
  regex/tuple constants, and defs, with `main()` behind `if __name__ == '__main__'`. Both
  `_frontmatter_mask(lines)` and `_code_fence_mask(lines, skip_mask=None)` exist with 03-01's signatures.
- Unrelated repo defect, worth a look before 03-03 edits the file: `docs/providers.md` `## Model tiers`
  now states the executor rationale **twice** (leftover from `cc4f069`). Phase 04's content audit would
  likely charge it to phase 03.
- `$(find plugins/devflow/{agents,skills,references,templates} …)` relies on bash brace expansion; under
  `sh` the `kb` arithmetic breaks. Fine for a bash executor, worth knowing.

---

## Round 3 — orchestrator verification (budget spent, no fourth checker round)

All four round-2 findings plus the staleness were verified **by execution**:

| Fix | Verified | Result |
|---|---|---|
| 1 — config-key resolver reds on a real key | grep for the corrected `leaf_re` | applied |
| 2 — unreachable blob greens the checks | ran the reconstruction against the live blob AND a dead SHA | live: 539 chars, matches README line 3 exactly. Dead SHA: `RECONSTRUCTION EMPTY` fires. Unguarded control confirmed matching an arbitrary file — the fail-open, closed |
| 3 — PROBES miss the single-segment branch | `verbose` probe present | applied |
| 4 — diagram fence ungraded | `sed -n '52,55p'` present, `53,54p` gone | applied |
| 5 — staleness | inspected every remaining numeral hit | correct: they survive only as the `sed` reconciling the pinned blob against the corrected README, and as accurate historical narrative. The deviation instruction is gone |

Note on fix 5, which came back better than specified: the revision kept the numeral
substitution (necessary — the pinned blob predates phase 02's PR fix) and reframed it
as reconciliation rather than a deviation, instead of deleting it as instructed. That
is the correct reading.
