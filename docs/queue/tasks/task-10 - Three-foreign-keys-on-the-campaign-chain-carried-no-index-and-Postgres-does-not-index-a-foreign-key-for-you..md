---
id: TASK-10
title: >-
  Three foreign keys on the campaign chain carried no index, and Postgres does
  not index a foreign key for you.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 101000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — P2, measured rather than suspected. DONE 2026-09-20 (migration 0018).** **Three foreign keys on the campaign chain carried no index, and Postgres does not index a foreign key for you.** Measured individually against synthetic volume in the test database, each as one query before and after:
  - `decision_resolutions.decision_slot_id` — 3.45 ms / 801 buffers → **0.080 ms / 12** (36×), at 96,040 rows. The one that matters: this table grows at one row per recipient per slot.
  - `variants.campaign_id` — 1.335 ms / 617 → **0.016 ms / 3** (83×), at 60,004 rows.
  - `decision_slots.variant_id` — 1.554 ms / 849 → **0.014 ms / 3** (111×).

  **A fourth candidate was measured and deliberately not indexed.** `delivery_executions.send_instance_id` came out at 1.511 ms before and 1.439 ms after with identical buffers — a send instance owns most of that table's rows, so the lookup is unselective and a sequential scan is the correct plan. **Selectivity decides this, not foreign-key-ness**, and indexing every FK on principle would have added a useless index here. Worth remembering before the remaining twenty-two are touched.

  Two more that look unindexed in the models and are not: `module_instances.variant_id` and `content_versions.content_record_id` are each the leading column of a composite unique constraint, which is a usable index. **Reading `index=True` off the model is the wrong measurement** — ask the database which column each index leads on.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 49, section "Bugs", position 10 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
