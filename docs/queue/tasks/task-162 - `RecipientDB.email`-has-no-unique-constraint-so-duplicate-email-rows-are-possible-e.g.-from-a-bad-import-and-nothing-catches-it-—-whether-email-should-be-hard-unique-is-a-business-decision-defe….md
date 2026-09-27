---
id: TASK-162
title: >-
  `RecipientDB.email` has no unique constraint, so duplicate-email rows are
  possible (e.g. from a bad import) and nothing catches it — whether email
  *should* be hard-unique is a business decision (defe…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 502600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `RecipientDB.email` has no unique constraint, so duplicate-email rows are possible (e.g. from a bad import) and nothing catches it — whether email *should* be hard-unique is a business decision (deferred, likely part of the future config-layer work), not decided now. Regardless of that decision, small fix needed now: deduplicate by email before sending and when calculating audience segments/criteria, so duplicate-email recipients don't get double-emailed or get double-counted in segment previews. Source: [[Interview Prep - Delivery, Providers, Recipients]] → Recipients Q2. **Done 2026-07-12** — `find_by_criteria` (audience segment preview/criteria) now dedupes by email. The "before sending" half has no concrete implementation point yet — there's no bulk send-from-audience-group flow built at all today (delivery executions are only created one at a time via explicit API calls); revisit once that flow exists.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 553, section "Done", position 26 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
