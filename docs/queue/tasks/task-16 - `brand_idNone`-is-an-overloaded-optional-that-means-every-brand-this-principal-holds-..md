---
id: TASK-16
title: >-
  `brand_id=None` is an overloaded optional that means "every brand this
  principal holds".
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 101600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P2, the same defect shape as the brand-filter item above, and worth fixing in one pass with it.** **`brand_id=None` is an overloaded optional that means "every brand this principal holds".** `permissions_for` (`auth/service.py:819-866`) answers the union when given no brand, so the safe reading and the dangerous one are the same call with one argument missing. `_permitted` (`auth/dependencies.py`) already refuses a brand-scoped permission outright when the request has no working brand — correct, tested, and a guard against an argument shape that should not be expressible in the first place. Passing it through would let an Admin on brand A act as one on brand B. **Fix:** a typed scope (`AllBrands` vs `Brand(id)`) so the union is something a caller names rather than something they get by forgetting. The union across roles itself needs no change: it falls out of grants-only, and with no DENY two roles cannot contradict each other. Source: [[Interview Prep - Auth, Permissions, Machine Principals]] → Q2.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 68, section "Bugs", position 16 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
