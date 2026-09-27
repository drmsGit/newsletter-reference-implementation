---
id: TASK-157
title: >-
  `RecipientDB.preferred_airport` is a domain-specific example (the airline use
  case) hardcoded as a first-class column in the generalized reference schema —
  wrong for a reference architecture meant to…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 502100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `RecipientDB.preferred_airport` is a domain-specific example (the airline use case) hardcoded as a first-class column in the generalized reference schema — wrong for a reference architecture meant to be reused across any industry. The data itself can stay airline-related as a living example, but the schema shouldn't hardcode it. Fix: remove `preferred_airport` (and any other column tied to one specific use case) and represent business-specific fields through a generalized key/value or JSON structure instead (a "preferences" JSON, or extend `attributes`) — same direction as the `attributes` scoping fix below. `language` stays as-is (a genuinely universal field, not domain-specific). Source: [[Interview Prep - Delivery, Providers, Recipients]] → Recipients Q6 (addendum, flagged for follow-up — don't forget). **Done 2026-07-12** — column dropped; the airline example now lives at `attributes.preferred_airport` in seed data. Recipients list/detail UI updated to render `attributes` generically instead of the hardcoded column.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 543, section "Done", position 21 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
