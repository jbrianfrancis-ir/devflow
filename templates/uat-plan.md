<!-- .planning/deploy/UAT-PLAN.md — cap 4KB. Regenerated per UAT round; git keeps history. -->
---
round: 1
sha: {git SHA deployed}
date: {YYYY-MM-DD}
env: uat
urls: []
result: pending             # pending | passed | failed
---
# UAT Plan — round {N}

## Smoke
- [ ] health endpoints respond ({url}/health, /alive)
- [ ] can authenticate (if applicable)
- [ ] critical path works: {one-line flow}

## Route sweep (web UIs — omit section otherwise)
| Route | Loads | Console clean | Requests clean | Notes |
|-------|-------|---------------|----------------|-------|
| / | | | |
<!-- One row per key route from the app's routing. Filled by the automated sweep; a console error or failed request is a failure even when the page "looks fine". -->

## Acceptance — one case per requirement
### REQ-01: {requirement one-liner}
Steps: 1. {step} 2. {step}
Expect: {observable result}
Result: [ ] pass [ ] fail — notes:
