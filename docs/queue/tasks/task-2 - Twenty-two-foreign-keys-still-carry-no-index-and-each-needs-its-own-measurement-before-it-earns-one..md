---
id: TASK-2
title: >-
  Twenty-two foreign keys still carry no index, and each needs its own
  measurement before it earns one.
status: To Do
assignee: []
created_date: '2026-09-27 13:46'
labels:
  - backend
dependencies: []
priority: p3
type: chore
ordinal: 1011
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Chore] — P3, the tail of the item above.** **Twenty-two foreign keys still carry no index, and each needs its own measurement before it earns one.** The full list comes from asking `pg_index` which column each index leads on, not from grepping the models. Candidates worth measuring first, because they grow per recipient or per event: `engagement_events.delivery_execution_id`, `signal_contributions.event_id`, `decision_resolutions.recipient_id`, `content_category_assignments.category_id` (the decision strategies join through it). The rest are structural tables that stay small. **Do not batch-add them** — the measurement above found one candidate in four that a plausible rule would have indexed for nothing.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 58, section "Bugs", position 11 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
