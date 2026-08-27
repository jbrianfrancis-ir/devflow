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

The two PR rows above come from a live `gh pr view`, never from the line STATE has recorded
(autonomy.md → External state is a cache, never evidence). When the live
state contradicts STATE, report the live state, say plainly that STATE was stale and what it had
claimed, and correct STATE in this pass. When `gh` cannot answer, say the PR check did not run and
report the recorded line as a recorded line with its date — never as current. That is weaker than
`/flow-next`'s `BLOCKED` on purpose: `flow-status` only reports, it does not advance the project,
and a status command that refuses to print anything is worse than one that labels its uncertainty.

When `.planning/config.json` → `deploy.tool` is `null` the project has no deployable surface (autonomy.md): drop the harden/uat/release rows, route *all phases verified, not yet PR'd* straight to `/flow-pr`, and report a verified-and-merged roadmap as `DONE` rather than pointing at a deploy step it will never take. Only an explicit `null` — missing or unreadable config means the project deploys.

A populated `## Gate` block outranks the routing: print `asked` and the numbered `options` verbatim, note who has to answer, and route to that instead. Report a non-zero `## Run` `Repeats` as "the loop has not moved in K iterations at `{signature}`" — the run is in trouble before the rail trips, and this is where a human notices. A malformed `## Run` block is `BLOCKED`, not a shrug.

If the routing disagrees with what's on disk (ROADMAP status vs SUMMARYs vs VERIFICATION), say so and point at `/flow-audit` rather than guessing which artifact is right.

**Plugin build** (default path, one line, only when there is something to say): the skills running this session come from an installed DevFlow build, not from the repo you are looking at. Every DevFlow repo carries the self-bootstrap block (`conventions.md` → Plugin self-bootstrap), so it has its **own** pinned install alongside the user-scope one, pinned at whatever was current when the repo was first opened — and nothing reconciles them. Read this project's entry from `~/.claude/plugins/installed_plugins.json` (`plugins["devflow@devflow"]`, the `scope: "project"` entry whose `projectPath` is this repo) and compare it against the newest version that file and `~/.claude/plugins/marketplaces/devflow/.claude-plugin/marketplace.json` mention. Behind → say so and name both versions: routing rules live in the skills, so an old build is a correctness risk, not just a stale one. Level → say nothing; a line that always prints stops being read.

Two things this must not claim. The newest version *this machine knows of* is not the published release — the marketplace cache (`~/.claude/plugins/marketplaces/devflow`) is a git clone that moves only when Claude Code refreshes it, so matching it is not proof of being current, and the line should say "newest known" rather than "latest". **Check that cache's own age** from the mtime of its `.git/FETCH_HEAD`: older than a few days, or no fetch on record, means a published release could be invisible here — say so and give `claude plugin marketplace update devflow`. This is the half that actually bites: a version can be merged, tagged and released while every local reading still shows the old number, and the release then reaches nobody. Never fetch to find out; this is a local read, and "the reading is N days old" is the honest signal rather than "you are behind". And when the registry is missing entirely there is no Claude plugin system here (Codex, a container) — that is not applicable, not a failure; when it exists but will not parse, say the check did not run (`conventions.md` → Fail-closed guards). Never report a version you did not read.

Mention: `/flow-next` advances one step automatically; the autonomy recipes are in `docs/autonomy.md` (`/goal` + `/flow-next`, `/loop /flow-next`).

Session hygiene: `/clear` is safe anytime — state persists in `.planning/`. Clear at phase boundaries or when context is heavy; never mid-`/goal`/`/loop` (it ends the run). See `docs/autonomy.md` → Session hygiene.

**--all** (fleet board — every DevFlow project on this machine, not just this repo): run `python3 {devflow_root}/scripts/flow-fleet.py` (append roots as args to override; `--json` when a caller wants to parse it). Print its output verbatim — it is already a table; do not re-summarize or re-sort it. Then add at most three lines of your own: the one project you'd touch first and why, and any `NO-DECL` repos (offer `/flow-migrate`-style self-bootstrap, never add it silently). The scanner prints the plugin-build spread and flags `OLD-PLUGIN` repos itself — do not restate it, but do act on it: if the project you are routing someone to is one of them, say so in that line, because they are about to run old routing rules. The scanner reads STATE/ROADMAP/JOURNAL/config + git metadata per project, and outside the project tree the Claude plugin registry and cached marketplace manifest (that is how it knows a build is stale) — no source, no `.env*`, and no network.

First run with no roots configured scans the parent of the current directory. Offer to write `~/.devflow/fleet.json` (`{"roots": ["~/dev"], "stale_days": 3}`) so later runs cover the right tree. Exit status is 1 when any project needs a human — useful to a driving session.

Status line for `--all`: report the fleet, not this repo — `FLOW: GATE | fleet: N projects, M need a human | next: cd <path> && <command>` when any do, else `FLOW: CONTINUE | fleet: N projects, none blocked | next: cd <path> && <command>` naming the project you'd advance first.

**--pause**: rewrite STATE.md's Session section (Stopped: exact position incl. in-flight wave/plan; Resume: the command + any context needed cold), commit `chore(flow): pause` if commit_docs. Resume later needs no special command — every skill reads STATE.md first.

**--reset-run**: reset STATE.md's `## Run` block (`Iteration: 1`, `Started:` now, `Repeats: 0`, `Signature:` cleared) — the manual counterpart to the automatic reset an answered gate performs. Use it after fixing whatever the loop was stuck on, or to re-arm a rail that tripped. Say what the counters were before clearing them: the numbers are the evidence for why the run stopped, and silently zeroing them loses the only record. It does not touch `## Gate` — an unanswered gate stays unanswered.

End with the status line per `{devflow_root}/references/autonomy.md` reflecting the routed state: `FLOW: <CONTINUE|GATE|BLOCKED|DONE> | <position> | next: <command>`.
