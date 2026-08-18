# Findings — accuracy

Lens: CORRECTNESS as FACTUAL ACCURACY. Diff: `main` (22dfdc7) → `origin/flow/phase-02-docs-carve` (5ffe726).
Every claim below was checked by running commands against the repo, not read off the prose.

## Summary

2 blocking, 2 should-fix, 2 nit

## Findings

### [blocking] `docs/providers.md` model-tier enumeration omits two of the eleven agent roles, and contradicts the reference it cites

**File:** `docs/providers.md:14`

**The false claim, quoted:**

> Judgment roles — planner, plan-checker, verifier, reviewer, consultant, migrator — run on the top tier; bounded roles — mapper, researcher, and the high-volume **executor** — run a tier down.

Read with the sentence that precedes it ("Each role declares its own model"), this is an exhaustive two-bucket partition of the roles. It names 9. The repo has 11.

**What is actually true:**

`plugins/devflow/references/hosts.md:62-64` — the reference this very page points at on line 16 ("the full per-role model table … are specified in [`hosts.md`]") — says:

> Judgment roles — planner, plan-checker, **plan-reviewer**, verifier, reviewer, **adjudicator**, consultant, migrator — run on the top tier; bounded roles — mapper, researcher, executor — run a tier down.

Confirmed against the agent frontmatter (`grep -m1 '^model:' plugins/devflow/agents/*.md`):

```
flow-adjudicator.md     model: opus     <- omitted from the page
flow-plan-reviewer.md   model: opus     <- omitted from the page
flow-consultant.md      model: opus
flow-migrator.md        model: opus
flow-plan-checker.md    model: opus
flow-planner.md         model: opus
flow-reviewer.md        model: opus
flow-verifier.md        model: opus
flow-executor.md        model: sonnet
flow-mapper.md          model: sonnet
flow-researcher.md      model: sonnet
```

This is REQ-12a: a page contradicting its own reference contract. It is also a **cross-page inconsistency inside this diff** — `docs/review.md:4` says the plan panel "costs three top-tier agents per round", i.e. it asserts `flow-plan-reviewer` is top-tier, which `docs/providers.md` implicitly denies by leaving it out of the top-tier list without putting it in the other one.

**Provenance (why it drifted):** the paragraph was carried into `docs/providers.md` byte-identical from `git show 22dfdc7:README.md` line 40 (verified with `diff`). `hosts.md` was updated to add `plan-reviewer` in 7d4155b (2026-08-15) and `adjudicator` landed with dbdf745 (2026-08-16); the README paragraph was never updated, and this phase moved the stale text rather than reconciling it. A verbatim move is the right default — but a page that now *cites* `hosts.md` as its authority has to agree with it.

**Fix:** replace the two role lists on `docs/providers.md:14` with the `hosts.md` lists — add `plan-reviewer` and `adjudicator` to the judgment group.

---

### [blocking] `README.md` opening paragraph undercounts subagents and prompt-content size

**File:** `README.md:3`

**The false claim, quoted:**

> 20 shared Agent Skills and 9 subagents across ~165KB of prompt content

**What is actually true:** 20 skills is correct. The other two figures are not.

```
$ ls plugins/devflow/agents/ | wc -l
11
```

Byte totals over the `.md` prompt content:

```
plugins/devflow/skills          91518 bytes   89.4 KB
plugins/devflow/agents          41842 bytes   40.9 KB
plugins/devflow/references      63747 bytes   62.3 KB
plugins/devflow/templates       29909 bytes   29.2 KB
TOTAL                          227016 bytes  221.7 KB
```

So: **11 subagents, ~222KB** — not 9 and ~165KB. The size claim is understated by ~34%.

**Provenance:** `git log -S'165KB' -- README.md` dates the figure to 45cf01f, and `git log --diff-filter=A --name-only -- plugins/devflow/agents/` shows exactly 9 agent files existed at that point. `flow-plan-reviewer.md` (7d4155b, 2026-08-15) and `flow-adjudicator.md` (dbdf745, 2026-08-16) landed after, and the count was never revised.

**Scope note, stated plainly:** this line is **not touched by this diff** — `git diff main...origin/flow/phase-02-docs-carve -- README.md` opens at `@@ -22,27 +22,6 @@`, so the paragraph is inherited unchanged. I am reporting it as blocking because it is a concretely false statement standing in the file this phase exists to rewrite, and because it is the same drift class as the `providers.md` finding above (agent roster grew, prose didn't). If the phase's scope is strictly "move text, change nothing", downgrade it to should-fix and file it — but do not ship the 61-line README claiming 9 subagents.

**Fix:** `9 subagents across ~165KB` → `11 subagents across ~222KB`.

---

### [should-fix] `docs/installation.md` has a dangling "above" — the thing it refers to stayed in the README

**File:** `docs/installation.md:3` and `docs/installation.md:7`

**The claim, quoted (line 7):**

> Codex v1 uses the user-installed marketplace **above** and does not mutate user configuration from a project skill.

**What is actually true:** there is no marketplace above. On the source page there was — `git show 22dfdc7:README.md` lines 18-23 carry the `codex plugin marketplace add …` / `codex plugin add …` block immediately above this paragraph. The carve left those install blocks in `README.md:18-23` and moved only the prose, so the anaphor now points off the page.

The same break hits the page's opening sentence, line 3:

> Start a new Codex thread **after installation** and invoke skills with `$flow-new`, …

A page titled "Installation" that opens mid-thought, continuing an install procedure it does not contain.

The underlying facts are correct — `plugins/devflow/references/conventions.md:107-110` confirms "Codex v1 is installed at user scope from the DevFlow marketplace. Project skills must not edit `~/.codex`…". Only the reference is broken.

**Fix:** either move the two install code blocks from `README.md` onto `docs/installation.md` (which is what a page with that title should hold), or reword line 7 to name the target — "the user-scope DevFlow marketplace installed in the README's Install section" — and give line 3 a lead-in sentence.

---

### [should-fix] Eight of the nine new pages have no inbound link from anywhere

**Files:** all of `docs/{installation,providers,execution-model,provenance,requirements-clarity,review,parallel-work,autonomy}.md`

The diff carves README 167→61 lines into nine pages. `README.md` links exactly two documents:

```
$ grep -n 'docs/' README.md
7:  … Contract: [`docs/status-contract.md`](docs/status-contract.md).
59: Concept lineage and upstream credit: [docs/acknowledgements.md](docs/acknowledgements.md).
```

`docs/acknowledgements.md` is reachable (README:59). The other eight are not — I grepped every `.md` in `README.md` and `docs/` for inbound references and found none. (`docs/autonomy.md` appears to match, but every hit — `docs/provenance.md:9`, `docs/blitzos.md`, `docs/status-contract.md` — links `../plugins/devflow/references/autonomy.md`, the *reference* file, not the docs page. Same basename, different file.) There is no `docs/README.md` or index either.

Roughly 105 lines of prose that the README used to carry are now unreachable from any entry point. This is adjacent to the accuracy lens rather than inside it, but it makes the README's claims *less* verifiable, not more: a reader who wants the model-tier detail the README dropped has no path to `docs/providers.md`.

**Fix:** add a "Docs" section to `README.md` linking all nine pages, or a `docs/README.md` index that the README points at.

---

### [nit] `docs/autonomy.md` human-gate list drops a gate that `docs/review.md` names as one

**File:** `docs/autonomy.md:38-41` vs `docs/review.md:19`

`docs/autonomy.md` lists eleven human gates. `plugins/devflow/references/autonomy.md:30` — the authoritative list, which the page correctly points at on lines 43-44 — carries three more: shipping a `CONFIRMED` finding dispositioned `ACCEPTED AS-IS`, `azd login`, and "anything destructive in git".

The first of those is asserted as a human gate on `docs/review.md:19` in the same diff ("Shipping a `CONFIRMED` finding `ACCEPTED AS-IS` is a human gate, named individually at the PR gate and in the PR body"). Not a contradiction — the page defers to the reference for the authoritative list — but two pages in one diff give different-length answers to "what are the gates", and the one the reader hits first is the shorter one.

**Fix:** add the `ACCEPTED AS-IS` gate to the `docs/autonomy.md` list, or nothing — the deferral sentence already carries the weight.

---

### [nit] `docs/autonomy.md:3` widens "orchestrating skill" to "skill"

**File:** `docs/autonomy.md:3`

> Every skill ends its final message with a machine-checkable status line

`plugins/devflow/references/autonomy.md:8` says "Every **orchestrating** skill ends its final message with exactly one line". The page drops the qualifier.

**In this repo the wider claim happens to be true** — I checked all 20 skills for a `FLOW:` line and every one has it, so there is no skill this misdescribes today. Flagging only because it is a silent widening of a contract sentence, and it inherits the same phrasing already in `README.md:7`. No action needed unless a non-orchestrating skill is ever added.

## Verified clean

Everything below was checked by running a command and reading the result.

**Commands and flags — all exist.** Every `/flow-*` command named across the nine pages and the README table resolves to a directory under `plugins/devflow/skills/` (20 of them, matching the README's "20 shared Agent Skills"). Every flag was confirmed against the owning `SKILL.md` frontmatter: `--auto` / `--gaps` / `--research` / `--panel` / `--review` (flow-plan), `--adversarial` (flow-pr), `--all` / `--pause` / `--reset-run` (flow-status), `--export` / `--since` (flow-audit), `--panel` / `--followup NNN` (flow-oracle), `--docs` / `--refresh` (flow-map), `--refresh` (flow-design), `--provider native|claude|codex` (every delegating skill), `new` / `list` / `drop` (flow-workstream), `--json` / `--stale-days` / `--depth` (flow-fleet.py).

**File and artifact paths — all exist.** `docs/blitzos.md`, `docs/status-contract.md`; all eight referenced files under `plugins/devflow/references/` (`adjudication.md`, `autonomy.md`, `checkpoints.md`, `conventions.md`, `hosts.md`, `oracle.md`, `plan-format.md`, `verification.md`); `plugins/devflow/templates/architecture.md`; `plugins/devflow/scripts/flow-fleet.py`. Relative-path depth from `docs/` (`../plugins/devflow/references/…`) is correct on every link I resolved. The `docs/blitzos.md` link was correctly rewritten from the README's `docs/blitzos.md` to a page-relative `blitzos.md`.

**Counts and enumerations — correct except the one in Finding 1.** `docs/review.md:7`'s seven `flow-reviewer` lenses (correctness, security, architecture, conventions, reuse, tests, design) match `plugins/devflow/agents/flow-reviewer.md:15-24` exactly and match the selection rules in `flow-pr/SKILL.md:17`. `docs/review.md:4`'s "three fresh-context `flow-plan-reviewer` agents … scope, feasibility, coherence" matches `flow-plan-reviewer.md:20-24`, and "three top-tier agents" is right (`model: opus`). `docs/review.md:19`'s "three rules" match `adjudication.md` (disproving §29, dismissal §37, immutability §55). `docs/autonomy.md`'s "three rails" match `references/autonomy.md:42-44` (stuck / iterations / time). `docs/autonomy.md`'s five recipes match `references/autonomy.md:58-63` verbatim, including the `/loop 15m` deployment watch. Checkpoint types "decision / human-action / human-verify" match `checkpoints.md:4-6`. "Two axes" adjudication matches `adjudication.md:10-23`. `docs/parallel-work.md` correctly dropped the old README's "Four pieces address that:" lead-in after two of the four moved to `docs/review.md` — that enumeration would otherwise have been left dangling at two.

**Config snippets — exact.** `"agents": {"provider": "native|claude|codex"}` and `"agents": {"models": {"executor": "opus"}}` match `hosts.md:69-75`. `"autonomy": {"max_iterations": 40, "max_repeats": 3, "max_hours": null}` matches `references/autonomy.md:53` character for character. `{"roots": ["~/dev"], "stale_days": 3}` at `~/.devflow/fleet.json` matches `flow-fleet.py:18-19,33`.

**Behavioral claims — each traced to its contract.**
- Smoke gate (`docs/execution-model.md:7`): `verification.md:33-41` confirms `## Smoke` in `.planning/ARCHITECTURE.md`, run verbatim, judged against "Pass looks like", failure is a GAP even when phase truths pass, flagged as pointing at earlier work, undeclared → standing HUMAN check, never invented, never skipped. The page also *corrected* the old README here: `ARCHITECTURE.md` → `.planning/ARCHITECTURE.md`, which is what the reference says. `## Smoke` confirmed present in `templates/architecture.md:30`.
- Revision budget (`docs/review.md:4`): the page drops the old README's literal "3-round" and defers to `plan-format.md` → Gates; that section (`plan-format.md:41`) does say "max 3 iterations" and does name the three panel lenses. Pointer and fact agree.
- Librarian pass (`docs/execution-model.md:13`): `mapped_sha` confirmed in `templates/codebase-map.md:4`; the `mapped_sha..HEAD` diff and the exact structural-movement trigger list (new top-level dir/service, changed manifest or pin, new env-var accessor, changed build/test/run command) match `flow-execute/SKILL.md:31`; `flow-verify/SKILL.md:22` confirms it runs on that path too; the fail-closed `map: not refreshed` behaviour with fields left untouched matches `flow-execute/SKILL.md:33`.
- Workstream reconciliation (`docs/parallel-work.md:9`): the page replaced the README's inline artifact list with a pointer to `conventions.md` → Parallel workstreams. That section (`conventions.md:43-58`) does carry the branch-local / union / single-writer table, the hidden-edge refusals (migration chain, lockfile, generated output, ports, shared dev infra), the port offset, and the `user_setup` naming of missing untracked files. Pointer is accurate and the dropped specifics are all there.
- Fleet board (`docs/parallel-work.md:6`): `flow-fleet.py` confirmed to parse the `## Gate` block for `type`/`asked`/`options`/`default` (lines 110-138), print the question and numbered options in the "needs a human" footer (382, 395), expose `--json` (422, 443), and exit 1 when anything needs a human (line 22 docstring, 451).
- Oracle (`docs/review.md:10`): `oracle.md:24-25` confirms `--panel` is "same bundle to 2–3 models"; `:30` confirms `--followup NNN` chains via `parent: NNN`; `:3,:12` confirm `.planning/consults/` and lineage. The three stuck-point offers are real: `flow-debug/SKILL.md:19` (after a widen round), `flow-plan/SKILL.md:22` (checker escalation), `flow-harden/SKILL.md:20` (finding of unclear production impact).
- Adjudication (`docs/review.md:16,19`): the page abstracts the two vocabularies behind a pointer; `adjudication.md:10-23` carries all eleven terms. All three ledger rules verified at `adjudication.md:29` (REFUTED needs a command that ran and its output), `:37` (`FIX LATER` requires the backlog entry to exist *before* the row), `:55` (closed round immutable, supersession cites rather than overwrites). `ACCEPTED AS-IS` as a human gate confirmed at `adjudication.md:20` and `references/autonomy.md:30`. `.planning/reviews/LEDGER.md` and `templates/review-ledger.md` confirmed at `flow-pr/SKILL.md:29`.
- Adversarial dispatch (`docs/review.md:13`): "a missing or failing peer is BLOCKED, never a quiet fall back to native" matches `flow-pr/SKILL.md:27` and the fail-closed rule in `hosts.md:90-97`.
- Provenance (`docs/provenance.md:6,9,11`): trailer format `DevFlow-Agent: <role>/<provider>/<model>` + `DevFlow-Plan: NN-MM` and the `git log --grep='^DevFlow-Agent:'` claim match `conventions.md:22-36`, including "the committer stays the human". "The one uncapped state file, never rewritten" matches `conventions.md:84` verbatim in substance. JOURNAL overflow rolling into `.planning/history/` matches `conventions.md:81` and `templates/journal.md:2`. `/flow-audit --export [--since <date|tag|sha>]` writing `.planning/exports/AUDIT-<date>.md` matches `flow-audit/SKILL.md:42-46`, as does the "leads with what it cannot cover" framing.
- Requirements clarity (`docs/requirements-clarity.md`): `## Assumptions`, `## Success criteria` with `SC-NN`, and the `[NEEDS CLARIFICATION]` example all present in `templates/requirements.md:4-31`; the SC examples quoted on the page ("p95 under 400ms at 500 concurrent users", "90% finish onboarding unaided") are faithful paraphrases of `SC-02`/`SC-03` in that template. `/flow-harden`'s SC audit — number-with-nothing-measuring-it is a finding, human-judged is deferred not dropped — matches `flow-harden/SKILL.md:20`. `/flow-uat` writing one acceptance case per SC with threshold matches `flow-uat/SKILL.md:16`. `ARCHITECTURE.md` → `## Principles` confirmed at `templates/architecture.md:17`.
- Conventions (`docs/execution-model.md:16`): `src/`/`tests/`, branch off `dev`/`main` → `origin` → PR to `upstream`, fail-closed secret scan as a human gate with the value never echoed, names-only Environment manifest — all in `conventions.md` §§ Code layout / Git workflow / Secret scan and `templates/architecture.md:52`. Aspire within-major auto / major bump (13→14) needs approval matches `flow-harden/SKILL.md:20`.
- Self-bootstrap (`docs/installation.md:7`): the `.claude/settings.json` merge of `extraKnownMarketplaces` + `enabledPlugins`, marker-merged `CLAUDE.md`/`AGENTS.md` pointers, and Codex not mutating user config all match `conventions.md:95-110`.
- Status line (`docs/autonomy.md:3-7`): the grammar `FLOW: <state> | <position> | next: <command>` with states CONTINUE/GATE/BLOCKED/DONE matches `references/autonomy.md:8-18`, and the example `FLOW: CONTINUE | phase 2/4 executed, verification pass | next: /flow-plan 3` is copied verbatim from `references/autonomy.md:20`. The `## Gate` block fields (`type`, `asked`, `options`, `default`) match `:23` and `templates/state.md:9`; the `## Run` block matches `templates/state.md:23`; "a driver may surface options; it may never pick one" matches `:27`; the malformed-block-is-BLOCKED rule matches `:48`; reset on `/flow-status --reset-run` matches `:46`.

**Prose survived the move.** I ran a word-level diff of all 20 relocated paragraphs against `git show 22dfdc7:README.md`. Every one is either byte-identical or differs only in ways the restructure required: a bold lead-in converted to an `##` heading (`**Smoke gate**:` → `## Smoke gate` + "Per-phase…"), an inline reference path converted to a trailing "…are specified in [`x.md`](…)" pointer, or hard-wrapping. `docs/autonomy.md:49-52` (session hygiene) is byte-identical to old README:144. `docs/providers.md`, `docs/acknowledgements.md`, and the Codex-thread paragraph are verbatim moves. No paragraph was silently reworded to mean something different, and no factual sentence was truncated in a way that changed its claim.

Three deliberate compressions are worth naming, all of which move detail behind an accurate pointer rather than losing it:
- `docs/review.md:10` drops the oracle engine-detection detail (oracle CLI / MCP / render-and-copy fallback, ≤10-line verdict) → `oracle.md:5-9,27` has all of it.
- `docs/review.md:16` drops the eleven verdict/disposition terms → `adjudication.md:10-23` has all of them.
- `docs/parallel-work.md:9` drops the `STATE.md`/`JOURNAL.md`/`ARCHITECTURE.md` merge classification → `conventions.md:47-53` has the table.

None of these is a contradiction; each pointer resolves and the target says what the page says it says.
