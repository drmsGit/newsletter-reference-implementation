---
id: TASK-180
title: >-
  `record_outcome_delta` (`overrides/service.py:32-39`) is a read-modify-write
  with no lock — concurrent PATCH calls computing outcome deltas for the same
  `override_id` (e.g. an open-rate job and a cli…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 504400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `record_outcome_delta` (`overrides/service.py:32-39`) is a read-modify-write with no lock — concurrent PATCH calls computing outcome deltas for the same `override_id` (e.g. an open-rate job and a click-rate job overlapping) have last-write-wins semantics, silently dropping whichever update committed first. Compounds the Q3 merge bug above. Fix mechanism not yet decided — either optimistic locking (a `version`/`updated_at` check-and-increment on write) or a DB-level row lock (`SELECT ... FOR UPDATE`); needs a decision before implementing. Source: [[Interview Prep - Decision, Overrides, Insight]] → Overrides Q4. **Done 2026-07-12** — went with `SELECT ... FOR UPDATE` (a row lock), for consistency with the Delivery Q5 double-send guard already using that pattern in this codebase, rather than introducing a second, different concurrency mechanism (optimistic locking) for a very similar problem.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 589, section "Done", position 44 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
