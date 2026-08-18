# Provenance

Who made which change, and who approved it.

## Attribution
Every commit DevFlow produces carries git trailers (`DevFlow-Agent: executor/claude/sonnet`, `DevFlow-Plan: 03-02`), so `git log --grep='^DevFlow-Agent:'` answers "which of this came from an agent" over any range; the committer stays the human whose credentials made the commit, because the trailer records what assisted, not who is accountable. The exact trailer syntax and field rules are specified in [`conventions.md`](../plugins/devflow/references/conventions.md).

## Decision log
Every human gate — checkpoint decisions, secret-scan clearances, consult sends, UAT acceptance, release confirmation — appends to `.planning/DECISIONS.md`: what was asked, what was actually answered (refusals included), by which git identity, at which SHA. It is the one uncapped state file, never rewritten, and `JOURNAL.md` overflow now rolls into `.planning/history/` instead of being dropped. The authoritative list of which actions are human gates is specified in [`autonomy.md`](../plugins/devflow/references/autonomy.md).

## Export
If you have ever been asked which AI tools touched a repo and what they changed, this is the part that is otherwise unreconstructable — DevFlow is not telemetry and does not try to be, but intent → change → evidence → approval all land in files you can hand someone. `/flow-audit --export [--since <date|tag|sha>]` assembles exactly that into `.planning/exports/AUDIT-<date>.md`: access by role with its sandbox class, changes grouped by plan with the unattributed remainder named rather than hidden, the decision log verbatim including refusals, verification status per phase, and the controls actually enforced. It leads with what it *cannot* cover — agents run outside DevFlow, review bots, session telemetry, pre-adoption history — because a pack that overstates itself is worth less than none. Secret-scanned like any outbound bundle, and never sent: distribution is your call.
