<!-- .planning/reviews/LEDGER.md — APPEND-ONLY, UNCAPPED, oldest first. Never rewritten, never reordered.
     Same discipline as DECISIONS.md: a closed round is immutable, and only the adjudicator reads this
     file (in its own fresh context), so length costs the orchestrator nothing. Created on first round.
     Doctrine: references/adjudication.md. -->
# Review ledger

Findings ruled on this repo, oldest first. Read by three later audiences: whoever executes the
fixes, the next round's settled-ground screen, and whoever asks in six months why a known defect
was left alone.

---

## Round {N} — {YYYY-MM-DD} · {what was reviewed}

**Range:** `{base}...{sha}` | **Reviewer:** {role/provider/model, one per lens} | **Adjudicated by:** {role/provider/model}
**Findings in: {N} · Rows out: {N}** {say which IDs merged, when any did}

### Situation
{One paragraph: what was reviewed, what state it was in, what came back at the top level. No rulings.
A reader who stops here should know what happened and nothing they would have to unlearn.}

### Re-verification
<!-- What gives every ruling below its weight. Command verbatim + real output, never a paraphrase.
     Mark any check whose result contradicted what you expected. A section containing only
     confirmations of what you already believed is self-review with extra steps. -->
- `{command}` → {real output, trimmed to what matters} — bears on #{N}
- {where nothing could be executed: the standard used instead, and the source quoted}

### Rulings
<!-- Both axes on every row. Keep the reviewer's numbering; prefix with the reviewer tag
     (codex-3, claude-3) when more than one reviewer fed this round. -->

| # | Finding | Lens | Verdict | Disposition |
|---|---------|------|---------|-------------|
| 1 | {title, verbatim from the report} | {lens} | **CONFIRMED** | **FIX NOW** — {minimal fix, named} → `{file or plan task}` ({commit, backfilled}) |
| 2 | {title} | {lens} | **REFUTED** | **NO ACTION** — {the command and its output; not the reasoning} |
| 3 | {title} | {lens} | **SETTLED ALREADY** | **NO ACTION** — round {N} row {M}, or `{file:line}` quoted |
| 4 | {title} | {lens} | **CONFIRMED** | **FIX LATER** — `{backlog path/URL that already exists}` |
| 5 | {title} | {lens} | **CONFIRMED** | **ACCEPTED AS-IS** — {why we ship with it}; approved by {who}, {date} |
| 6 | {title} | {lens} | **COULD NOT DETERMINE** | **VERIFY** — {the concrete check}; {blocks / does not block} |
| 7 | {title} | {lens} | **OWNER RULING REQUIRED** | **PENDING OWNER** — see Owner decisions |

### Could-not-verify items
<!-- One entry per item the reviewer flagged as unverifiable, each with both axes. It flagged a gap
     honestly; an unruled gap reads downstream as a pass. Omit the section only when there were none. -->
- CNV-1: {item} — **COULD NOT DETERMINE** / **VERIFY** — {the check}; {blocks / does not block}

### Process findings
<!-- Findings about the review or the brief, not the code — their fix lands in the prompt.
     Omit when there were none. -->
- {what it was} — {real?} — {what changed as a result}

### Owner decisions required
<!-- Omit when none. Once answered, the answer is recorded here verbatim and dated — an owner ruling
     that lives only in chat is the same failure as a review that lives only in chat. -->
#### Q1 — {one-line question}
**What turns on it:** {the trade-off in the user's terms, not the code's}
**Options:** {A} — {costs, buys, forecloses} · {B} — {same}
**Recommendation:** {yours, one clause of why — a recommendation is not a ruling}
**Blocks:** {what cannot start until answered, or "nothing"}
**Answered:** {verbatim}, {date}, by {git identity}

### Upheld
<!-- What the reviewer checked and found sound. One line each, no elaboration.
     This is what stops the next round re-targeting ground already walked. -->
- {claim examined and upheld}

### Not settled by this round
{Explicit. An unstated gap reads as a pass — the same rule the reviewer is held to.}

<!-- Later rounds append below this line. Never edit a closed round: a ruling shown to be wrong gets a
     NEW row citing the one it supersedes. Ask each later round explicitly whether an earlier fix
     opened a new path to the failure it closed. -->
