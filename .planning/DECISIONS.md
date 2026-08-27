<!-- .planning/DECISIONS.md — APPEND-ONLY. The one DevFlow file with no size cap.
Every other state file is capped because it is read into context on every run; this one
is never read for warm-start, only written at gates and read by a human or an export.
So the usual rule inverts: never rewrite, never compact, never drop the oldest entry.
Newest entries go at the BOTTOM — an append-only log reads forward in time.

Records the answer to "who approved this, and when". A gate that stops the agent but
leaves no trace proves nothing after the fact: the decision happened in a conversation
that no longer exists. One entry per human gate in autonomy.md's list. -->
# Decisions

<!-- Entry format. `gate` is the gate type from autonomy.md (checkpoint-decision,
checkpoint-human-action, package-verification, secret-scan-clearance, consult-send,
pr-upstream, review-refute, uat-acceptance, release-confirmation, tag-push,
worktree-drop). `by` is the git identity that answered — `git config user.name` and
user.email — never a guess at who was at the keyboard. -->

## 2026-08-18 10:00 · checkpoint-decision
- **asked**: Phase 01 verification abstained on GitHub anchor-slug rules for cases this repo contains none of (duplicate headings, inline-code/punctuation headings, setext). How should the backstop truth be settled?
- **answered**: Accept the abstention (option 1). The rule stays unproven and unasserted; revisit if `docs/` ever introduces duplicate or inline-code headings. Explicitly NOT resolved by reading the slugger and declaring it correct.
- **by**: jbrianfrancis-ir <brianf@informativeresearch.com>
- **at**: d1dfd048f53c3e25dadbe586c5c6eff6d543c468 · phase 01 / plan 01-01

## 2026-08-19 21:55 · checkpoint-human-action
- **asked**: SC-04 — does a first-time reader get from the top of README to a running `/flow-new` without opening any `docs/` link? Nothing runnable can settle this; it needs a person reading the README cold.
- **answered**: PASS. Confirmed met, with no conditions or follow-up attached.
- **by**: jbrianfrancis-ir <brianf@informativeresearch.com>
- **at**: 1d1c398e02e633de777b60a67d42f8b8db65e504 · phase 03 / SC-04

## 2026-08-20 · pr-upstream
- **asked**: Open the pull request to merge `flow/sc-04-signoff` into `main`? Opening a PR is outward-facing and never auto-proceeds, so the branch sat pushed-but-unmerged awaiting this.
- **answered**: Approved — "create the PR to merge sc-04". No changes requested to scope or content.
- **by**: jbrianfrancis-ir <brianf@informativeresearch.com>
- **at**: 0eb2cd8 · PR for flow/sc-04-signoff

## 2026-08-21 · architecture-reversal
- **asked**: `ARCHITECTURE.md` defines a skill as `SKILL.md` with (`name`, `description`) frontmatter and is silent on hooks. `/flow-handsoff` needs a session `Stop` hook declared there, which reverses DevFlow's standing "ships no hooks" property — the same property `migrate-gsd.md` cites when telling migrators to strip project-level hooks. Permit skill-declared hooks, forbid them, or leave the question open?
- **answered**: Permit, with constraints. Amended `ARCHITECTURE.md` → Architecture & patterns to allow `hooks` in skill frontmatter under four limits (skill-scoped, `type: prompt` only, degrades where unsupported, structurally validated), recorded as `D-21`. The no-Node-runtime half of the old claim stands; only the hook half is reversed, and the prose asserting it in `migrate-gsd.md` and `docs/execution-model.md` was corrected in the same commit.
- **by**: jbrianfrancis-ir <brianf@informativeresearch.com>
- **at**: ffc5df7 · /flow-pr review round 1, architecture lens

## 2026-08-22 · scope-reversal
- **asked**: `/flow-pr`'s adversarial review ran four rounds against this branch and blocking findings went 3 → 4 → 6 rather than converging. Nearly every new blocker was introduced by the previous round's fix, concentrated in three areas: the `/flow-handsoff` hook conditions, the hand-rolled `hooks:` frontmatter validator, and the settings-snapshot guard. Keep fixing, relax ARCHITECTURE's no-dependency rule so a real YAML parser could validate the hook, or split the branch?
- **answered**: Split. Ship the parts that went quiet for two consecutive rounds — the `^gsd-[a-z0-9-]+$` injection filter, the `/flow-harden` DONE ordering fix, the deploy-N/A guards across five skills, the doc reconciliation and the version bump. Revert `/flow-handsoff`, its validator, its tests, and the `D-21` amendment permitting skill-declared hooks; rebuild it on its own branch where its driving loop can actually be exercised before review. The settings-snapshot check is downgraded from a gate to an advisory report, which removes the entire false-BLOCKED class rather than patching its latest instance.
- **why it is recorded**: `D-21` was approved earlier in this same session and is being reversed unshipped. The approval was real and so is the reversal; a log that kept only the first would misrepresent what happened. The reversal is not a judgement that skill-declared hooks are wrong — it is that a hand-rolled parser for an untyped format has unbounded bypass surface, and three consecutive rounds each closed one class of malformation and left the next.
- **by**: jbrianfrancis-ir <brianf@informativeresearch.com>
- **at**: 2417d36 · /flow-pr review round 4

## 2026-08-27 16:29 · pr-merge
- **asked**: PR #31 (flow-pr direct-invocation gate) is green — required checks pass, no open bot threads, no human review yet. Merge it? (rule-10 gate raised by `/flow-next`)
- **answered**: Merged on GitHub, outside this session, at 2026-08-27T16:28:21Z. PR #30 (v0.17.0, `/flow-hooks`) merged in the same window, at 2026-08-27T16:29:33Z — both answering the same standing gate. STATE.md had not been re-read live and still asserted both PRs open; that drift is the defect quick 011 fixes.
- **by**: jbrianfrancis-ir <brianf@informativeresearch.com>
- **at**: bf6f9c1 · PR #31 / PR #30
