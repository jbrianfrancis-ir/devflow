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

## Acceptance — one case per requirement
### REQ-01: {requirement one-liner}
Steps: 1. {step} 2. {step}
Expect: {observable result}
Result: [ ] pass [ ] fail — notes:
