---
name: flow-status
description: Show where the project is and what to run next; --all boards every DevFlow project on the machine, --pause records a clean stopping point, --reset-run re-arms the autonomous loop rails. Use at session start, when lost, when tracking parallel work, or before stepping away.
---

# flow-status

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

No `.planning/` → point to `/flow-new` (except `--all`, which needs no project). STATE.md missing but `.planning/` exists → offer reconstruction (ROADMAP statuses + newest SUMMARY frontmatter → rewrite STATE.md from `{devflow_root}/templates/state.md`).

**Default**: read STATE.md + ROADMAP.md (table only). Print: position (phase, plans done, status), blockers, open TODO count (`.planning/TODOS.md`), last activity (STATE `Last:` plus the top line of `.planning/JOURNAL.md` when present), and the next command by this routing:
- current phase has no plans → `/flow-plan N`
- plans exist, not all SUMMARYs → `/flow-execute N`
- VERIFICATION has gaps → `/flow-plan N --gaps`
- phase verified, more phases → `/flow-plan N+1`
- all phases verified → `/flow-harden`
- hardened, work not yet PR'd/merged → `/flow-pr` (push origin + PR upstream)
- PR open but not green (failing/pending checks, unresolved bot threads) → `/flow-ci`
- PR merged to base → `/flow-uat`, then sign-off, `/flow-release` (see `.planning/deploy/PIPELINE.md` if present)

A populated `## Gate` block outranks the routing: print `asked` and the numbered `options` verbatim, note who has to answer, and route to that instead. Report a non-zero `## Run` `Repeats` as "the loop has not moved in K iterations at `{signature}`" — the run is in trouble before the rail trips, and this is where a human notices. A malformed `## Run` block is `BLOCKED`, not a shrug.

If the routing disagrees with what's on disk (ROADMAP status vs SUMMARYs vs VERIFICATION), say so and point at `/flow-audit` rather than guessing which artifact is right.

Mention: `/flow-next` advances one step automatically; the autonomy recipes are in `docs/autonomy.md` (`/goal` + `/flow-next`, `/loop /flow-next`).

Session hygiene: `/clear` is safe anytime — state persists in `.planning/`. Clear at phase boundaries or when context is heavy; never mid-`/goal`/`/loop` (it ends the run). See `docs/autonomy.md` → Session hygiene.

**--all** (fleet board — every DevFlow project on this machine, not just this repo): run `python3 {devflow_root}/scripts/flow-fleet.py` (append roots as args to override; `--json` when a caller wants to parse it). Print its output verbatim — it is already a table; do not re-summarize or re-sort it. Then add at most three lines of your own: the one project you'd touch first and why, and any `NO-DECL` repos (offer `/flow-migrate`-style self-bootstrap, never add it silently). The scanner reads only STATE/ROADMAP/JOURNAL/config + git metadata — no source, no `.env*`.

First run with no roots configured scans the parent of the current directory. Offer to write `~/.devflow/fleet.json` (`{"roots": ["~/dev"], "stale_days": 3}`) so later runs cover the right tree. Exit status is 1 when any project needs a human — useful to a driving session.

Status line for `--all`: report the fleet, not this repo — `FLOW: GATE | fleet: N projects, M need a human | next: cd <path> && <command>` when any do, else `FLOW: CONTINUE | fleet: N projects, none blocked | next: cd <path> && <command>` naming the project you'd advance first.

**--pause**: rewrite STATE.md's Session section (Stopped: exact position incl. in-flight wave/plan; Resume: the command + any context needed cold), commit `chore(flow): pause` if commit_docs. Resume later needs no special command — every skill reads STATE.md first.

**--reset-run**: reset STATE.md's `## Run` block (`Iteration: 1`, `Started:` now, `Repeats: 0`, `Signature:` cleared) — the manual counterpart to the automatic reset an answered gate performs. Use it after fixing whatever the loop was stuck on, or to re-arm a rail that tripped. Say what the counters were before clearing them: the numbers are the evidence for why the run stopped, and silently zeroing them loses the only record. It does not touch `## Gate` — an unanswered gate stays unanswered.

End with the status line per `{devflow_root}/references/autonomy.md` reflecting the routed state: `FLOW: <CONTINUE|GATE|BLOCKED|DONE> | <position> | next: <command>`.
