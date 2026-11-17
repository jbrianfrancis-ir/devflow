# Size budget

DevFlow's prompt text loads into every session that uses it, so its size is capped. `scripts/budget-count.sh --check` runs in CI and fails when any count is over its cap below. Caps only go up when Brian raises them; an over-budget change trims its own text instead.

Counting rules (git-tracked files only): **skills** = `plugins/devflow/skills/*/SKILL.md`; **agents** = `plugins/devflow/agents/*.md`; **commands** = `plugins/devflow/commands/*`; **hooks** = `plugins/devflow/templates/hooks/*-guard.py` plus `plugins/devflow/hooks/*`; **prompt_lines** = `wc -l` over the text under `plugins/devflow/` that agents load or Read: every `*.md`, plus `*.json`, `*.txt`, `*.yml` and `*.yaml` under `references/` and `templates/`, plus any file under agents/, commands/ or skills/. `.json` references count because agents Read them as instructions and data. Excluded: `plugins/devflow/scripts/**` and hook `*.py` (executed code, not prompt text; hooks have their own cap) and the plugin manifests `.claude-plugin/**` and `.codex-plugin/**`. Reported but not capped: `prompt_bytes_info` (same files, bytes); `planning_lines_info` (`.planning/**/*.md`, this repo's own state, grows every phase by design); `repo_docs_lines_info` (every other tracked `*.md` outside `plugins/devflow/` and `.planning/`: README, CHANGELOG, AGENTS.md, CLAUDE.md, docs/), which never reaches an agent.

| metric | cap |
|---|---|
| skills | 28 |
| agents | 13 |
| commands | 0 |
| hooks | 5 |
| prompt_lines | 4548 |
