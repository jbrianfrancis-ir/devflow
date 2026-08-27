<!-- .planning/TODOS.md — captured ideas and small tasks, not roadmap work. Newest first.
Format: `- [ ] YYYY-MM-DD | one line | why it matters`. Promote to a phase or /flow-quick when acted on. -->
# Todos

- [ ] 2026-08-27 | Nothing writes `config.json` → `git.branch` when a skill creates a `flow/<slug>` branch | `/flow-pr`'s pre-flight checks "on the feature branch (`git.branch`)" against that field. In this repo it had been stale since `flow/deploy-na-routing` — eight branches back — so the check was comparing against a branch that no longer mattered and would either pass vacuously or fail on correct work. Same cache-vs-fact shape as quick 011, but the stale value is DevFlow's own, which makes it a maintenance gap rather than an external-state one: either write the field when a branch is created, or drop it and read `git branch --show-current`.
