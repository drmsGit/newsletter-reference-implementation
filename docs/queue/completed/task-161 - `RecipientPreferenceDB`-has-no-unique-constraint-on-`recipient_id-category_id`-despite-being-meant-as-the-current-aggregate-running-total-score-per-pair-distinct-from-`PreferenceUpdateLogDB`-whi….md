---
id: TASK-161
title: >-
  `RecipientPreferenceDB` has no unique constraint on `(recipient_id,
  category_id)` despite being meant as the current/aggregate running-total score
  per pair (distinct from `PreferenceUpdateLogDB`, whi…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 502500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `RecipientPreferenceDB` has no unique constraint on `(recipient_id, category_id)` despite being meant as the current/aggregate running-total score per pair (distinct from `PreferenceUpdateLogDB`, which is the correct append-only historical log and needs no such constraint). `create_recipient_preference` always inserts rather than upserting, so duplicate "current score" rows can silently appear, and `apply_event_to_preferences`'s `.first()` picks one non-deterministically, leaving the other permanently stale. Fix: add a unique constraint on `(recipient_id, category_id)` and change creation to upsert (insert if missing, update in place if it exists). Source: [[Interview Prep - Delivery, Providers, Recipients]] → Recipients Q3. **Done 2026-07-12.** Verified live: posting twice for the same pair updates the same row (same id) rather than creating a second.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 551, section "Done", position 25 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
