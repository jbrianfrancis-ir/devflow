# Findings — conventions

Diff: `main...origin/flow/phase-02-docs-carve` (15 commits, `e23403c..5ffe726`).
Everything below was run against the checkout at `5ffe726`.

## Summary
1 blocking, 6 should-fix, 5 nit

## Findings

### [blocking] `docs/providers.md` contradicts `hosts.md` on which roles are top-tier — and the agent frontmatter proves the page wrong
**File:** `docs/providers.md:14`

**What is wrong.** The page splits roles into two cost tiers as an exhaustive list:

> Judgment roles — planner, plan-checker, verifier, reviewer, consultant, migrator — run on the top
> tier; bounded roles — mapper, researcher, and the high-volume **executor** — run a tier down.

`plugins/devflow/references/hosts.md` → `## Model tiers`, which this very page names as its source of
truth (`docs/providers.md:16`), lists judgment roles as *planner, plan-checker, **plan-reviewer**,
verifier, reviewer, **adjudicator**, consultant, migrator*. The page omits `plan-reviewer` and
`adjudicator` from both halves — they appear in neither tier.

The frontmatter settles it against the page, not against the reference:

```
$ grep -m1 '^model:' plugins/devflow/agents/flow-{plan-reviewer,adjudicator,executor}.md
plugins/devflow/agents/flow-adjudicator.md:model: opus
plugins/devflow/agents/flow-plan-reviewer.md:model: opus
plugins/devflow/agents/flow-executor.md:model: sonnet
```

Both omitted roles are `opus` — top tier. The page is not merely incomplete; its enumeration is false.

**Scenario.** A user reads `docs/providers.md` precisely because its thesis sentence promises cost is
knowable from the docs — *"cost is a property of the plugin rather than something you have to remember
to ask for."* They budget a review round from it. `docs/review.md:4` tells them `/flow-plan N --panel`
spawns **three** `flow-plan-reviewer` agents per round, and `docs/review.md:16` tells them
`/flow-pr --adversarial` adds a `flow-adjudicator`. Neither role appears in the top-tier list on the
one page that owns cost, so they price four opus-tier agents per phase as cheap-tier and enable
`--panel` and `--adversarial` across a milestone. The spend lands several multiples over the estimate,
and the page they used to estimate it is the page that told them wrong.

This is the class `CONTEXT.md` → Watch out names explicitly: *"A `docs/` page that contradicts its
`references/` contract is a defect, not staleness (REQ-12a)."*

**Not the executor's invention** — the paragraph is a verbatim move of `README.md:40` at `e23403c`, so
the error predates the carve. But phase 02 is what created `docs/providers.md` and what asserted, in
its own `MAPPING.md` D-10 table, that this page *summarizes and links* `hosts.md` as source of truth.
Restating a diverged role list under that claim is what makes it a defect now rather than then.

**Fix.** Drop the role enumeration from `docs/providers.md:14` and keep the parts that are genuinely
the page's own — the *why* (cost is declared per role, the executor is deliberately cheap because a
plan is a complete prompt) and the `agents.models.<role>` override. Let the existing
`[`hosts.md`](../plugins/devflow/references/hosts.md)` pointer carry the table. That is D-10 applied,
and it removes the divergence rather than re-syncing a copy that will diverge again.

---

### [should-fix] `docs/autonomy.md` copies behavior facts that `references/autonomy.md` owns — the one thing CONTEXT.md's Discretion clause forbids
**File:** `docs/autonomy.md:16–35` (config block at :23, gate-record fields at :31)

**What is wrong.** `CONTEXT.md` → Discretion grants the executor latitude on summary-versus-link with
one explicit proviso: *"provided no behavior fact appears in full in both a `docs/` page and its
`references/*.md` contract."* Measured, ten maximal verbatim runs are shared between
`docs/autonomy.md` and `plugins/devflow/references/autonomy.md` (8-gram shingling, punctuation and
case normalized):

```
• example flow continue phase 2 4 executed verification pass next flow-plan 3
• goal flow says done or gate or stop after 40 turns then flow-next
• watch a deployment loop 15m curl the uat health endpoints and report any change
• the next command can run not the run is getting anywhere a rule that keeps
  re-matching its own precondition replanning gaps that replanning
• close is the usual one emits continue forever and a loop will
• run block in state md and checks three rails before doing any work
• autonomy max iterations 40 max repeats 3 max hours null
• be read is not a counter that says zero
• type asked enumerated options with their consequences default
• a driver may surface options it may never
```

Two of those are behavior facts in full, not framing:

- **`"autonomy": {"max_iterations": 40, "max_repeats": 3, "max_hours": null}`** (`docs/autonomy.md:23`)
  is byte-for-byte the tunable block at `plugins/devflow/references/autonomy.md:53`, defaults included.
- **The `## Gate` record's field list** — `type`, `asked`, enumerated `options` with their
  consequences, `default` (`docs/autonomy.md:31`) — is the field list at
  `references/autonomy.md:23`, minus *"and the plan/task when it is plan-scoped"*.

`MAPPING.md`'s own D-10 table assigns exactly these to the reference: *"Normative detail that stays
there: Status-line grammar, rail semantics, gate-record fields, the gate list."* All four are on the
page in full, and the page then links the reference underneath them.

**Scenario.** `max_iterations` is lowered from 40 in `references/autonomy.md` (the file `/flow-next`
actually reads). `docs/autonomy.md` still says 40 and nothing flags it — `check-links.py` validates
targets, never agreement, and no test compares the two. A user tuning autonomy copies the block from
the docs page, writes a stale default into `.planning/config.json`, and their run's iteration cap does
not match what the docs told them they set. This is verbatim the "stale duplicate is worse than none"
failure in `ARCHITECTURE.md` → Principles.

Same as the blocking finding, the prose is a faithful move of `README.md:136`/`:138` — the duplication
existed before the carve. D-14 required the *move*; it did not require the *duplication to survive it*,
and Discretion said so in the phase's own locked context.

**Fix.** On `docs/autonomy.md`, keep the argument (why a loop needs rails, why a malformed counter is
`BLOCKED` and not zero, why structured is not auto-answerable) and cut the two data payloads — name
the three rails and the config key without reprinting values or the field list. The
`[`autonomy.md`](../plugins/devflow/references/autonomy.md)` pointers at :26 and :44 already carry them.

---

### [should-fix] The human-gate list is restated on `docs/autonomy.md` and is already missing entries
**File:** `docs/autonomy.md:37–41`

**What is wrong.** Under the H2 `## Human gates that never auto-proceed` the page enumerates ten gates,
then says the authoritative list is in `references/autonomy.md`. Against
`plugins/devflow/references/autonomy.md:30`, the page's list drops:

- **anything destructive in git**
- **never commit to the base branch (`dev`/`main`)** — the reference carries it in the same sentence as
  a hard rule, not a gate
- **shipping a `CONFIRMED` finding dispositioned `ACCEPTED AS-IS`** — present on `docs/review.md:19`,
  so it is on the docs surface, but not on the page whose heading claims to list gates

**Scenario.** Someone wiring `/loop /flow-next` into an unattended overnight run audits their setup
against the page titled *Human gates that never auto-proceed* — the obvious place to check. They
conclude destructive git operations and base-branch commits are inside the autonomous envelope,
because the page enumerates and does not say "partial". The reference says otherwise, but they had a
list in front of them and no reason to open a second file.

An incomplete enumeration is worse than the full copy flagged above: a copy goes stale later, this one
is already wrong.

**Fix.** Either drop the enumeration to a characterization ("outward-facing actions, credential
exposure, and irreversible git operations") and let the pointer carry the list, or keep it and label it
non-exhaustive in the heading. Not both a bare list and a heading that reads as complete.

---

### [should-fix] `docs/installation.md:7` — "the user-installed marketplace above" points at nothing on the page
**File:** `docs/installation.md:7`

**What is wrong.** The sentence reads *"Codex v1 uses the user-installed marketplace above and does not
mutate user configuration from a project skill."* In `README.md` at `e23403c` that "above" resolved to
the install blocks at lines 11–23. `MAPPING.md` marks those lines **STAYS** (REQ-03 keeps both install
blocks above the fold), so they are still in `README.md`:

```
$ grep -n -i marketplace README.md docs/installation.md
README.md:14:/plugin marketplace add jbrianfrancis-ir/devflow
README.md:21:codex plugin marketplace add jbrianfrancis-ir/devflow
docs/installation.md:7:… Codex v1 uses the user-installed marketplace above …
```

The referent moved apart from the reference. Nothing on `docs/installation.md` is "above" it but a
paragraph about restarting Codex threads.

**Scenario.** After phase 03 lands `docs/README.md`, a reader arrives at `docs/installation.md`
directly from the index — not by scrolling past `README.md`. "The marketplace above" resolves to
nothing they have read, and the sentence's claim (that Codex installs at user scope rather than being
bootstrapped per-project, the actual distinction the paragraph is drawing) does not land.

This is the failure mode `ARCHITECTURE.md` → Principles calls out as uncatchable: *"including prose
mentions, which no checker catches."* `check-links.py` is green and always would be.

**Fix.** Replace "above" with the thing it means — "the user-scope marketplace installation" — or link
back to `../README.md`'s install section. One word.

---

### [should-fix] `docs/installation.md` has no H2s, breaking the page shape the phase's own librarian pass recorded
**File:** `docs/installation.md` (whole file)

**What is wrong.** Measured across the nine new pages:

```
$ for f in installation providers execution-model provenance requirements-clarity \
           parallel-work review autonomy acknowledgements; do
    printf '%-22s H1=%s H2=%s\n' "$f" "$(grep -c '^# ' docs/$f.md)" "$(grep -c '^## ' docs/$f.md)"; done
installation           H1=1 H2=0
providers              H1=1 H2=2
execution-model        H1=1 H2=7
provenance             H1=1 H2=3
requirements-clarity   H1=1 H2=4
parallel-work          H1=1 H2=2
review                 H1=1 H2=7
autonomy               H1=1 H2=5
acknowledgements       H1=1 H2=0
```

`.planning/codebase/MAP.md:41` — written by this phase's own librarian commit (`5ffe726`) — records
the rule as: *"`docs/*.md` (phase 02): one H1, topical H2s."* `installation.md` carries three
unrelated topics (Codex thread + cloud scope, self-bootstrap + pointer files, context repos) as three
bare paragraphs. `acknowledgements.md` is exempt: REQ-07 mandates a verbatim move and the source has
no headings.

**Scenario.** Phase 04 must repoint every inbound reference to the carved content
(REQ-06/REQ-08, D-05). A reference to the self-bootstrap material can be deep-linked as
`docs/execution-model.md#conventions` on the pages that have H2s, but on `installation.md` the best
available target is the whole file — so a reader following a pointer to "the pointer-file merge rules"
lands at the top of a page and hunts. The same applies to `docs/README.md`'s index in phase 03.

**Fix.** Three H2s: `## Codex`, `## Self-bootstrap and pointer files`, `## Context repos`. The prose
does not change.

---

### [should-fix] `docs/installation.md:9` uses `docs/blitzos.md` as link text — the exact form MAP.md:41 names as wrong
**File:** `docs/installation.md:9`

**What is wrong.** The link is written `[`docs/blitzos.md`](blitzos.md)`. The **target** is correct
(sibling form, resolves — verified below). The **visible text** is `docs/blitzos.md`, which
`.planning/codebase/MAP.md:41` records verbatim as the form not to use: *"Sibling links as
`blitzos.md`, not `docs/blitzos.md`."*

It also breaks the pattern the wave-1 correction (`572767c`) established for every other pointer on
these pages — `[`conventions.md`](…)`, `[`hosts.md`](…)`, `[`plan-format.md`](…)` — where link text is
the bare filename.

**Scenario.** A reader on github.com sees `docs/blitzos.md` rendered as the link label while already
inside `docs/`, and reads it as `docs/docs/blitzos.md` — or copies the label into a new reference on
another `docs/` page, where `[x](docs/blitzos.md)` **fails**: `MAPPING.md` measured that exact form and
recorded *"`[x](plugins/devflow/references/oracle.md)` from `docs/` — fails, 'target does not exist'."*
The label teaches the broken form to the next page that copies it, which is how a convention regresses
one file at a time.

**Fix.** `[`blitzos.md`](blitzos.md)`.

---

### [should-fix] Two pages omit a reference link their own MAPPING table requires, and all five SUMMARYs record `deviations: []`
**Files:** `docs/installation.md`, `docs/requirements-clarity.md`

**What is wrong.** `MAPPING.md` → *"REQ-12 / D-10 — which reference each page must link as source of
truth"* is the phase's reviewable contract. Two rows are unmet:

```
$ grep -c 'hosts.md' docs/installation.md          # MAPPING requires hosts.md
0
$ grep -c 'questioning.md' docs/requirements-clarity.md   # MAPPING requires questioning.md
0
```

- `installation.md` is assigned `hosts.md`, `conventions.md` for the **host capability matrix**; only
  `conventions.md` is linked.
- `requirements-clarity.md` is assigned `plan-format.md`, `verification.md`, `questioning.md` for the
  **abstention procedure**; `questioning.md` is absent.

The other seven rows check out. What makes this a finding rather than a nit is the second half:

```
$ grep -n 'deviations:' .planning/phases/02-carve-out-docs/*SUMMARY.md
02-01-SUMMARY.md:7:deviations: []
02-02-SUMMARY.md:7:deviations: []
02-03-SUMMARY.md:7:deviations: []
02-04-SUMMARY.md:7:deviations: []
02-05-SUMMARY.md:7:deviations: []
```

Every plan reports zero deviations while two of its stated obligations went unmet.

**Scenario.** Phase 04's REQ-06 content-loss audit uses `MAPPING.md` and the SUMMARYs as its baseline
for what phase 02 promised versus delivered. With `deviations: []` across the board, the audit reads
`MAPPING.md`'s link table as satisfied and never re-derives it, so the two missing pointers survive
into the finished docs — and `docs/requirements-clarity.md` ships describing abstention with no link to
the contract that specifies it, which is the exact D-10 gap the table existed to close.

**Fix.** Add the two links, or record them in the phase's deviation log as deliberate with the reason
(a defensible one exists for `hosts.md` on `installation.md`: `docs/providers.md` already owns that
pointer and duplicating it would be its own D-10 problem). Either resolution is fine; silence is not.

---

### [nit] Non-`references/` repo paths a reader is told to open stay unclickable
**Files:** `docs/execution-model.md:19`, `docs/parallel-work.md:6`, `docs/execution-model.md:10`

`MAP.md:41`'s clickable-pointer rule is scoped to `references/*.md`, and by that letter these pass —
all 18 `references/` pointers on the nine pages are markdown links, with zero regressions from
`572767c` (verified below). But three backticked paths point at files a reader is actively directed to:

- `docs/execution-model.md:19` — *"or write it yourself from `plugins/devflow/templates/architecture.md`"*
  is an instruction to go get a file, with no way to click through to it.
- `docs/parallel-work.md:6` — `plugins/devflow/scripts/flow-fleet.py`
- `docs/execution-model.md:10` — `plugins/devflow/templates/` (a directory; least important)

`572767c`'s own reasoning applies unchanged: *"Backticked paths are the house style of
`plugins/devflow/references/*.md`, which are agent-facing prompt contracts where nobody clicks
anything. `docs/` pages exist to be navigated."* The template path is the one worth fixing.

---

### [nit] Two commits carry a malformed `DevFlow-Plan` value
**Commits:** `ac7a0ba`, `a3a107c`

`conventions.md` → Commit attribution specifies `DevFlow-Plan: NN-MM` and *"plan-scoped commits only;
omit it for project-level ones."*

- `ac7a0ba` (`chore(flow): phase 02 executed + verified`) → `DevFlow-Plan: 02` — not `NN-MM`.
- `a3a107c` (`chore(flow): plan phase 02`) → `DevFlow-Plan: 02-00` — well-formed, but there is no plan
  `02-00`; plans are `02-01`…`02-05`.

Both are phase-level bookkeeping, so the contract says omit the trailer, as `e23403c` and `5ffe726`
correctly do. `git log --grep` still works; a consumer joining `DevFlow-Plan` to a plan file gets a
miss on `02-00` and a parse failure on `02`. Everything else on the branch is clean — see below.

---

### [nit] Page lead-ins take three different shapes across the nine pages
**Files:** `docs/provenance.md:3`, `docs/requirements-clarity.md:3`, `docs/parallel-work.md:3`

Three treatments, no pattern: `provenance.md` opens with a one-line gloss (*"Who made which change, and
who approved it."*), `requirements-clarity.md` with an italic tagline (*"\*Saying "unknown" out loud\*"*,
the retired README H2), `parallel-work.md` and `autonomy.md` lead straight into moved prose, and
`providers.md` / `execution-model.md` / `review.md` go H1 → H2 with nothing between. All are terse and
none is filler — this is consistency, not register. Worth settling before phase 03 writes
`docs/README.md` and the shape gets copied into a ninth and tenth page.

---

### [nit] `review.md`'s "twice / First / Then" enumeration straddles an H2 boundary
**File:** `docs/review.md:13, 15`

`## Adversarial review` opens *"`/flow-pr --adversarial` raises the bar twice. First the reviewer
becomes a different model…"* and the second half lands under the next heading:
`## Adjudication in a third context` → *"Then the findings are adjudicated in a third context…"*.

In `README.md` these were adjacent paragraphs, so the enumeration read straight through. Splitting them
under sibling H2s means a reader arriving at the second heading from an index meets "Then" with no
antecedent, and a reader of the first meets "twice" with only one item under it. An artifact of the
carve, not of the prose.

---

### [nit] Link-text style is inconsistent for sibling pages, including in `README.md` itself
**Files:** `docs/parallel-work.md:6`, `README.md:59` vs `README.md:7`

- `docs/parallel-work.md:6` — `[status-contract.md](status-contract.md)`, unbackticked text, where
  every reference pointer on these pages uses `[`file.md`](…)`.
- `README.md:59` (added by `1da9692`) — `[docs/acknowledgements.md](docs/acknowledgements.md)`, while
  the pre-existing `README.md:7` uses `[`docs/status-contract.md`](docs/status-contract.md)`.

Both targets are correct — from `README.md` the `docs/`-prefixed form is the right one. Only the
backticking differs. Settle it in phase 03 when the index is written.

---

## Verified clean

**`ARCHITECTURE.md` → Forbidden — all five hold.** The diff touches nothing outside
`.planning/`, `docs/`, and `README.md`:

```
$ B=$(git merge-base main HEAD); git diff --name-only $B HEAD | grep -vE '^(\.planning/|docs/|README\.md$)'
(no output)
$ [ -d src ] || echo "no src/"                                   → no src/
$ ls mkdocs.yml docusaurus.config.js conf.py _config.yml         → none
$ ls requirements.txt pyproject.toml                             → none
$ grep -rn 'pip install' .github/workflows/                      → none
$ git diff --name-only $B HEAD | grep -E 'plugin\.json'          → untouched
$ git diff --name-only $B HEAD | grep -E '^(CLAUDE|AGENTS)\.md$' → untouched
```

No third-party dependency, no `pip` in CI, no docs build system, no `src/`, no manifest version edit,
and `CLAUDE.md`/`AGENTS.md` were not touched at all — so nothing was restated into them.

**Clickable reference pointers — no regression from `572767c`.** All 18 pointers into
`plugins/devflow/references/` across the nine pages are markdown links; zero bare backticked
`references/` paths remain:

```
$ grep -onE '\[[^]]*\]\((\.\./)?plugins/devflow/[^)]*\)|`[^`]*plugins/devflow/[^`]*`' <nine pages>
```
returns 21 hits: 18 `[`file.md`](../plugins/devflow/references/file.md)` links, plus the three
non-`references/` backticked paths raised as a nit above. The wave-1 correction held across all four
later waves and seven later pages, which is what it was made at wave 1 to do.

**Sibling link targets.** Both intra-`docs/` links use the sibling form and resolve:
`docs/parallel-work.md:6` → `(status-contract.md)`, `docs/installation.md:9` → `(blitzos.md)`. No
`](docs/…)` target appears anywhere under `docs/`. (The `docs/blitzos.md` *label* at `installation.md:9`
is the should-fix above; the target is right.)

**Move completeness — 41/41 anchor phrases.** Every anchor in `MAPPING.md` → Anchor phrases scores 0
hits in `README.md` and exactly one file under `docs/`:

```
$ while IFS='|' read -r anchor page; do
    r=$(grep -cF "$anchor" README.md); d=$(grep -rlF "$anchor" docs/); n=$(echo $d | wc -w)
    [ "$r" = 0 ] && [ "$n" = 1 ] || echo "MISS: $anchor README=$r docs=[$d]"
  done < anchors.txt
(no output — all 41 pass)
```

D-14's true-move property holds: no carved prose survives in `README.md`, and no anchor landed on two
pages. `README.md` went 167 → 61 lines.

**Prose register — no padding, measured not eyeballed.** Every line of the nine pages was 6-gram
shingled against `README.md@e23403c`. The only prose above 50% novel is the eight added
*"…are specified in [`file.md`](…)"* pointer sentences (required by D-10) and re-wrap artifacts on
`docs/autonomy.md`. Zero connective throat-clearing was introduced. Compression went the right
direction where it moved at all — `docs/review.md:19` generalizes README's `FIX LATER` to "a deferral";
`docs/autonomy.md:31` drops README's "and the reason the rest can stay prose" and "the gate list below
is unchanged". Matches `MAP.md:40`: *"dense, terse, load-bearing — no filler."*

**SC-03 and the smoke gate.**

```
$ wc -l docs/*.md | awk '$2 != "total" && $1 > 250'      → (nothing; largest new page is autonomy.md at 55)
$ python3 scripts/validate-plugin.py                     → OK
$ python3 -m unittest discover -s tests                  → Ran 92 tests, OK (skipped=2)
$ python3 scripts/check-links.py                         → 0 failures, 179 references checked
```

Reference count rose 162 → 179, well clear of the 140 floor, so `CONTEXT.md`'s coverage-collapse
concern does not fire.

**D-15 (G3) — no repo path inside a fence.** The `MAPPING.md` G3 command, `~~~`-aware and `[ \t]`-indent
aware, over the seven new pages (excluding `blitzos.md`/`status-contract.md` by design): no output.
Consistent with the fact that none of the nine pages contains a fenced block at all — which also means
D-19's G3-parity port is genuinely still unexercised, exactly as PROJECT.md records.

**NOTICE byte-identical.**

```
$ git diff --exit-code $(git merge-base main HEAD) -- NOTICE   → exit 0, no output
```

REQ-07's verbatim-move half also holds: the eight acknowledgement paragraphs on
`docs/acknowledgements.md` are unmodified from `README.md:151–165`, and `README.md:59` carries the
one-line pointer plus the `NOTICE` mention.

**Commit hygiene.** All 15 commits on `main..HEAD` carry `DevFlow-Agent`:

```
$ git log main..HEAD --format='%h %s' --invert-grep --grep='^DevFlow-Agent:'
(no output)
```

Committer and author are the human (`jbrianfrancis-ir <brianf@informativeresearch.com>`) on every
commit — attribution stayed additive, per `conventions.md`. All nine executor commits carry
`DevFlow-Plan: 02-01`…`02-05` matching their plan, and the two project-level commits (`e23403c`,
`5ffe726`) correctly omit the trailer. `git log HEAD..main` is empty — nothing from this phase
landed on `main`, and `main` has not moved under the branch.

**D-10 duplication sweep — the seven pages not flagged above.** 8-gram overlap between each new page
and every `references/*.md`, with maximal shared runs inspected:
`installation.md` (1 gram, "a session that never runs a flow- skill" — shared framing, not a fact),
`execution-model.md` (1, "aspire updates within the current major apply automatically" — a rule
correctly summarized, with the reference linked), `provenance.md` (3, the "committer stays the human"
clause — the principle, not the trailer syntax, which is correctly left in `conventions.md`),
`review.md` vs `adjudication.md` (9, the three ledger rules' *names and rationale*; the operative
vocabularies — verdicts, dispositions, the `FIX LATER` mechanics — are correctly not restated, and
`README.md`'s `verification.md` mention was dropped rather than duplicated),
`requirements-clarity.md`, `parallel-work.md`, `acknowledgements.md` (zero overlap).
Only `providers.md` (8, blocking) and `autonomy.md` (52, should-fix) exceed the summarize-and-link line.

---

### Note on this review's own side effect

While gathering the diff I ran `git checkout origin/flow/phase-02-docs-carve -- .` from the repo root.
The checkout is already on that branch, so it was a no-op for tracked branch content — but it reverted
an **uncommitted** working-tree edit to `.planning/PROJECT.md` that added rows **D-18, D-19, D-20**
(phase-03 decisions). I restored all three rows verbatim from the copy I had read moments earlier, in
their original position between D-15 and D-17; `PROJECT.md` now matches what it held before my command.
No other uncommitted change was present to lose (`git status` is otherwise clean but for the untracked
`.planning/phases/03-rebuild-readme/`). Flagging it because whoever owns that edit should confirm it
reads correctly, and because a concurrent phase-03 session may hold a newer version than the one I
restored.
