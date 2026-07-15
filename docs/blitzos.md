# DevFlow ↔ BlitzOS context repos — fork integration contract

Design contract for a [BlitzOS](https://github.com/blitzdotdev/blitzos) fork that manages DevFlow projects. **Not loaded by any skill** — this is for fork implementers (scanner, builder, portal, bootstrap). DevFlow-side counterparts live in `references/conventions.md` (secret scan, credential modes, session journal, self-bootstrap) and `references/autonomy.md` (status line, human gates).

## 1. Detection (evidence-based)

A member repo is **DevFlow-managed** iff `.planning/STATE.md` exists. The plugin is **declared** iff `.claude/settings.json` at the repo root contains both keys (byte-exact contract, from conventions.md "Plugin self-bootstrap"):

```json
{
  "extraKnownMarketplaces": {
    "devflow": { "source": { "source": "github", "repo": "jbrianfrancis-ir/devflow" } }
  },
  "enabledPlugins": { "devflow@devflow": true }
}
```

Managed-but-undeclared is a scanner finding (the project predates self-bootstrap): offer to add the block, never add it silently. The scanner reads only `.planning/STATE.md` (≤1.5KB), the `ROADMAP.md` table, and the top lines of `.planning/JOURNAL.md` — **never `.env*`, key files, or source**.

## 2. Company-brain block (per DevFlow repo, ≤4 lines)

Inside the context repo's <200-line `CLAUDE.md`, render each DevFlow member repo as:

```
- <owner/repo> [devflow] — <STATE.md Position line verbatim, incl. "Next:">
  last: <newest JOURNAL.md line>
  flow: <last observed FLOW: state, or "unknown">
```

STATE.md's Position and JOURNAL's line format are stable, capped, rewrite-in-place artifacts — safe to quote verbatim; never summarize them with a model at scan time.

## 3. Context-repo `.claude/settings.json`

The builder merges the same marketplace block from §1 into the **context repo's own** `.claude/settings.json` (merge, never overwrite; never remove existing marketplaces/plugins). Sessions launched at the context-repo level then get `/flow-*` commands; member repos already self-bootstrap individually.

## 4. Work loop

Boot → BlitzOS warm start (`sessions/INDEX.md` + recent records) → `cd` into the member repo → `/flow-status` → drive with `/flow-next` (one step per turn), or `/goal FLOW says DONE or GATE, or stop after 40 turns` + `/flow-next`.

Every DevFlow skill ends with exactly one machine-checkable line the portal/feed parses:

```
FLOW: CONTINUE|GATE|BLOCKED|DONE | <position> | next: <command>
```

- `CONTINUE` → keep driving (next `/flow-next`).
- `GATE` / `BLOCKED` → stop; raise a steering notification carrying `<position>` (it names what the human must decide/do).
- `DONE` → write the session record (§5), stop.

**Permanent human gates the fork must surface and never auto-answer** (from `references/autonomy.md`): checkpoint decisions and human-actions; failed-package (typosquat) verification; a fail-closed secret-scan hit; UAT acceptance + SIGNOFF.md; production release confirmation; opening a PR to upstream; pushing tags; anything destructive in git. Hard rule: never commit to the base branch.

## 5. Session-record mapping

One BlitzOS `sessions/` record per session, assembled from DevFlow artifacts (no model summarization needed):

| Record field | Source |
|---|---|
| date, repo | session metadata |
| index entries | the `.planning/JOURNAL.md` lines **added this session**, verbatim (they double as `sessions/INDEX.md` entries) |
| work detail | `phases/*/NN-MM-SUMMARY.md` frontmatter: `commits`, `deviations`, `human_checks` |
| verification | `phases/*/VERIFICATION.md` frontmatter: `status`, `gaps` |
| diff summary | `git log --oneline <base>..<feature-branch>` |

## 6. bootstrap.sh hook

- **Default rail**: no-op for DevFlow repos — the `.claude/settings.json` self-bootstrap installs the plugin at session start; the session's platform git credential covers selected repos (selection = blast radius). DevFlow's first push (`/flow-new`) doubles as the push canary.
- **Power mode**: `BLITZOS_GIT_TOKEN` arrives as an env var only — never written to disk or git config (matches conventions.md Token mode). DevFlow's push canary validates it.
- Defense in depth: DevFlow's fail-closed secret scan runs **inside** every session (before each commit and push) in addition to the fork's own builder-side scanner — both fail closed; neither replaces the other.
