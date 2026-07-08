# Verification method

Goal-backward, not task-forward: start from each plan's `must_haves.truths` and prove each one. Never start from "which tasks ran".

For each truth, prove it one of three ways: **run it** (execute the behavior), **test it** (run the relevant tests), or **trace it** (open the code path named in `key_links` and confirm it's wired: imported, called, routed — not just present). Three verdicts:
- **VERIFIED** — proof in hand; record the evidence (command output, test name, code trace).
- **GAP** — provably missing or broken; record why and where. You report gaps, you don't fix them.
- **HUMAN** — needs human judgment or a real environment; add to the human checks list.

Never trust SUMMARY claims — spot-check the commits and code. A file existing proves nothing about behavior. Artifacts must exist AND be wired in.

Consolidate `human_checks` from all SUMMARY frontmatter plus your HUMAN verdicts into one batched list.

Output `VERIFICATION.md` per the template. `status: pass` only if every truth is VERIFIED and there are no gaps; `gaps` if any gap (one line each); `human_needed` if only human checks remain. Learnings: ≤3 bullets, only things future phases must know (conventions discovered, traps, implied decisions).
