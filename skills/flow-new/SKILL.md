---
name: flow-new
description: Initialize a Flow project (greenfield or existing repo) — creates .planning/ with requirements, roadmap, and state. Use when starting Flow work in a repo that has no .planning/ directory.
---

# flow-new

Context rules (all flow skills): read `.planning/STATE.md` before acting when it exists; pass subagents file *paths*, never contents; read only frontmatter of phase artifacts; keep orchestrator output terse.

**Pre-flight**: if `.planning/` exists → stop, point to `/flow-status`. If not a git repo (`git rev-parse --git-dir`) → offer `git init` (required for commits).

**Git setup** (read `${CLAUDE_PLUGIN_ROOT}/references/conventions.md`): resolve the base branch — `dev` if it exists (local or remote), else `main` (create `main` if the repo has no commits yet). Detect remotes: `origin` (your working remote); `upstream` if present (fork model). Create and switch to a feature branch off the base — `git checkout -b flow/<project-slug> <base>` (skip if already on a non-base feature branch). All code lives under `src/` off the repo root.

1. **Detect existing code**: `git ls-files | head -50` + look for manifests (package.json, *.csproj, pyproject.toml, go.mod). If real code exists, spawn agent `flow-mapper` with: template path `${CLAUDE_PLUGIN_ROOT}/templates/codebase-map.md`, output path `.planning/codebase/MAP.md`. Use its digest for questioning and roadmap.

2. **Understand**: if the user gave an idea file or description (or `--auto`), work from that. Otherwise read `${CLAUDE_PLUGIN_ROOT}/references/questioning.md` and run the bounded Q&A (≤5 questions, one round, AskUserQuestion).

3. **Research** (only if `--research`, the user asks, or the domain has real unknowns — offer, don't assume): spawn `flow-researcher` with the 2–4 questions that block roadmap decisions; output `.planning/research/RESEARCH.md`.

4. **Write** from templates at `${CLAUDE_PLUGIN_ROOT}/templates/` (architecture.md, project.md, requirements.md, roadmap.md, state.md):
   - `ARCHITECTURE.md` — the user's exact stack: runtime/frameworks/libraries **with versions**, patterns, Azure/Aspire resources, forbidden items. If they provided a spec (file or description), transcribe it faithfully; otherwise ask for it directly (most users have one) — only offer to draft it from MAP.md/research if they truly don't. These are hard constraints on every agent; show it for confirmation before continuing.
   - `DESIGN.md` — if the project has a UI, ask whether to link a Claude Design (claude.ai/design) design system now: yes → run the `/flow-design` flow (Skill tool) after init; no design system → skip, note "none" in config.
   - `PROJECT.md` — what, core value, out of scope, D-NN decisions from Q&A.
   - `REQUIREMENTS.md` — REQ-NN one-liners with acceptance hints. **Show to user for confirmation before the roadmap** (skip confirmation in `--auto`).
   - `ROADMAP.md` — 3–6 phases; each: name, one-line goal, REQ-IDs. Every REQ-ID in exactly one phase; each phase independently verifiable.
   - `STATE.md` — Position: phase 1 of N, status planning, Next: `/flow-plan 1`.
   - `config.json` — `{"mode":"interactive","commit_docs":true,"deploy":{"tool":"aspire+azd"},"git":{"base":"<dev|main>","origin":"origin","upstream":"<upstream|null>","branch":"flow/<slug>"}}` (`--auto` → `"mode":"auto"`).
   - `.claude/settings.json` (repo root) — the plugin self-bootstrap block from conventions.md (Plugin self-bootstrap section), so cloud/fresh sessions install DevFlow automatically. Merge into an existing file, never overwrite.

5. **Commit** (if commit_docs): `chore(flow): initialize project` on the feature branch, then `git push -u origin <branch>`. Print the roadmap table, then the autonomy recipes:
   - Drive to completion: `/goal FLOW says DONE or GATE, or stop after 40 turns` then `/flow-next`
   - Background cadence: `/loop /flow-next`
   If the user indicated they'll drive autonomously, set `"mode":"auto"` in config.json.

End with the status line per `${CLAUDE_PLUGIN_ROOT}/references/autonomy.md`: `FLOW: CONTINUE | initialized, N phases | next: /flow-plan 1`.
