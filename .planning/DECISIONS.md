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
