---
id: TASK-163
title: >-
  No uniqueness check on `provider_event_id` at ingestion — a webhook delivered
  twice creates a second `EngagementEventDB` row unconditionally
  (`providers/service.py`).
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 502700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** No uniqueness check on `provider_event_id` at ingestion — a webhook delivered twice creates a second `EngagementEventDB` row unconditionally (`providers/service.py`). This is a different, earlier layer than the Insight Q3 dedup fix (which governs whether a *scoring* update applies, not whether the raw event itself gets recorded twice). Fix: add a uniqueness check/constraint on `provider_event_id` at ingestion. Source: [[Interview Prep - Delivery, Providers, Recipients]] → Providers Q5. **Done 2026-07-12** — `ingest_provider_event` now checks for an existing `(provider, provider_event_id)` row and returns it with `status="duplicate"` instead of inserting again; backed by a DB unique constraint (also applied to the generic `/insight/events` endpoint, now catching the `IntegrityError` as a 409). Verified live: second post of the same `provider_event_id` returned the original event, not a new row.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 555, section "Done", position 27 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
