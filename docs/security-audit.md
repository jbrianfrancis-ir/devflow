# Security audit (opt-in)

## Off by default
`/flow-security-audit` is an **optional** pre-production gate. It does not run on any other `/flow-*`
invocation: `/flow-next` never routes to it, and `/flow-harden`, `/flow-uat`, and `/flow-release` do not
require it. Turn it on per run, by invoking it — run it before `/flow-uat` or `/flow-release` when a
human asks for a pre-production security audit, a pen-test-style review, or a full vulnerability review.
There is no config key that makes it default-on.

## How it differs from `/flow-harden`
`/flow-harden` checks production readiness against a checklist and fixes what it finds.
`/flow-security-audit` hunts for vulnerabilities that cross a real trust boundary, and a checklist
deviation is explicitly *not* one of those. It reports and never edits target source; fixes go through
`/flow-quick` or `/flow-plan` like any other work.

## Two modes
- **Guidance** (default) — questions, one focused path, or triage of a single finding. Answered in the
  transcript; no files written.
- **Full audit** — only on an explicit request. Recon → coverage-led hunt → candidate validation →
  structured findings → independent verify → report. Hunters and verifiers are fresh read-only
  `flow-reviewer` contexts, and whoever finds a candidate never confirms it.

## Verdicts
Every candidate ends as `confirmed` (it gets a severity), `needs_validation` (a deployment fact the repo
cannot show, with a safe check for the owner to run; no severity), or `rejected` (with the reason). The
audit is source-only and never probes live endpoints. Targets with LLM surfaces get extra units for
prompt injection, tool/agent authority, and model-output handling.

## Where artifacts go
Outside the repo at `~/security-audit-skill/<repo>/run-N/` by default. `.planning/security-audit/run-N/`
is used only when `.gitignore` already covers that directory, so audit output is never committed by
accident.

## Upstream
The method is adapted from Cloudflare's
[security-audit-skill](https://github.com/cloudflare/security-audit-skill) (MIT), which also has the deep
companion files (attack classes, `AI-AND-LLM.md`, sandboxed local execution) and the findings/ledger
validators. DevFlow keeps a thin wrapper and links to that repo. It does not install the upstream skill for
you; whether and where to install it is your decision.

The full contract is [`flow-security-audit/SKILL.md`](../plugins/devflow/skills/flow-security-audit/SKILL.md).
