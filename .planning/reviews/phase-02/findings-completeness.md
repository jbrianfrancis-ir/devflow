# Findings — completeness

Lens: ARCHITECTURE (completeness and shape). Diff: `main...origin/flow/phase-02-docs-carve`.
Source of truth for "before": `git show 22dfdc7:README.md` (167 lines; byte-identical to `e23403c:README.md`,
the blob MAPPING.md cites — verified with `git diff 22dfdc7:README.md e23403c:README.md` → empty).

## Summary

1 blocking, 5 should-fix, 3 nit

## Content accounting

**Method — prose first, mapping second.** I extracted the 167-line original and the new corpus
(README 61 lines + the nine `docs/` pages, 170 lines) and split every non-blank original line into
sentence-level fragments (≥25 chars, whitespace-normalised), then tested each fragment for verbatim
presence anywhere in the new corpus. 39 fragments failed the verbatim test; I read all 39 by hand and
classified each. Only then did I check the result against MAPPING.md.

Of the 167 lines: 62 blank, 105 carrying content. Disposition as actually observed in the tree:

| Bucket | Original lines | Verified how |
|---|---|---|
| Stayed in README, byte-identical | 1–7, 9, 11–23, 46–69, 71, 73–76, 167 | present in the new 61-line README |
| Moved intact (whitespace/label form aside) | 25–27, 29–40, 42, 44, 78, 80, 82, 84, 86, 88, 92, 94–102, 104, 106 (lead), 108, 112, 116, 118, 124, 126–134, 136, 140, 142–147, 151–165 | present in the named page |
| Moved with REQ-12a compression, detail traced to a linked reference | 90, 110, 114, 120, 122, 138 | see below |
| Deliberately deleted | 106 connector only | see §Deliberate deletion |
| **Unaccounted for** | **none** | — |

**No load-bearing sentence is in neither place.** The 39 verbatim misses break down as:

- **26 are bold-run-in → `##` heading conversions.** `**Graph execution** (…): a phase's plans…`
  became `## Graph execution` + the same sentence. Structural, not substantive. MAPPING's claim holds
  for all of these.
- **7 are link-rewrites or link-insertions** — an inline `(plugins/devflow/references/plan-format.md)`
  parenthetical replaced by a trailing "…are specified in [`plan-format.md`](…)" sentence, or
  `ARCHITECTURE.md` promoted to `.planning/ARCHITECTURE.md` (an improvement). No claim changes.
- **6 are genuine REQ-12a compressions.** I checked each dropped detail against the reference the page
  links, at the branch head:
  - L114 "the same **3-round** revision budget" → `plan-format.md:41` "max 3 iterations". Covered.
  - L120 verdict/disposition vocabularies (`COULD NOT DETERMINE`, `PENDING OWNER`, …) →
    `adjudication.md`. Covered (`grep -c` hits 1 and 2).
  - L122 "the same anchor standard `verification.md` already demands, because re-reading the code…is
    circular" → `adjudication.md:29` carries the rule *and* the rationale. Covered.
  - L110 `STATE.md`/`config.json` branch-local, `JOURNAL.md`/`LEARNINGS.md` unions, pins single-writer
    → `conventions.md` → Parallel workstreams, linked. Covered.
  - L138 "and the reason the rest can stay prose" → dropped outright, in neither place. Nit N-3.
  - L90 the oracle engine fallback and the ≤10-line verdict cap → `oracle.md:10` ("always works,
    nothing to install") and `oracle.md:29` ("≤10 lines"). Technically covered, but see SF-1: the
    strings "no install required", "chat UI", "10-line" and "advisory verdict" now appear **zero**
    times anywhere under `docs/`.

So: MAPPING.md's line-by-line disposition survives the test. I found no row where the prose says
something different from what the tree does. The one thing MAPPING does not disclose is that
`docs/autonomy.md` **adds** prose that was never in the README (see N-2).

## Deliberate deletion

**Confirmed deleted, correctly recorded, and the right call.**

- Deleted: `grep -c "Four pieces address that"` → 0 in `README.md`, 0 across `docs/`.
- Recorded: MAPPING.md §"Deliberate deletion (one, recorded for phase 04's REQ-06 audit)", with the
  reason stated (already false — seven bolded pieces followed it; and it is scaffolding for a section
  being dissolved across three pages). 02-04-PLAN.md carries it too.
- Lead sentence survives intact at `docs/parallel-work.md:3`.
- Judgment: dropping it was right. It was a counted forward-reference to a count that had already
  drifted, and after the carve the number is 2, not 4 or 7. Keeping it would have required inventing a
  new number for a page whose contents are set by REQ-05, not by the sentence.

There is exactly one such deletion, and it is the only one. Nothing else was dropped without a home —
except the L138 clause in N-3, which was *not* recorded and should have been.

## Findings

### [blocking] `docs/acknowledgements.md` renders as one paragraph — the eight upstream credits collapse

**What is wrong.** The move stripped every blank line between the eight acknowledgement paragraphs.
Original README lines 151–165 alternate paragraph / blank / paragraph. The page is 10 lines:

```
1  # Acknowledgements
2  (blank)
3–10  the eight paragraphs, consecutive, no separators
```

In Markdown, consecutive non-blank lines are one paragraph. On GitHub this page renders as a single
undifferentiated ~4,500-character block.

**Concrete scenario.** A maintainer of one of the credited projects — say Dzazaleo, whose
`adversarial-review-skills` attribution is original line 161 — opens
`github.com/jbrianfrancis-ir/devflow/blob/main/docs/acknowledgements.md` to check how their work is
credited. They cannot locate their attribution: GSD Core, oracle, Kopadze, Spec Kit, r/ClaudeCode,
adversarial-review-skills, AgentOS, and agent-scripts run together as one wall of prose with no
visual boundary between one project's credit and the next. Before the carve, each was a separate
paragraph on the repo front page.

**Why the phase's own gate missed it.** VERIFICATION.md proves REQ-07 with "every non-empty line …
is `grep -qxF` present in the page". That predicate is blind to blank lines by construction, so a
verbatim check passed on a page whose rendering is not verbatim. This is the failure mode phase 04's
REQ-06 audit will also miss — REQ-06 hunts for *lost claims*, and no claim is lost here.

**Fix.** Reinsert the seven blank lines (`docs/acknowledgements.md`, between lines 3–10). One-line
change. Tighten the REQ-07 truth to compare the paragraph *block* (`sed -n '151,165p'` including
blanks) rather than per-line membership.

### [should-fix] `docs/installation.md` says "the marketplace above" — there is no marketplace above it

**Evidence.** `docs/installation.md`, the self-bootstrap paragraph: *"Codex v1 uses the user-installed
marketplace **above** and does not mutate user configuration from a project skill."* In the original
README that "above" pointed at lines 20–23, the `codex plugin marketplace add` fence. Those lines
**stayed** in README (MAPPING rows for 18–23, correctly — REQ-03 wants both install blocks above the
fold). The referring sentence moved. The referent did not.

Same page, first paragraph: *"Start a new Codex thread **after installation**…"* — the page named
Installation contains no installation.

**Why it matters now.** No later phase owns this. REQ-08 (phase 04) repoints *inbound* references to
relocated content; this is a dangling deictic *inside* relocated content pointing at content that
stayed. It will not be caught by `git grep -in readme`, and `check-links.py` cannot see prose deixis.
If phase 02 does not fix it, nothing will.

**Fix.** In `docs/installation.md`, replace "the user-installed marketplace above" with an explicit
link back — "the user-installed marketplace in the [README](../README.md#install)" — or restate it as
"the marketplace install shown in the README".

### [should-fix] `docs/installation.md` is a leftovers page, and "installation" is split across two homes

**What is wrong.** REQ-05 requires one home per topic. The topic *installation* now lives in two
places: the actual install commands in `README.md:11–23`, and everything else in
`docs/installation.md`. The page holds three unrelated leftovers — Codex thread restart, plugin
self-bootstrap + pointer files, and BlitzOS context repos — none of which is installation, and it is
9 lines.

**Concrete scenario.** Phase 03 writes `docs/README.md` (REQ-04) with a one-line "what it answers" per
page. A new user reads "Installation — how to install DevFlow", clicks through, and finds no install
command; the page opens mid-thought with "Start a new Codex thread after installation". They go back
to the README to find what they were sent to a dedicated page for.

**Fix (pick one).** Either (a) rename the page to what it actually is — `docs/setup.md` /
`docs/after-install.md` — and have REQ-04's index describe it as post-install setup and bootstrapping;
or (b) keep the name and open the page with a one-sentence "Install commands are in the
[README](../README.md#install); this page covers what comes after." Option (b) is cheaper and also
resolves SF-1. Either way, "Context repos (BlitzOS-style)" is a poor fit for a page named
installation — it is a deployment-context topic that already has its own page (`docs/blitzos.md`) and
would sit more naturally as a pointer from the README or the index.

### [should-fix] `docs/parallel-work.md`'s lead sentence promises something the page no longer delivers

**Evidence.** `docs/parallel-work.md:3` — *"The bottleneck in agent-assisted work isn't decomposition —
it's losing track of what each session is doing, **and reading its output cold at the end**."* The page
then has exactly two sections: Fleet board, Workstreams. Both address the first clause. Neither
addresses the second.

The pieces that answered "reading its output cold" were original lines 112 (`/flow-ci` triaging bot
threads) and 124 (the PR **Review guide** — literally *"so a reviewer never meets the diff cold"*).
Both were routed to `docs/review.md`. The framing sentence stayed behind.

**Why the recorded deletion analysis missed it.** MAPPING correctly identified that "Four pieces
address that:" had to go. It did not notice that the sentence *before* the connector is also a
promise, and that half of it went to a different page.

**Fix.** Either trim the lead to its surviving half — "…losing track of what each session is doing." —
or keep it whole and add "(reading output cold is the other half; see [review.md](review.md))". The
first is cleaner and is the same edit the deliberate-deletion reasoning already justifies. Record it
alongside the existing deletion so phase 04's REQ-06 audit sees both.

### [should-fix] `/flow-oracle`'s "no install required" reach fact is gone from `docs/` entirely

**Evidence.** Original line 90: *"…runs it through the best available engine (the `oracle` CLI or MCP
server when installed; otherwise a render-and-copy bundle you paste into any chat UI — **no install
required**), and distills the reply into a **≤10-line advisory verdict**."*

`docs/review.md` § Second opinions replaces this with "The bundle, engine-detection order, and consult
lineage mechanics are specified in [`oracle.md`]". Across the whole new corpus: `no install required`
→ 0 hits, `chat UI` → 0, `10-line` → 0, `advisory verdict` → 0, `best available engine` → 0.

**This is defensible under REQ-12a and I am not calling it content loss** — `oracle.md:10` says
"always works, nothing to install" and `oracle.md:29` says "≤10 lines", and the page links there. But
"you can use this without installing anything" is a *reach* fact, not a mechanic: it changes whether a
reader decides `/flow-oracle` applies to them at all. REQ-12a explicitly preserves "enough shape to
decide whether to read further", and this is the sentence that did that work.

**Concrete scenario.** A reader without the `oracle` CLI reads `docs/review.md` § Second opinions,
sees only a link to an engine-detection reference, and concludes `/flow-oracle` requires tooling they
do not have. They do not open `references/oracle.md`, because they have already decided.

**Fix.** Restore one clause to `docs/review.md`: "…runs it through the best available engine — the
`oracle` CLI or MCP server when installed, otherwise a bundle you paste into any chat UI, so nothing
has to be installed — and distills the reply into a capped advisory verdict." The thresholds stay in
`oracle.md`; only the reach claim comes back.

### [should-fix] This PR deletes README sections that the shipped plugin still tells users to read

**Evidence.**

- `plugins/devflow/skills/flow-status/SKILL.md:26` — *"see the README's Autonomous operation recipes"*
- `plugins/devflow/skills/flow-status/SKILL.md:28` — *"See README → Session hygiene."*
- `.github/ISSUE_TEMPLATE/config.yml:5` — `about: Command reference and autonomous-operation recipes.`
  on a link to `…/devflow#readme`

All three describe README content this PR removes. The new README has four `##` headings — Install,
Commands, Flow, Acknowledgements — and no link to `docs/autonomy.md`.

**Concrete scenario.** A user on the merged branch runs `/flow-status`. The skill tells them to read
the README's Autonomous operation recipes. They open the README, find no such section, find no
documentation index, and find no path to `docs/autonomy.md` from anywhere in the repo. The content
exists; it is unreachable by the route the product itself hands them.

**This is scheduled** — REQ-08, phase 04, and REQ-08 names both files explicitly. I am raising it as a
should-fix on *this PR* rather than deferring, because it is the specific harm behind the navigability
question in §Judgment, and it is what makes a standalone merge unsafe rather than merely ugly.

**Fix.** Do not merge this branch to `main` on its own — see §Judgment.

### [nit] BlitzOS link text still reads `docs/blitzos.md` while the target is the sibling

`docs/installation.md`: `[`docs/blitzos.md`](blitzos.md)`. The href was correctly rewritten to a
sibling (MAPPING §"Link forms inside `docs/`" proved the checker requires it); the visible text was
not. A reader inside `docs/` sees a path that would resolve to `docs/docs/blitzos.md`. Make the text
`blitzos.md`, or make it prose ("specified in [BlitzOS context repos](blitzos.md)").

### [nit] `docs/autonomy.md` adds prose that was never in the README

D-14 frames this phase as a true move. `docs/autonomy.md:1–6` adds material with no README origin:
"ends **its final message** with", "and which `/loop` and `/flow-status --all` read the same way", and
an invented example line `FLOW: CONTINUE | phase 2/4 executed, verification pass | next: /flow-plan 3`.

The additions are correct and improve the page. But MAPPING claims a line-by-line disposition and does
not disclose them, so phase 04's REQ-06 audit — which diffs old README against the new corpus — will
meet unexplained new text and have to re-derive whether it is drift. One line in MAPPING noting
"02-05 adds an example status line and the `/loop`//`flow-status` reader note" costs nothing and
closes that.

### [nit] One rationale clause dropped without being recorded

Original line 138 ends: *"— the one structured exception to that rule, **and the reason the rest can
stay prose**."* `docs/autonomy.md` keeps "the one structured exception to that rule" and drops the
rest. `grep -c "reason the rest can stay prose"` → 0 in `docs/`, 0 in `references/`.

It is a rationale sentence, which REQ-12a says the `docs/` page keeps (it is "why it exists", not a
threshold or a field list). Small, but it is a second undeclared deletion in a phase whose whole
artifact is a claim that there is exactly one. Either restore the clause or add it to MAPPING's
deletion section.

## Judgment

**Item 4 — should this ship as a standalone PR? No. It should not merge to `main` on its own.**

Not because the intermediate state is ugly. CONTEXT.md D-14 accepts the husk knowingly, the reasoning
behind it is sound (never let the same prose live in README and a `docs/` page), and the serial-wave
argument in MAPPING §Waves is correct — the alternative was a copy-then-delete window, which is worse.
The carve itself is good work: nine coherent pages, no content lost, a mapping artifact that survives
being tested against the tree.

The problem is that "unindexed" understates it. Merged alone, this branch produces a state where:

1. `github.com/jbrianfrancis-ir/devflow` — the project's only marketing surface — renders 61 lines
   with nothing about the execution model, provenance, autonomy, review, parallel work, or
   requirements clarity, and no link to the eight pages that now hold them.
2. The shipped plugin actively misdirects: `flow-status/SKILL.md` tells every user who runs
   `/flow-status` to read two README sections that this same commit deletes.
3. The issue template's "DevFlow README" contact link promises "Command reference and
   autonomous-operation recipes" and delivers half of one.

Points 2 and 3 are the ones that decide it. An ugly README is a cosmetic cost the team chose. A
product that hands users a route to content and then removes the destination is a regression, and it
is live from the moment this merges until phase 04 lands — an unbounded window, since nothing forces
phase 04 to follow immediately.

**Should it have been one phase?** No — and I want to be precise, because the two questions have
different answers. Splitting the *carve* from the *rebuild* was correct: they are genuinely different
work with different failure modes, the carve is mechanically risky in a way that benefits from its own
review, and this findings file exists because it got one. Merging them would have produced one
enormous diff where the content-loss question — the one that actually matters — would have been
buried under README restructuring.

The mistake is not the phase boundary. It is treating the phase boundary as a *merge* boundary.

**Recommendation:** land phases 02 and 03 together — either stack `flow/phase-03-*` on this branch and
open one PR, or hold this branch unmerged until 03 is verified and merge both. Phase 04 (repointing)
can follow separately: once `docs/README.md` exists and README links it, points 2 and 3 degrade from
"broken route" to "indirect route", which is a tolerable interim.

If the team merges this standalone anyway, the minimum mitigation is a three-line temporary
`## Documentation` section in README linking the nine pages, deleted in phase 03 when the real index
lands. That is a deviation from REQ-01's section list for one phase, and it is cheaper than the
alternative.

**Item 5 — does anything foreclose phase 03 or 04?** Nothing hard-blocks either. Two things will fight
them:

- **REQ-01 requires a `## Configuration` section in README, and phase 02 moved every configuration
  knob out of it.** `agents.provider` and `agents.models` are now only in `docs/providers.md`;
  `autonomy.max_iterations`/`max_repeats`/`max_hours` only in `docs/autonomy.md`;
  `~/.devflow/fleet.json` roots only in `docs/parallel-work.md`. D-14 forbids restating any of them in
  README. So phase 03's `## Configuration` can only be a pointer list. That is probably the right
  shape anyway, but phase 03 should go in knowing the constraint rather than discovering it
  mid-write — otherwise the natural move is to copy the JSON snippets back, which violates D-14.
- **MAPPING's REQ-12 link table is a plan, not an inventory.** `installation.md` is paired with
  `hosts.md` + `conventions.md` there; the page links only `conventions.md`. VERIFICATION.md and
  LEARNINGS already caught this. Phase 04 must not audit link coverage against that table.

Phase 04's REQ-08 targets are unchanged and still accurate. Phase 04's REQ-06 audit is well served by
MAPPING.md — it held up under an independent prose-first check — with the three caveats above (the
undisclosed `autonomy.md` additions, the unrecorded L138 clause, and the fact that REQ-06 as written
would not have caught the blocking finding, because losing paragraph structure is not losing a claim).
