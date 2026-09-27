---
id: TASK-160
title: >-
  `create_recipient` has no duplicate check before insert — a repeat CRM sync (a
  realistic, expected operational path) hits an unhandled `IntegrityError` on
  `external_id`'s unique constraint and return…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels: []
dependencies: []
type: bug
ordinal: 502400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `create_recipient` has no duplicate check before insert — a repeat CRM sync (a realistic, expected operational path) hits an unhandled `IntegrityError` on `external_id`'s unique constraint and returns a raw 500 instead of a clean upsert. Fix: upsert keyed on `external_id` (update if exists, insert if not) instead of blind insert. Source: [[Interview Prep - Delivery, Providers, Recipients]] → Recipients Q5. **Done 2026-07-12.** Verified live: re-posting the same `external_id` updates the existing row in place instead of erroring.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 549, section "Done", position 24 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
