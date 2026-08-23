# DevFlow status contract — the agent-facing interface

DevFlow is a **crew member, not an orchestrator**. It runs inside whatever substrate you already use — tmux, herdr, cmux, Orca, Superset, Conductor, the desktop app, plain terminal tabs — and exposes its state as files and one status line so an outside session (a "foreman", a dashboard, a cron job, a context repo) can observe and drive it without ever reading a screen.

This document is that interface. Everything here is stable: it does not change without a minor version bump, and DevFlow's own skills are held to it. `docs/blitzos.md` is one consumer of this contract; this file is the general form.

## 1. The status line

Every orchestrating skill ends its final message with exactly one line:

```
FLOW: <state> | <position> | next: <command>
```

| State | Meaning for a driver |
|---|---|
| `CONTINUE` | Autonomous work remains. Run `next`. No human needed. |
| `GATE` | A human must decide or act. `<position>` names what. **Never auto-answer.** |
| `BLOCKED` | An error needs investigation before anything proceeds. |
| `DONE` | Roadmap fully verified (or released, after `/flow-release`). |

Grammar: one line, three `|`-separated fields, `next:` prefix on the third. Parse it with `grep -oE '^FLOW: [A-Z]+ \| .* \| next: .*$'` against the last message — not with a model. The full state list and the permanent human gates live in `plugins/devflow/references/autonomy.md`.

## 2. Files (read these; never screen-scrape)

All paths are relative to the project repo. A repo is DevFlow-managed **iff** `.planning/STATE.md` exists.

| File | Contract |
|---|---|
| `.planning/STATE.md` | ≤1.5KB, rewritten in place, never appended. `## Position` holds `Phase: N of M (name) \| Plans: d/t \| Status: <token>`, then `Last:` and `Next:`. `## Blockers` is a bullet list or `- none`. `## Session` holds `Stopped:` / `Resume:`. `## Gate` is `none`, or a populated gate record (below). `## Run` carries the autonomous-loop rails (below). Quote these lines verbatim — they are written to be quoted. |
| `.planning/JOURNAL.md` | ≤2KB, **newest first**, one line per state-changing run: `- YYYY-MM-DD \| /flow-cmd \| outcome \| FLOW-STATE`. The top line is "last activity". Lines added during a session are that session's record. Overflow past the cap moves to `.planning/history/JOURNAL-<YYYY>.md` — same line format, chronological, uncapped — so the full run history is `history/*` followed by `JOURNAL.md` reversed. |
| `.planning/DECISIONS.md` | Append-only, **uncapped**, oldest first. One `## YYYY-MM-DD HH:MM · <gate>` section per answered human gate, with `asked` / `answered` / `by` / `at` bullets. The record of who authorized what; never rewritten, so a driver may cache by byte offset. Absent until the first gate. |
| `.planning/ROADMAP.md` | Phase table with per-phase status. |
| `.planning/config.json` | `git` block (`base`, `origin`, `upstream`, `branch`); `agents.provider` (`native`, `claude`, or `codex`) and optional `agents.models.<role>` tier overrides; optional `autonomy` block (`max_iterations` 40, `max_repeats` 3, `max_hours` null) tuning the loop rails; `workstream` block when applicable. Absent keys mean the defaults, not "off". |
| `phases/NN-slug/*-SUMMARY.md` | Frontmatter: `agent` (`role/provider/model` that executed the plan), `commits`, `deviations`, `human_checks`, `deferred`. |
| `phases/NN-slug/VERIFICATION.md` | Frontmatter: `status` (`pass`/`gaps`/`human_needed`), `gaps`, `unverified` (backstop truths the verifier abstained on — non-inferable behavior awaiting a held-out test; these are not defects and never become gaps). |
| `.planning/reviews/LEDGER.md` | Append-only, **uncapped**, oldest first. One `## Round N` section per adjudicated review (`/flow-pr --adversarial`), each with a rulings table carrying **two axes** per finding: a verdict (`CONFIRMED` / `REFUTED` / `COULD NOT DETERMINE` / `SETTLED ALREADY` / `OWNER RULING REQUIRED`) and a disposition (`FIX NOW` / `FIX LATER` / `ACCEPTED AS-IS` / `NO ACTION` / `VERIFY` / `PENDING OWNER`). Closed rounds are immutable — a superseded ruling gets a new row citing the old one — so a driver may cache by byte offset. Absent until the first adversarial review. |

`STATE.md` and `config.json` are **branch-local** — in a multi-worktree repo each workstream has its own. See `plugins/devflow/references/conventions.md` → Parallel workstreams.

### The gate record

Every skill that emits `FLOW: GATE` also populates `STATE.md`'s `## Gate` block, and clears it to `none` when the gate is answered:

```
## Gate
type: decision                     # decision | human-action | approval
asked: Job queue backend not settled by REQ-07
options:                           # present for decisions; max 4, one line each
  1. Postgres — matches the ARCHITECTURE pin; needs a dev container
  2. SQLite — zero infra; no concurrent writers
default: none                      # `none`, or the option number that applies absent an answer
plan: 03-02 | task: 2              # omitted when the gate isn't plan-scoped
```

This is the **one structured exception** to "never parse skill prose" (§5). `<position>` on the status line stays a human-readable clause; the block is the machine-readable half, so a driver can render the actual question and the actual choices wherever the human is instead of waking someone to read a transcript. `asked` is the same text that lands in `DECISIONS.md` under `asked` when the gate is answered, so question and answer join on it.

**A driver may surface options. It may never select one.** The gate list in §4 is unchanged — structure changes how legibly a question reaches a human, not whether one is needed.

### The run rails

`## Run` is the autonomous loop's only cross-iteration memory, owned by `/flow-next`:

```
## Run
Iteration: 7 | Started: 2026-08-15T09:12Z | Repeats: 1
Signature: rule5:phase03:plans2/4:verif-gaps
```

`Signature` encodes what the routing matched. Unchanged between iterations means the run is not moving, and `/flow-next` stops with `BLOCKED` once `Repeats` reaches `autonomy.max_repeats` (default 3) rather than emitting `CONTINUE` forever. `Iteration` and `Started` back the `max_iterations` (default 40) and `max_hours` (default off) rails. Absent = cold start; **malformed = `BLOCKED`**, never read as zero. A driver should treat a rising `Repeats` as a run in trouble before the rail trips.

### Commit attribution

Every commit DevFlow produces carries git trailers naming what produced it:

```
DevFlow-Agent: <role-or-skill>/<provider>/<model>
DevFlow-Plan: NN-MM
```

`provider` is always concretely `claude` or `codex` (never `native`); `model` is `-` when the host does not expose it; `DevFlow-Plan` appears on plan-scoped commits only. Standard trailer syntax, so git's own tooling reads it — `git log --grep='^DevFlow-Agent:'` to list agent-produced commits in a range, or `git log --format='%h %s | %(trailers:key=DevFlow-Agent,valueonly)'` to extract the value per commit (empty for commits without it). Absence of the trailer means the commit did not come from DevFlow — it does **not** mean no agent touched it, since nothing outside DevFlow is required to attribute itself. The committer identity remains the human whose credentials made the commit; the trailer records what assisted, not who is accountable.

`.planning/exports/AUDIT-<YYYY-MM-DD>.md` is an **output**, not an input: a dated evidence pack built from the files above plus git metadata by `/flow-audit --export`. Drivers should regenerate it rather than parse it, since every figure in it is derived from sources they can already read.

A reader of this contract reads **only** the files above plus git metadata. Never source, never `.env*`, never key files.

## 3. The fleet scanner

```
python3 {devflow_root}/scripts/flow-fleet.py [ROOT ...] [--json] [--stale-days N] [--depth N]
```

`{devflow_root}` is the installed plugin directory (the parent of `skills/`); in a
clone of this repo it is `plugins/devflow/`. The scanner is stdlib-only, so a driver
can also vendor it directly.

Walks roots for DevFlow projects (including git worktrees of any repo it finds, even outside the roots) and returns one row per project. `--json` emits:

```json
{ "scanned": ["~/dev"], "stale_days": 3,
  "projects": [{
    "path": "...", "repo": "owner/name", "branch": "flow/payments", "worktree": false,
    "phase": "3/6", "plans": "2/4", "status": "executing", "position": "<STATE Position, verbatim>",
    "next": "/flow-execute 3", "last": "...", "resume": "...", "blockers": ["..."],
    "journal": "<top JOURNAL line, verbatim>", "flow": "GATE", "last_date": "2026-08-10",
    "age_days": 0, "dirty": 2, "flags": ["WT"], "needs_human": true,
    "gate": { "type": "decision", "asked": "...", "options": ["Postgres — ...", "SQLite — ..."],
              "default": "none", "plan": "03-02", "task": "2" },
    "run": { "iteration": 7, "started": "2026-08-15T09:12Z", "repeats": 1,
             "signature": "rule5:phase03:plans2/4:verif-gaps" } }] }
```

`gate` and `run` are `null` when the blocks are absent or say `none`. `gate.options` is `[]` for a gate with no choices (most `human-action` gates).

`flags`: `ON-BASE` (committing to the base branch — a convention violation), `DIRTY:n`, `STALE:nd` (in-flight with no activity), `WT` (git worktree), `NO-DECL` (missing the plugin self-bootstrap block), `GIT-UNKNOWN` (git could not be read here), `FLOW-UNKNOWN` (no parseable `FLOW:` state — the check did not run).

**Unanswerable checks are `null`, not a clean value.** `dirty` and `worktree` are `null` — never `0` or `false` — when git could not be consulted, and `git_readable` says whether it could. A consumer must not read `null` as "fine"; the project is flagged `GIT-UNKNOWN` and counted in `needs_human` for exactly that reason (conventions.md → Fail-closed guards). `flow: "unknown"` is the same shape: an unparseable or missing `JOURNAL.md` means the state check did not run, so it flags `FLOW-UNKNOWN` and counts in `needs_human` — it does not mean the project is fine.

**Exit status is the cheap signal**: `0` when every project is fine, `1` when any needs a human. A foreman can branch on that without parsing anything. Roots default to `~/.devflow/fleet.json` (`{"roots": ["~/dev"], "stale_days": 3}`), else the parent of the working directory.

## 4. Driving a DevFlow session from outside

```
cd <repo> && /flow-status          # orient (cold start needs nothing else)
cd <repo> && /flow-next            # advance exactly one step, then stop with FLOW:
```

`/flow-next` is the driver: one step per invocation, bounded turns, always terminating in a status line. Loop it (`/loop /flow-next`) or gate it (`/goal FLOW says DONE, GATE, or BLOCKED, or stop after 40 turns`). `/flow-ci` drives an open PR to green the same way. `/flow-status --all` boards every project; `/flow-workstream` adds a parallel worktree.

**Gates a driver must surface and never answer itself** (authoritative list in `plugins/devflow/references/autonomy.md`): checkpoint decisions and human-actions; failed-package (typosquat) verification; a fail-closed secret-scan hit; sending an external consult bundle; opening a PR to upstream; replying to human PR reviewers; shipping a confirmed review finding `ACCEPTED AS-IS`; UAT acceptance and sign-off; production release confirmation; pushing tags; anything destructive in git. Hard rule, not a gate: never commit to the base branch.

## 5. What not to build against

- **Don't screen-scrape the TUI.** Terminal output is not an interface; the files above are. Anything you'd learn by scraping is in `STATE.md` or the status line.
- **Don't parse skill prose.** Only the `FLOW:` line and the file formats in §2 are stable. The `## Gate` block is the deliberate exception and the reason the rest can stay prose: when you need the question and the options as data, read the block — never scrape `<position>` or the transcript for them.
- **Don't summarize `STATE.md` or `JOURNAL.md` with a model at scan time.** They are already capped and written to be quoted verbatim — a model pass adds cost, latency, and drift.
- **Don't spawn a provider CLI per workflow step.** DevFlow stays in the interactive host and uses native subagents by default. `claude -p` or `codex exec` is reserved for an explicitly selected, bounded cross-provider role.
- **Don't treat a `GATE` as a retry.** It means a human is required. Re-running the same command produces the same gate.
