---
id: TASK-177
title: >-
  The dedupe key in `apply_event_to_preferences` — `(recipient_id, category_id,
  reason=event_type, delivery_execution_id)` — doesn't identify the specific
  event, so two distinct legitimate engagements…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 504100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** The dedupe key in `apply_event_to_preferences` — `(recipient_id, category_id, reason=event_type, delivery_execution_id)` — doesn't identify the specific event, so two distinct legitimate engagements (e.g. clicks on two different links, same email/category/execution) get conflated: the second is silently dropped as a "duplicate" and never scored (`recipients/service.py:137-150`). Every real event must still be saved (already true for the raw `EngagementEventDB` row) — deduplication should only decide *whether/how much score* a given event contributes, not whether the event itself is recorded. Fix: include something that uniquely identifies the specific engagement (e.g. `event_id`) in the dedupe key, so distinct events each get their own scoring decision while true duplicate deliveries of the *same* event still dedupe correctly. Source: [[Interview Prep - Decision, Overrides, Insight]] → Insight Q3. **Done 2026-07-12** — dedupe key is now `(recipient_id, category_id, event_id)`. Verified live: two distinct click events both scored independently (4 log entries, compounding correctly); re-applying the same event_id a second time was still correctly deduped (no-op).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 583, section "Done", position 41 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
