---
id: TASK-175
title: >-
  `recipient_id` means two different things across modules —
  `recipients`/`decision`/`insight` use the internal integer PK, while
  `delivery`/`providers` (`DeliveryExecutionDB.recipient_id`) use the str…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 503900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `recipient_id` means two different things across modules — `recipients`/`decision`/`insight` use the internal integer PK, while `delivery`/`providers` (`DeliveryExecutionDB.recipient_id`) use the string `external_id`, with no FK between them. This forces indirect lookups (e.g. `insight/service.py:105-118` has to query `RecipientDB WHERE external_id = ...` just to translate a delivery execution's recipient into something joinable), and each such lookup is an extra failure mode (mismatched/stale external_id → `ValueError`) that a real FK wouldn't have. Confirmed this doesn't add any new CRM integration burden — per [[ADR-126 — Maintain Local Recipient Projection]], delivery execution tracking already requires the local `RecipientDB` projection to exist and be synced regardless of which of its two ID columns gets referenced; switching to the internal PK is purely internal plumbing, not a new sync dependency. Fix: make `DeliveryExecutionDB.recipient_id` (and any other cross-module reference doing the same thing) a direct FK to `RecipientDB.id`, consistent with [[ADR-054 — Use Internal Recipient Identifiers]]. Good time to do this — data model is still cheap to reshape. Source: [[Interview Prep - Decision, Overrides, Insight]] → Insight Q5 (also flagged as a cross-cutting finding in [[MOC - Interview Prep Baseline]], affects the not-yet-reviewed Delivery/Recipients cluster too). **Done 2026-07-12** — `DeliveryExecutionDB.recipient_id` is now a real FK to `RecipientDB.id`. `apply_event_to_preferences` no longer does an external_id lookup at all (deleted ~15 lines, uses the FK value directly); `send_send_instance` likewise. Since the provider layer still needs an address, `DeliveryProvider.send()`'s param was renamed `recipient_id` → `recipient_email` and now receives the recipient's actual email. Verified live end-to-end: created an execution via the API with an internal id, a bad id was rejected with a clean 400 (FK violation), a full personalized send completed, and `apply_event_to_preferences` correctly resolved the recipient with no translation step.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 579, section "Done", position 39 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
