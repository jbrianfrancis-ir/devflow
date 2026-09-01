# Incoming PR triage

## The problem this solves
Every review surface described in [`review.md`](review.md) — the plan panel, `/flow-pr`'s lenses,
adversarial review, adjudication — assumes the diff is yours: you wrote it, or an executor did, and
someone here decided it was worth opening. Contributions from outside the project don't arrive that
way. They arrive at a volume that scales with the project's visibility, not with how much attention
a maintainer has, and the honest failure mode isn't a bad merge — it's a good PR sitting unread
behind ten mediocre ones, because reading every incoming diff cold costs the same whether it's worth
it or not. `/flow-triage` is the pre-screen: it reads what's open, checks it against the project's
own law, and reduces the queue to what's actually worth a maintainer's first look. The concept is
DHH's description of his own OSS workflow (Lex Fridman podcast) — an agent that pre-screens
incoming contributions so a human's attention goes where it's earned.

## Per PR, not per lens
`/flow-pr`'s `flow-reviewer` agents parallelize across **lenses** of one diff — several judgment
angles on the same outgoing change. `/flow-triage`'s `flow-triager` agents parallelize across
**PRs** — one fresh-context pass per incoming pull request, holistic rather than lensed, because the
axis that needs to scale here is the number of contributions arriving, not the number of angles on
one of them. Each triager reads the PR's diff against `.planning/ARCHITECTURE.md` (pins,
`## Principles`, Forbidden list), `.planning/REQUIREMENTS.md`, `conventions.md`, `CONTRIBUTING.md`,
and `MAP.md` where each exists, and returns one verdict: `merge-candidate` (worth a first look),
`needs-human-judgment` (a real ambiguity, named rather than resolved — the triager doesn't get to
decide a Principle doesn't apply, the same way a refuted `blocking` review finding is a human gate
rather than a reviewer's own call), `needs-changes` or `reject` (a mechanical gap or an outright
conflict, with a drafted response), or `could-not-screen` (never dropped silently). Only
`merge-candidate` and `needs-human-judgment` reach the flagged table by default — `--all` widens the
report to every verdict tier, and explicit PR numbers as arguments are always screened regardless of
author or the default cap.

## Never posts
`/flow-triage` drafts; it doesn't send. A `draft_response` is output for a human to read, edit, and
post themselves — the same shape as `/flow-pr`'s PR body, drafted and then gated before `gh pr
create` ever runs. Posting a verdict or a drafted response to a third-party contributor's PR is a
named human gate in [`autonomy.md`](autonomy.md), not an autonomous step, and nothing in this skill
crosses it: no `--post`, no auto-close, no webhook. This is a first pass at the triage *judgment*,
not at any posting layer — if automation beyond drafting is what's needed next, it isn't here yet.

## Report, or a persisted export
By default `/flow-triage` is read-only and reports in the transcript, changing nothing the project
owns — the same shape as `/flow-audit`'s default pass. `--export` persists the report under
`.planning/triage/<date>.md` (secret-scanned before it's written, since it's an artifact meant to
leave the transcript) and is the one mode that commits and journals, mirroring `/flow-audit
--export`'s evidence pack.
