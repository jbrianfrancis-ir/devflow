<!-- .planning/quick/011-stale-pr-state.md — ad-hoc mini-plan (flow-quick), not tied to ROADMAP. -->
---
phase: quick-011
plan: 01
wave: 1
depends_on: []
files_modified:
  - plugins/devflow/references/autonomy.md
  - plugins/devflow/skills/flow-next/SKILL.md
  - plugins/devflow/skills/flow-status/SKILL.md
  - .planning/STATE.md
  - .planning/DECISIONS.md
  - .planning/JOURNAL.md
autonomous: true
requirements: []
must_haves:
  truths:
    - "autonomy.md states that state owned by another system (PR/CI/remote branch) recorded in .planning/ is a cache, and must be re-read live in the current invocation before any skill asserts or routes on it"
    - "flow-next re-reads live PR state with gh before rules 8-10 match, and never routes on the PR line recorded in STATE"
    - "flow-next has an explicit branch for a PR that was merged out-of-band: the merge answers the rule-10 gate, so Gate clears, Run resets, STATE updates, and routing continues instead of re-emitting the same GATE"
    - "flow-next fails closed when gh is unavailable or unauthenticated — BLOCKED, never fall back to the STATE-recorded PR state"
    - "flow-status reports PR open/merged from a live read, and says so explicitly when the live state contradicts what STATE.md records"
    - "This repo's own STATE.md matches reality: PRs #30 and #31 merged 2026-08-27, no open gate, one Last/Next pair and one Stopped/Resume pair"
  backstop_truths: []
  artifacts:
    - .planning/quick/011-stale-pr-state-SUMMARY.md
  key_links:
    - "flow-next's rules 8/9/10 and flow-status's PR rows both cite autonomy.md's externally-mutable-state rule as the source of truth rather than restating it"
---

<objective>
Close the stale-external-state hole: DevFlow routes on PR state recorded in STATE.md without ever
re-reading it, so a PR merged out-of-band (which is exactly what rule 10 asks a human to do) leaves
the run asserting "PR #N open" indefinitely. Fix the rule, then fix this repo's own STATE.md, which
is a live instance of the bug.
</objective>

<context>
Root cause, already diagnosed — do not re-derive it, implement it:

flow-next rules 8/9/10 key off "no PR URL recorded in STATE" / "PR open". Nothing instructs a live
re-read. Rule 10 deliberately hands control to a human for an action taken *outside the session*
(review + merge on GitHub), so the recorded state is stale by construction from the moment the gate
is raised. The Repeats rail cannot catch it either: rule 10 stops the loop rather than repeating, so
the signature never advances. flow-ci already does this correctly — its Pre-flight runs
`gh pr view --json number,url,state,isDraft,mergeStateStatus` and has a "PR closed/merged" branch;
flow-next and flow-status have no equivalent. That asymmetry is the bug.

Confirmed live in this repo (2026-08-27): `gh pr list --state all` reports #31 MERGED 16:28:21Z and
#30 MERGED 16:29:33Z, while `.planning/STATE.md` still says both are open and holds a `## Gate`
asking whether to merge #31. STATE.md also carries duplicated `Last:`/`Next:` and
`Stopped:`/`Resume:` pairs — appended rather than rewritten in place, against its own header rule.

Read: plugins/devflow/references/autonomy.md (Human gates section lists the out-of-band actions;
Loop rails explains why the rail misses this), plugins/devflow/skills/flow-next/SKILL.md (routing
rules 8-10), plugins/devflow/skills/flow-status/SKILL.md (routing rows, lines 18-20),
plugins/devflow/skills/flow-ci/SKILL.md (the Pre-flight live-read pattern to mirror),
plugins/devflow/references/conventions.md (Fail-closed guards).

Constraints: prose-only edits to skill/reference content, no code. Keep each file's existing voice
and density — these files argue for their rules, they don't list them. Do NOT bump manifest
versions (ARCHITECTURE.md: manifests are the version source of truth; /flow-pr owns the bump
decision at PR time, and quick 010 set the precedent of shipping a skill fix without one).
</context>

<tasks>
<task type="auto">
  <name>Task 1: Add the externally-mutable-state rule to autonomy.md</name>
  <files>plugins/devflow/references/autonomy.md</files>
  <action>
  Add a new section — place it immediately after "## Human gates", because it is the direct
  consequence of that list. Suggested heading: `## External state is a cache, never evidence`.

  Content to make (in autonomy.md's voice, roughly a paragraph plus a short rule):
  - `.planning/` records what a skill observed at a moment in time. For state DevFlow itself owns
    (phase status, plans, verification) the file *is* the truth. For state another system owns — PR
    open/merged/closed, check results, review decisions, remote branch position, deployment status —
    the file is a cache written by a past invocation, and nothing invalidates it.
  - The hazard is specific to the gate list above: every human gate is an action taken *outside this
    session*. The moment a skill emits `GATE | PR #N awaiting review/merge`, the state it just wrote
    is the state it is asking a human to change. A later invocation that reads that line and repeats
    the gate is not observing the world, it is quoting itself.
  - The rule: **before asserting or routing on state another system owns, re-read it live in the
    current invocation.** One command — `gh pr view <n> --json state,mergedAt,mergeStateStatus,reviewDecision`
    — is the whole cost. This is `CLAUDE.md`'s evidence-over-assertion rule applied to the one class
    of fact that changes while nobody is looking.
  - Fail-closed (`conventions.md` → Fail-closed guards): if the live read cannot run — `gh` missing,
    unauthenticated, network down — that is `BLOCKED`, not licence to fall back to the cached line.
    A cache that cannot be checked is not a cache that is current.
  - When live and recorded disagree, the live read wins and the skill corrects STATE in the same
    pass, so the next invocation does not rediscover the same drift.
  </action>
  <verify>`grep -n "re-read it live" plugins/devflow/references/autonomy.md` returns the new section; `python3 scripts/check-links.py` exits 0.</verify>
  <done>autonomy.md has the new section positioned after Human gates, covering: cache-not-evidence, the gate-quoting-itself hazard, the one-command rule, fail-closed on an unreadable read, and live-wins-and-corrects-STATE.</done>
</task>

<task type="auto">
  <name>Task 2: Make flow-next re-read PR state live and handle the out-of-band merge</name>
  <files>plugins/devflow/skills/flow-next/SKILL.md</files>
  <action>
  Three edits, all in the Routing section:

  (a) Immediately before the numbered routing list (or as a short bolded paragraph right after
  "Routing (first match wins):"), add the live-read precondition: if STATE records a PR, re-read it
  live — `gh pr view <n> --json state,mergedAt,mergeStateStatus,reviewDecision,url` — *before*
  evaluating rules 8-10, and route on that result, never on STATE's recorded line. Cite
  `autonomy.md` → External state is a cache, never evidence, rather than restating the argument.
  `gh` unavailable or unauthenticated → `FLOW: BLOCKED | cannot read PR #N state ({reason}) | next:
  gh auth login, then /flow-next` — never fall back to the recorded line.

  (b) Rewrite rules 9 and 10 so their preconditions read from the live state, and add the missing
  merged branch. Target shape:
    9. PR **live** open and not green (checks failing/pending, or unresolved bot review threads) →
       run `/flow-ci`. Unchanged otherwise.
    10. PR **live** open and green / awaiting human review or merge → stop, same GATE line as today.
    11. PR **live** merged → the merge *is* the answer to rule 10's gate. Clear `## Gate` to `none`,
        reset `## Run` (`Iteration: 1`, fresh `Started`, `Repeats: 0`), record the merge in STATE
        (Position + Session) and prepend a `.planning/JOURNAL.md` line, then route on: deploy-N/A
        with all phases verified → `FLOW: DONE | PR #N merged, roadmap verified | next: none`;
        otherwise → `FLOW: CONTINUE | PR #N merged | next: /flow-uat`.
    Also cover PR **live** closed unmerged: `FLOW: GATE | PR #N closed without merging | next:
    decide whether to reopen or re-branch` — a closed PR is a human decision, not a routing hop.

  (c) Amend rule 2's sentence about the `## Gate` block: a populated gate whose `asked` turns on
  external state (a PR merge, a deploy, a check) must be validated against the live read before it
  is surfaced — a gate the world already answered is not an open gate, and re-asking it is how a run
  parks forever on a question with no remaining answer. Clear it and continue routing instead.

  Renumbering: rule 11 is new; nothing else in the file references rules by number except the
  Deploy N/A paragraph (rules 7 and 8) — leave those references correct.
  </action>
  <verify>`grep -n "gh pr view" plugins/devflow/skills/flow-next/SKILL.md` shows the live read; the routing list contains a merged branch and a closed-unmerged branch; `python3 scripts/check-links.py` exits 0.</verify>
  <done>Rules 8-11 route only on live PR state; the out-of-band merge clears the gate, resets the run and continues; gh failure is BLOCKED; rule 2 no longer re-surfaces a gate the world has answered.</done>
</task>

<task type="auto">
  <name>Task 3: Make flow-status report PR state from a live read</name>
  <files>plugins/devflow/skills/flow-status/SKILL.md</files>
  <action>
  In the **Default** routing list, the two PR rows ("PR open but not green" and "PR merged to base")
  currently read as if STATE settles them. Add one short paragraph after the routing list (before
  the `deploy.tool` paragraph): the PR rows come from a live `gh pr view`, not from STATE's recorded
  line — cite `autonomy.md` → External state is a cache, never evidence. When the live state
  contradicts STATE, report the live state, say plainly that STATE was stale and what it claimed,
  and correct STATE in this pass. When `gh` cannot answer, say the PR check did not run and report
  the recorded line *as a recorded line with its date* — never as current. That is weaker than
  flow-next's BLOCKED on purpose: flow-status only reports, it does not advance the project, and a
  status command that refuses to print anything is worse than one that labels its uncertainty.

  Keep it to one paragraph in the file's existing voice. Do not touch the --all, --pause,
  --reset-run, or Plugin build sections.
  </action>
  <verify>`grep -n "gh pr view" plugins/devflow/skills/flow-status/SKILL.md` returns the new paragraph; `python3 scripts/check-links.py` exits 0.</verify>
  <done>flow-status's PR rows are explicitly live-read, the STATE-disagreement case is covered, and the gh-unavailable case degrades to a dated recorded line rather than a current claim.</done>
</task>

<task type="auto">
  <name>Task 4: Repair this repo's own stale STATE.md and log the answered gate</name>
  <files>.planning/STATE.md, .planning/DECISIONS.md, .planning/JOURNAL.md</files>
  <action>
  This is the live instance of the bug the first three tasks fix. Ground every claim in a live read
  first: run `gh pr list --state all --limit 5 --json number,state,mergedAt,title` and use its
  output, not this plan's summary of it.

  STATE.md (cap 1.5KB, rewrite sections in place, never append — the current file violates this):
  - Position: keep `Phase: 4 of 4 (complete) | Plans: 4/4 | Status: verified`. Collapse the two
    `Last:`/`Next:` pairs into one, reflecting reality: PRs #30 (v0.17.0, /flow-hooks) and #31
    (flow-pr direct-invocation gate) both merged to main on 2026-08-27; deploy is N/A, so a verified
    roadmap with the work merged is terminal. Next: the quick-011 work now in flight on
    `flow/stale-pr-state`.
  - Gate: reset to `none` on every field (`type: none`, `asked: none`, `options: none`,
    `default: none`, `plan: none | task: none` — match `{devflow_root}/templates/state.md`). The
    human answered it by merging #31.
  - Run: `Iteration: 1`, `Started:` the current UTC timestamp, `Repeats: 0`, `Signature:` cleared —
    an answered gate resets the rails (autonomy.md → Loop rails).
  - Decisions: add a `- quick 011: ...` line for the externally-mutable-state rule.
  - Session: collapse the two `Stopped:`/`Resume:` pairs into one current pair.

  DECISIONS.md (append-only, format in `{devflow_root}/templates/decisions.md` — read it first and
  match it exactly): one entry recording that the rule-10 gate on PR #31 was answered by the human
  merging it on GitHub on 2026-08-27, with #30 merged in the same window. Record the git identity
  and the SHA at the time (`git config user.email`, `git rev-parse --short HEAD`), per autonomy.md's
  "a DECISIONS.md entry when it is answered".

  JOURNAL.md: prepend one line (format `{devflow_root}/templates/journal.md`) — PRs #30/#31 merged;
  STATE had asserted both open, which is the defect quick 011 fixes.
  </action>
  <verify>`gh pr list --state open --json number` returns `[]`; `grep -n "asked:" .planning/STATE.md` shows `none`; `wc -c .planning/STATE.md` is under 1536.</verify>
  <done>STATE.md is under cap, has exactly one Last/Next pair and one Stopped/Resume pair, an empty Gate block and a reset Run block; DECISIONS.md records the answered gate with identity and SHA; JOURNAL.md has the merge line.</done>
</task>
</tasks>
</content>
