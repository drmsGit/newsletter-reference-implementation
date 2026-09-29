---
id: TASK-11
title: >-
  Twenty-two foreign keys still carry no index, and each needs its own
  measurement before it earns one.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-09-29 18:30'
labels:
  - backend
dependencies: []
priority: p3
type: chore
ordinal: 101100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Chore] — P3, the tail of the item above.** **Twenty-two foreign keys still carry no index, and each needs its own measurement before it earns one.** The full list comes from asking `pg_index` which column each index leads on, not from grepping the models. Candidates worth measuring first, because they grow per recipient or per event: `engagement_events.delivery_execution_id`, `signal_contributions.event_id`, `decision_resolutions.recipient_id`, `content_category_assignments.category_id` (the decision strategies join through it). The rest are structural tables that stay small. **Do not batch-add them** — the measurement above found one candidate in four that a plausible rule would have indexed for nothing.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 58, section "Bugs", position 11 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Measured the four growth candidates against synthetic volume (100k rows) in a rolled-back test-DB transaction, each with its real query. Indexed two via migrate_0023 and the models: engagement_events.delivery_execution_id (2.235 -> 0.005 ms) and a composite decision_resolutions(decision_slot_id, recipient_id) (renderer 0.184 -> 0.005 ms; attribution 0.536 -> 0.006 ms) — the composite, not recipient_id alone, because the slot index made each per-recipient lookup walk the whole slot. Refused two with numbers: signal_contributions.event_id (38 µs, already bounded) and content_category_assignments.category_id (0.17 ms, buffers unchanged; its multiplier is task-234). Remaining unindexed FKs are small structural tables, not measured. Tests pin exact column lists and the refusals; three mutations caught; applied to dev via the runner; 720 tests pass.
<!-- SECTION:FINAL_SUMMARY:END -->
