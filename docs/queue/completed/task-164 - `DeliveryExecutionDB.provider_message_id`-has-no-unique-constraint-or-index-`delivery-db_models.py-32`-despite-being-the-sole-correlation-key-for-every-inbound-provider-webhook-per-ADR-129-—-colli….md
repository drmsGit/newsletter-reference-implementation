---
id: TASK-164
title: >-
  `DeliveryExecutionDB.provider_message_id` has no unique constraint or index
  (`delivery/db_models.py:32`), despite being the sole correlation key for every
  inbound provider webhook per ADR-129 — colli…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 502800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `DeliveryExecutionDB.provider_message_id` has no unique constraint or index (`delivery/db_models.py:32`), despite being the sole correlation key for every inbound provider webhook per ADR-129 — collisions would silently pick the wrong execution, and the lookup (the hot path for all inbound events) degrades linearly with volume. Fix: add a unique constraint + index. Source: [[Interview Prep - Delivery, Providers, Recipients]] → Providers Q3. **Done 2026-07-12.**
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 557, section "Done", position 28 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
