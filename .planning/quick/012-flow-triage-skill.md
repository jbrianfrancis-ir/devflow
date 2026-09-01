<!-- .planning/quick/012-flow-triage-skill.md — ad-hoc mini-plan (flow-quick), not tied to ROADMAP. -->
---
phase: quick-012
plan: 01
wave: 1
depends_on: []
files_modified:
  - plugins/devflow/agents/flow-triager.md
  - plugins/devflow/skills/flow-triage/SKILL.md
  - plugins/devflow/templates/triage-report.md
  - plugins/devflow/references/autonomy.md
  - plugins/devflow/references/hosts.md
  - plugins/devflow/scripts/flow-agent.py
  - scripts/validate-plugin.py
  - plugins/devflow/.claude-plugin/plugin.json
  - plugins/devflow/.codex-plugin/plugin.json
  - .claude-plugin/marketplace.json
  - README.md
  - docs/README.md
  - docs/triage.md
  - docs/execution-model.md
autonomous: true
requirements: []
must_haves:
  truths:
    - "/flow-triage screens open, externally-authored pull requests against ARCHITECTURE.md, REQUIREMENTS.md, and conventions.md, and produces a merge-readiness summary without editing any file the audit reads"
    - "/flow-triage never posts a comment, requests changes, closes, or merges a third-party PR — every drafted response is transcript/report output for a human to paste, never sent by the skill itself"
    - "Only merge-candidate and needs-human-judgment verdicts are flagged for human review by default; needs-changes and reject stay out of the human's queue unless --all is passed"
    - "A PR whose diff cannot be fetched (gh missing/unauthenticated, or the fetch fails) is reported as could-not-screen, never silently dropped from the summary"
    - "Every fetched diff is secret-scanned (conventions.md pattern) before any hunk of it can appear in a report row or a drafted response; a hit reports file/line/pattern class only, never the value"
    - "references/autonomy.md's human-gates list names posting a triage verdict/response to a third-party PR as a gate, alongside the existing outward-facing gates"
    - "validate-plugin.py's expected skill/agent counts, the two plugin manifests, and the root marketplace.json version all agree after the addition (22 skills, 12 agents, matching version)"
    - "flow-agent.py's READ_ONLY_ROLES, hosts.md's Read-only roles/Model tiers prose, and flow-triager.md's frontmatter all name the same role (triager) consistently, per validate-plugin.py's cross-check"
  backstop_truths:
    - "Default external-contributor filter (author_association not in OWNER/MEMBER/COLLABORATOR) versus screening every open PR regardless of author is a policy choice REQUIREMENTS.md never settled for this project — recorded as a design decision below, not inferable from anything already in the repo"
  artifacts:
    - plugins/devflow/skills/flow-triage/SKILL.md
    - plugins/devflow/agents/flow-triager.md
    - docs/triage.md
  key_links:
    - "flow-triage/SKILL.md spawns flow-triager per PR, exactly as flow-pr/SKILL.md spawns flow-reviewer per lens"
    - "docs/README.md indexes docs/triage.md under a new 'Incoming contributions' section"
---

<objective>
Design and implement `/flow-triage`: a read-only skill that pre-screens open, externally-authored
pull requests against a project's own law (ARCHITECTURE.md, REQUIREMENTS.md, conventions.md) and
produces a merge-readiness summary, so a maintainer's attention goes to the PRs worth reading
closely rather than to every PR that landed in the queue. Concept: DHH's OSS-workflow description
on the Lex Fridman podcast (IRA-420) — an agent that pre-screens incoming contributions and
surfaces only the promising ones — adapted to DevFlow's existing review machinery rather than
built from scratch.
</objective>

<context>
This is engineering-manager-authored design + implementation for `jbrianfrancis-ir/devflow`
(IRA-445), done directly rather than via a live `/flow-new` → `/flow-plan` → `/flow-execute` run,
because the authoring session has no interactive DevFlow harness attached to this checkout. The
discipline is reproduced by hand: a design pass before any file changes (this document), then
implementation matching the file's own frontmatter contract, then a PR — never merged by its own
author (`AGENTS.md` review standard: no worker merges its own work; this PR goes to
`jbrianfrancis-ir` for review, same as any other external contribution this skill is built to
triage).

**What already exists to build on.** `/flow-pr` (`plugins/devflow/skills/flow-pr/SKILL.md`)
already reviews an *outgoing* diff by spawning one fresh-context `flow-reviewer`
(`plugins/devflow/agents/flow-reviewer.md`) per **lens** — correctness, security, architecture,
conventions, reuse, tests, design — in parallel, dedupes findings, and classifies them
`blocking`/`should-fix`/`nit`. `/flow-audit` (`plugins/devflow/skills/flow-audit/SKILL.md`) is the
other close analog: strictly read-only, reports in the transcript by default, an optional
`--export` mode persists an evidence pack under `.planning/` and is the only mode that commits or
journals.

**Why this isn't just "flow-reviewer, pointed at someone else's branch."** The axis needing
parallelism is different. `/flow-pr` parallelizes across *lenses* of one diff — always the same
diff, several judgment angles. Triage parallelizes across *PRs* — potentially many diffs, arriving
at volume from people who don't share this session's context and won't read a `blocking`/`nit`
vocabulary built for a diff's own author. One fresh-context `flow-triager` per PR, not per lens,
doing one holistic pass each: does this align with what the project's law already says, not "what
does the correctness lens think of it." Deep multi-lens review still happens later, through
`/flow-pr`'s own machinery, once a human has actually decided to take the PR on — triage's job
ends at "here's what's worth your first look," not at grading the diff.

**Design decisions this document settles (read `plugins/devflow/references/hosts.md`,
`plugins/devflow/references/autonomy.md`, `plugins/devflow/references/conventions.md`,
`.planning/ARCHITECTURE.md` before touching any file — they are the law this skill screens against
and the conventions it must itself follow):**

1. **Inputs.** Default: `gh pr list --state open --json number,title,author,isDraft,updatedAt` on
   `origin` (and `upstream` when set), then `gh api repos/{owner}/{repo}/pulls/{n}` per candidate for
   `author_association` — `gh pr list`/`gh pr view --json` don't expose that field (verified against
   installed `gh` 2.46.0: `Unknown JSON field: "authorAssociation"`; the REST `pulls` endpoint carries
   it as `author_association`). Drop drafts, capped to the 20 most recently updated — an explicit
   `flow-triage 123 456` always screens exactly those PRs, uncapped, regardless of author or draft
   state (an explicit ask is never rate-limited). Default author filter: skip
   `author_association` in `OWNER`/`MEMBER`/`COLLABORATOR` — this is a filter for *external*
   contributions, named in the title; `--all` widens it to every open PR and prints full detail for
   every verdict tier, not only the flagged ones.
2. **What each `flow-triager` reads**: the PR's diff (`gh pr diff <N>`), title/body/author,
   `.planning/ARCHITECTURE.md` (pins, Principles, Forbidden list), `.planning/REQUIREMENTS.md` when
   present, `{devflow_root}/references/conventions.md`, `CONTRIBUTING.md` when present, and
   `codebase/MAP.md` when present (catches a PR reimplementing something that already exists). No
   network access beyond `gh`/git against the repo's own configured remotes.
3. **Verdict, not a lens list.** `merge-candidate` (aligned with pins/Principles, in scope, tests
   present where behavior changed, CI green or the failure looks unrelated) → flagged.
   `needs-human-judgment` (a debatable edge of a Principle/pin, ambiguous scope, conflicts with an
   open `D-NN`, or a real idea with a gap that isn't mechanical to name) → flagged, with the
   specific ambiguity named — the triager never resolves it, exactly as a refuted `blocking` finding
   is a human gate elsewhere in this repo, never the reviewer's own call. `needs-changes` (a
   mechanical, nameable gap: missing regression test, a conventions.md violation, needs rebase) →
   not flagged by default, drafted comment produced. `reject` (violates Forbidden/a Principle
   outright, duplicates existing functionality, or is out of scope of anything the project asked
   for) → not flagged by default, drafted decline reason produced. `could-not-screen` (diff
   unfetchable) → always listed, never dropped (`conventions.md` → Fail-closed guards).
4. **Gating — this is the load-bearing decision.** `/flow-triage` never posts, closes, requests
   changes, or merges anything on GitHub. Every drafted response is output only — printed in the
   transcript, or written to the `--export` report — for a human to read, edit, and paste
   themselves. This mirrors `/flow-pr` step 5 (the PR body is drafted, then a human gate clears it
   before `gh pr create` runs) and matches this repo's own `autonomy.md` philosophy that anything
   outward-facing to a third party is a human gate, never an autonomous step. `references/
   autonomy.md`'s human-gates list is extended to name this explicitly, so a future skill (or a
   `/flow-triage --post` someone is tempted to add later) doesn't quietly cross this line without
   the same review this document went through.
5. **Output.** Default mode: read-only, reports in the transcript, changes and commits nothing
   (mirrors `/flow-audit`'s default pass — "this run changed nothing" is also why it journals
   nothing). `--export` is the one mode that writes: `.planning/triage/<YYYY-MM-DD>.md` from
   `templates/triage-report.md`, secret-scanned before it's written (an outbound-shaped artifact,
   same as `/flow-audit --export`'s evidence pack), and the one mode that commits
   (`chore(flow): triage report <date>`, attribution trailer) and journals.

**Prototype honesty.** This is a first pass at the triage *judgment* — verdict + drafted response
— not at any posting/automation layer. No `--post`, no auto-close, no webhook, nothing that acts on
GitHub beyond `gh pr list`/`gh pr diff` reads. Say so in the skill's own description rather than
letting a maintainer discover the gap by trying `--post` and finding nothing there.

**Files this touches beyond the two new skill/agent files**, and why each is load-bearing rather
than incidental: `scripts/validate-plugin.py` hardcodes skill/agent counts (21/11 → 22/12) and
cross-checks agent frontmatter against `flow-agent.py`'s role sets and `hosts.md`'s prose lists —
all three must agree or the plugin fails its own smoke gate. Both plugin manifests and the root
marketplace.json version must move together (`ARCHITECTURE.md` → "Manifests are the version source
of truth") — this is a new capability in shipped content, so it's a **minor** bump (0.18.0 →
0.19.0), decided here rather than left to `/flow-pr` to guess at PR time since there's no `/flow-pr`
run driving this change. `docs/execution-model.md`'s "20 shared Agent Skills and 11 subagents" line
is already one skill stale against this repo's actual 21/11 (pre-existing drift, not this change's
doing) and would become two stale against the true 22/12 if left untouched while sitting directly
beside the count this change moves — corrected in the same commit rather than left to compound.
</context>

<tasks>
<task>
  <name>Add the flow-triager agent and flow-triage skill</name>
  <files>plugins/devflow/agents/flow-triager.md, plugins/devflow/skills/flow-triage/SKILL.md, plugins/devflow/templates/triage-report.md</files>
  <action>
    Write `flow-triager.md` mirroring `flow-reviewer.md`'s structure and voice: frontmatter
    (`name: flow-triager`, `tools: Read, Bash, Grep, Glob`, `model: opus` — a judgment role per
    `hosts.md`'s tiering, read-only per decision 2/4 above), one assigned PR per invocation, the
    verdict vocabulary from decision 3, a `TRIAGE` return block (pr/author/verdict/summary/
    concerns/draft_response), the secret-scan rule from decision 2/4, and "be honest about volume"
    language matching `flow-reviewer.md`'s own (a clean sweep returns real verdicts, not padding).

    Write `flow-triage/SKILL.md` mirroring `flow-pr/SKILL.md`'s host-setup/provider preamble and
    `flow-audit/SKILL.md`'s read-only-by-default shape: pre-flight (gh auth, PR set resolution per
    decision 1), spawn `flow-triager` once per PR in parallel (batched, e.g. 5 concurrent, to bound
    cost — matches decision 2's per-PR fan-out), assemble the report (table of every screened PR,
    full `TRIAGE` blocks for flagged rows only unless `--all`), `--export` mode per decision 5, and
    the closing `FLOW:` status line (`DONE` never applies here — triage doesn't complete a roadmap;
    `CONTINUE` on a clean or unflagged sweep, `GATE` when something is flagged or a report was
    exported, `BLOCKED` on gh unavailable/unauthenticated).

    Write `templates/triage-report.md` mirroring `templates/audit-export.md`'s shape (frontmatter
    summary counts, then the same "what this covers / does not" honesty section, then the flagged
    table, then per-PR TRIAGE blocks) for the `--export` artifact.
  </action>
  <verify>python3 scripts/validate-plugin.py passes with the new files present and counts updated (see next task)</verify>
  <done>flow-triage/SKILL.md and flow-triager.md exist, frontmatter-valid, and describe the gating in decision 4 explicitly (never posts/closes/merges)</done>
</task>
<task>
  <name>Register the new role and update counts/manifests</name>
  <files>plugins/devflow/references/autonomy.md, plugins/devflow/references/hosts.md, plugins/devflow/scripts/flow-agent.py, scripts/validate-plugin.py, plugins/devflow/.claude-plugin/plugin.json, plugins/devflow/.codex-plugin/plugin.json, .claude-plugin/marketplace.json, docs/execution-model.md</files>
  <action>
    Add `"triager"` to `flow-agent.py`'s `READ_ONLY_ROLES` set; add it to `hosts.md`'s "Read-only
    roles:" prose list and its "Judgment roles" list in Model tiers (top tier, per decision 1's
    `model: opus`). Add the human-gate sentence from decision 4 to `autonomy.md`'s gates list.
    Bump `expected 21 skills`/`expected 11 Claude role agents` in `validate-plugin.py` to 22/12.
    Bump both plugin manifests and the root marketplace.json `version` from `0.18.0` to `0.19.0`
    together. Correct `docs/execution-model.md`'s "20 shared Agent Skills and 11 subagents" to
    "22 shared Agent Skills and 12 subagents".
  </action>
  <verify>python3 scripts/validate-plugin.py; python3 -m unittest discover -s tests -v; python3 scripts/check-links.py — all three exit 0</verify>
  <done>Smoke command (ARCHITECTURE.md → ## Smoke) passes clean</done>
</task>
<task>
  <name>Document the command</name>
  <files>README.md, docs/README.md, docs/triage.md</files>
  <action>
    Add a `/flow-triage` row to README.md's command table (new `triage` loop category, since it
    doesn't fit core/ad-hoc/integrate/deploy — it operates on PRs the project didn't write). Add
    `docs/triage.md` narrating the design (mirrors `docs/review.md`'s prose style: what problem it
    solves, the per-PR-not-per-lens distinction, the verdict vocabulary, the never-posts gate) and
    index it from `docs/README.md`.
  </action>
  <verify>python3 scripts/check-links.py reports 0 failures</verify>
  <done>docs/triage.md exists, is linked from docs/README.md, and every internal reference it makes resolves</done>
</task>
</tasks>
