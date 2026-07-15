---
name: flow-status
description: Show where the project is and what to run next; --pause records a clean stopping point. Use at session start, when lost, or before stepping away.
---

# flow-status

No `.planning/` → point to `/flow-new`. STATE.md missing but `.planning/` exists → offer reconstruction (ROADMAP statuses + newest SUMMARY frontmatter → rewrite STATE.md from `${CLAUDE_PLUGIN_ROOT}/templates/state.md`).

**Default**: read STATE.md + ROADMAP.md (table only). Print: position (phase, plans done, status), blockers, open TODO count (`.planning/TODOS.md`), last activity (STATE `Last:` plus the top line of `.planning/JOURNAL.md` when present), and the next command by this routing:
- current phase has no plans → `/flow-plan N`
- plans exist, not all SUMMARYs → `/flow-execute N`
- VERIFICATION has gaps → `/flow-plan N --gaps`
- phase verified, more phases → `/flow-plan N+1`
- all phases verified → `/flow-harden`
- hardened, work not yet PR'd/merged → `/flow-pr` (push origin + PR upstream)
- PR merged to base → `/flow-uat`, then sign-off, `/flow-release` (see `.planning/deploy/PIPELINE.md` if present)

Mention: `/flow-next` advances one step automatically; see the README's Autonomous operation recipes (`/goal` + `/flow-next`, `/loop /flow-next`).

Session hygiene: `/clear` is safe anytime — state persists in `.planning/`. Clear at phase boundaries or when context is heavy; never mid-`/goal`/`/loop` (it ends the run). See README → Session hygiene.

**--pause**: rewrite STATE.md's Session section (Stopped: exact position incl. in-flight wave/plan; Resume: the command + any context needed cold), commit `chore(flow): pause` if commit_docs. Resume later needs no special command — every skill reads STATE.md first.

End with the status line per `${CLAUDE_PLUGIN_ROOT}/references/autonomy.md` reflecting the routed state: `FLOW: <CONTINUE|GATE|BLOCKED|DONE> | <position> | next: <command>`.
