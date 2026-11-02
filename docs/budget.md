# Size budget

DevFlow's prompt text loads into every session that uses it, so its size is capped. `scripts/budget-count.sh --check` runs in CI and fails when any count is over its cap below. Caps only go up when Brian raises them; an over-budget change trims its own text instead.

Counting rules (git-tracked files only): **skills** = `plugins/devflow/skills/*/SKILL.md`; **agents** = `plugins/devflow/agents/*.md`; **commands** = `plugins/devflow/commands/*`; **hooks** = `plugins/devflow/templates/hooks/*-guard.py` plus `plugins/devflow/hooks/*`; **prompt_lines** = `wc -l` over every `*.md` outside `.planning/`, plus any non-`.md` file under agents/, commands/ or skills/. `prompt_bytes_info` (same files, bytes) and `planning_lines_info` (`.planning/**/*.md`) are reported but not capped: `.planning/` is this repo's own state and grows every phase by design.

| metric | cap |
|---|---|
| skills | 28 |
| agents | 13 |
| commands | 0 |
| hooks | 5 |
| prompt_lines | 4548 |
