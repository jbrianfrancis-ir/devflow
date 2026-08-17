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
