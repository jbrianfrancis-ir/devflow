<!-- .planning/ROADMAP.md — cap 2KB. One row per phase; status: pending → planned → executing → verified. -->
# Roadmap

| NN | Phase | Goal (one line) | Requirements | Status |
|----|-------|-----------------|--------------|--------|
| 01 | Link safety net | Build the stdlib link checker and wire it into CI and smoke, before any documentation moves | REQ-09, REQ-10, REQ-11, SC-02, SC-05 | planned |
| 02 | Carve out docs/ | Move the deep-dive topics out of README into focused `docs/` pages, one topic per file | REQ-05, REQ-07, REQ-12, SC-03 | pending |
| 03 | Rebuild README | Rewrite README as install + quickstart + command table + config + docs index, and write the index | REQ-01, REQ-02, REQ-03, REQ-04, SC-01, SC-04 | pending |
| 04 | Repoint and audit | Repoint every inbound reference including prose mentions, and prove no substantive content was lost | REQ-06, REQ-08 | pending |

<!-- Phase 01 comes first deliberately: it is the guard that makes phases 02–04 safe.
     Once REQ-11 lands, the link check is part of the smoke command, so every later
     phase re-proves link integrity as a condition of its own verification.

     REQ-12 is RESOLVED (D-10, 2026-08-17): docs/ pages summarize and link to
     plugins/devflow/references/*.md as source of truth; normative detail is never
     restated. No marker remains open on this roadmap, so no phase carries a
     backstop truth for it.

     Phase 04 is last because a content-loss audit is only meaningful once both the
     destination pages and the trimmed README are final. -->
