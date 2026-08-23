---
name: flow-harden
description: Production-hardening pass - audit the codebase against the Aspire production checklist, fix findings via a hardening plan. Use after all roadmap phases are verified, before /flow-uat. Supports --provider native|claude|codex.
---

# flow-harden

**Host setup**: resolve `devflow_root` and follow `{devflow_root}/references/hosts.md` before doing anything else.

**Agent provider**: accept `--provider native|claude|codex`. Resolve and dispatch every role in this run exactly as `{devflow_root}/references/hosts.md` specifies. The selected provider applies to all delegated roles unless this skill explicitly calls an external consultation engine. A missing or failed peer is fail-closed; report `FLOW: BLOCKED` with remediation and never fall back silently.

Context rules: read `.planning/STATE.md` first; paths not contents.

**Pre-flight**, in this order — the verified check comes **first**, because `DONE` is the contract's terminal state and must never be emitted on a state this skill did not establish (autonomy.md → Status line):

1. **All ROADMAP phases verified?** No → list what's pending and stop; hardening unfinished work wastes a pass. On a deploy-N/A project stop with `FLOW: CONTINUE | phase {N}/{T} not verified | next: /flow-next`, never `DONE` — a half-built project reported as finished is read that way by every consumer of the status contract (`docs/status-contract.md`), including `flow-fleet.py --json` and any `/goal` or `/loop` run driving on it.
2. **`.planning/config.json` → `deploy.tool`**: `null` means the project has no deployable surface (autonomy.md), so there is no production to harden for. Say so, point at the `D-NN` decision that recorded it, and stop — `FLOW: DONE` once the work is also merged, otherwise `FLOW: CONTINUE | roadmap verified, nothing to harden | next: /flow-pr`, since on these projects the merge *is* the end state and it has not happened yet.
3. Otherwise continue with the hardening pass below.

1. **Read** `{devflow_root}/references/aspire.md` (Detection, No-AppHost, Build-gate, Hardening-checklist sections).

2. **AppHost gate**: detect the Aspire AppHost and CLIs per the reference. No AppHost → the first hardening task is creating one that models every existing service and external resource (per the reference), gated by `aspire run` working locally. Missing CLIs → give the user the install pointers and stop.

3. **Audit** (read-only, this session): walk the hardening checklist against the codebase. If `.planning/ARCHITECTURE.md` exists, also diff it against reality (manifest versions, libraries in use, forbidden items) — drift is a finding. Check Aspire against the latest within its current major (per `aspire.md` Version policy): an available within-major update becomes a hardening task applied automatically; a *major* bump (e.g. 13→14) is a `checkpoint:decision`, not an auto-fix. Run `aspire publish` as the build gate. **Environment audit**: collect env/parameter names referenced in code (accessor greps per the mapper's list; never open `.env*`) and diff against ARCHITECTURE.md's Environment section — unlisted names, or any credential value found in the repo, are findings; also run the conventions.md secret scan over `git diff <base>...HEAD`. **Success criteria audit**: for each `SC-NN` in REQUIREMENTS.md, decide whether the build can meet it and say how you know. A criterion with a number (latency, throughput, capacity) that nothing measures is a finding — the fix is the measurement, not a guess that it's probably fine. A criterion that can only be judged by a human under real use (task-completion rates, satisfaction) is not a finding here: mark it *deferred to UAT* so it reaches the acceptance plan rather than being silently dropped. Never record an SC as met on the strength of it seeming likely. Record each finding as: what, where, why it blocks production. A finding whose production impact is genuinely unclear may be cross-checked via `/flow-oracle` before it drives a fix task.

4. **Fix**: no findings → skip to 5. Otherwise write the findings as a standard plan (spawn `flow-planner` with the findings, gap-mode style: smallest change per finding; phase dir `.planning/phases/H1-hardening/`), then spawn `flow-executor` per plan and `flow-verifier` after — same contracts as /flow-execute (templates and references from `{devflow_root}` as usual). Re-run `aspire publish` to confirm green.

5. **Close**: create `.planning/deploy/PIPELINE.md` if missing:
   ```markdown
   # Deploy pipeline
   | Env | azd env | Provisioned | Last deploy (SHA, date) | Result | URLs |
   |-----|---------|-------------|--------------------------|--------|------|
   | uat | — | no | — | — | — |
   | prod | — | no | — | — | — |
   ```
   Update STATE.md (Status: hardened, Next: `/flow-pr` — integrate before deploying). Commit `chore(flow): hardening pass` on the feature branch, prepend a `.planning/JOURNAL.md` line (format `{devflow_root}/templates/journal.md`; create if missing), and `git push origin <branch>`. Repeat runs are cheap — re-audit and report "already hardened" when clean.

Hardening fixes are code, so they land on the feature branch like any other work and reach base via `/flow-pr`; deploy (`/flow-uat`, `/flow-release`) runs from merged base code.

End with the status line per `{devflow_root}/references/autonomy.md` — clean: `FLOW: GATE | hardened; open a PR before deploy | next: /flow-pr`; findings being fixed: `CONTINUE`; missing CLIs/AppHost decision: `GATE`.
