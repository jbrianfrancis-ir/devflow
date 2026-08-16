# Adjudication — ruling on review findings

Reviewers produce findings. Somebody has to decide which are true and what happens about each, and those are **two different questions**. Collapsing them is how "we looked at it" becomes the record of a defect nobody fixed.

Used by `/flow-pr --adversarial`. The ruling happens in a **third context**: the author wrote the code, a reviewer found things, and neither of them rules — an orchestrator that is about to write the fixes is not a neutral judge of whether they are needed.

## Two axes, always both

**Verdict** — is the finding true?
- `CONFIRMED` — reproduced. Say how.
- `CONFIRMED (partial)` — part established, part not. Name which is which.
- `REFUTED` — disproved by evidence, not by re-reading.
- `COULD NOT DETERMINE` — the check to settle it is known but was not run.
- `SETTLED ALREADY` — ruled in an earlier round or fixed by a locked decision. Cite it: file:line, quoted.
- `OWNER RULING REQUIRED` — the answer turns on risk appetite or product direction, not on facts.

**Disposition** — what happens now?
- `FIX NOW` — the minimal fix, named, with the file or plan task it lands in.
- `FIX LATER` — deferred, with the backlog entry that **already exists**.
- `ACCEPTED AS-IS` — true, and we ship anyway. A human gate (`autonomy.md`).
- `NO ACTION` — nothing is owed, because the verdict says so.
- `VERIFY` — the concrete check that would settle it, and whether it blocks.
- `PENDING OWNER` — waiting on the question in the ledger's owner section.

Never one word for both. "Accepted" alone means *the finding is real* and *we are shipping with it* at the same time, and the reader cannot tell which was meant — which is exactly the ambiguity that lets a known defect look adjudicated.

## Symmetric evidence — disproving costs what proving cost

A `blocking` finding must carry a concrete failure scenario (`flow-reviewer.md`). `REFUTED` is held to the same bar: **a command that ran and its real output**, or the code path traced to the line — not "I re-read it and it's fine." The code is what produced the behavior, so reading it and finding it coherent is circular; this is the same rule `verification.md` applies to backstop truths, for the same reason.

Where nothing can be executed — a plan, a design target — say so in one line and name the standard used instead: the source cited and quoted that settles the claim.

A reviewer's figures that you could not reproduce is a finding about the review, not a refutation of it. Say which.

## Dismissal has to cost something

`FIX LATER` requires the backlog entry to exist **before** the row is written — a `TODOS.md` line or an issue, cited by path or URL in the disposition. A promise to record it later is the same as not recording it. This is the only guard against the disposition that costs nothing to assign and quietly absorbs every finding nobody wants to argue about.

Backfill each `FIX NOW` row as the work lands, with its commit. A ledger still saying `queued` three phases later is telling you something true.

## An unruled gap reads as a pass

Every finding gets both axes — including the reviewer's own "could not verify" items, which are the ones most likely to be dropped precisely because nobody claimed them. Same rule the reviewer is held to: silence about a gap is indistinguishable downstream from having checked it and found nothing (`conventions.md` → Fail-closed guards).

Findings about the *review itself* — contradictory instructions, a stale citation, a leaked placeholder — are wanted, but their fix lands in the prompt, not the code. Rule them in their own block, out of the main table.

## Settled ground

Screen every incoming finding against the existing ledger **before** re-verifying anything: an already-ruled claim is `SETTLED ALREADY` with the round and row cited, and costs nothing further. This is what stops round 3 from re-arguing round 1, and it only works because the ledger is durable.

Screening is a citation, not a judgment call. If you cannot point at the row that settled it, it is not settled.

## Rounds

The ledger appends; it is never rewritten. **A closed round is immutable** — a later round that shows an earlier ruling was wrong writes a *new* row citing the row it supersedes and says what changed (new evidence, or a ruling made without it). The original stays as written: the record of having been wrong is part of what the ledger is for, and a log that only contains correct rulings is not a record.

A round is closed when every finding has both axes filled, no `PENDING OWNER` is outstanding, and the `FIX NOW` queue is backfilled with commits. Until then it is the current round and gets filled in place.

Ask each later round one question explicitly: **did an earlier fix open a new path to the failure it closed?** It is cheaper to answer here than to have the next reviewer find it.

## What it never does

It never fixes anything — the output is the ledger and a queue. It never decides whether to ship: risk appetite is the owner's, and a finding whose answer depends on it is `OWNER RULING REQUIRED`, not a judgment call made quietly in a subagent.
