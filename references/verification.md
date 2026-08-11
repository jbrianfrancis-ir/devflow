# Verification method

Goal-backward, not task-forward: start from each plan's `must_haves.truths` and prove each one. Never start from "which tasks ran".

For each truth, prove it one of three ways: **run it** (execute the behavior), **test it** (run the relevant tests), or **trace it** (open the code path named in `key_links` and confirm it's wired: imported, called, routed — not just present). Three verdicts:
- **VERIFIED** — proof in hand; record the evidence (command output, test name, code trace).
- **GAP** — provably missing or broken; record why and where. You report gaps, you don't fix them.
- **HUMAN** — needs human judgment or a real environment; add to the human checks list.

Never trust SUMMARY claims — spot-check the commits and code. A file existing proves nothing about behavior. Artifacts must exist AND be wired in.

Evidence must be an **anchor** — a signal that can't argue back: a command that actually ran with its output recorded, a test that actually passed, a code path traced to the line. "Should pass", SUMMARY claims, and agent self-reports are not evidence. must_haves are frozen: never weaken, reword, or reinterpret a truth to match what was built — a truth you can't prove is a GAP (or HUMAN), not a rewording.

## backstop truths — abstain, don't certify
`must_haves.backstop_truths` are truths the plan declared **non-inferable**: the requirements never settled what the correct behavior is. The tag comes from the planner, not from your own read of the code, and you do not re-litigate it — a truth is in that list or it isn't.

For each one, exactly one question: **is there explicit evidence — a test that actually exercises this specific case, or the behavior directly observed — that pins the answer?**
- Yes → `VERIFIED`, evidence recorded, like any other truth.
- No → **`HUMAN`**, reason `non-inferable — needs a held-out test`. Never `VERIFIED`. Reading the implementation and finding it coherent is *not* evidence here: the code is what defined the behavior, so treating it as proof of the behavior is circular.

You are not being asked to say what the right answer is. If you could work that out, the truth wouldn't be non-inferable. Report only "the spec doesn't settle this and nothing pins it down" and route it to a human — naming the wrong reason while abstaining is fine; certifying it is not.

A backstop truth **never** produces `gaps`. It is not a defect, so it does not send the phase back to `--gaps` replanning; it lands in the batched human checks with a specific ask: *write a test that fixes this behavior, or state the rule so it becomes inferable.*

## Coincidental reliance — does it hold for a guaranteed reason?
For every truth you mark `VERIFIED`, ask one follow-up: **does this hold because something guarantees it, or because of an accident that happens to be true right now?** An executor optimizes to make the goal observably true, and the shortest path to green is often an incidental one. Flag three shapes:
- **Undeclared precondition** — it works only because some state happens to be present that nothing sets up on purpose (a row a fixture seeds, a directory that happens to exist, a config another phase left behind).
- **Incidental ordering or side effect** — it works because of an execution order or a side effect in unrelated code that nothing enforces.
- **Fixture-only truth** — it is true under the test harness but not in the real runtime (mocked at the boundary that matters, or asserted against a stub).

This is an **advisory, not a verdict**: the truth stays `VERIFIED` and the phase can still pass. Record it as `VERIFIED (coincidental-reliance)` in the truths table with one line on what the reliance is, and carry it into learnings when future phases could break it. The point is that fragile-but-passing is named where someone can act on it, instead of surfacing three phases later as a mystery regression.

Consolidate `human_checks` from all SUMMARY frontmatter plus your HUMAN verdicts into one batched list.

Output `VERIFICATION.md` per the template. `status: pass` only if every truth is VERIFIED and there are no gaps; `gaps` if any gap (one line each); `human_needed` if only human checks remain — including when the sole reason is an abstained backstop truth. The status vocabulary is unchanged: an abstention routes through the existing `HUMAN` verdict and `human_needed` status, and advisories never change a status. Record abstained backstop truths in the `unverified` frontmatter list so a driver can see them without parsing the table. Learnings: ≤3 bullets, only things future phases must know (conventions discovered, traps, implied decisions) — a coincidental-reliance flag that a later phase could trip over belongs here.
