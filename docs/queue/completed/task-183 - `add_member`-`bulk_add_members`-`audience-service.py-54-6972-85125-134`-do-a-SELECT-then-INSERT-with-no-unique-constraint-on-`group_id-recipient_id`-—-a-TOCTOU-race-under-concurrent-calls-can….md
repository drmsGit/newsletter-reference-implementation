---
id: TASK-183
title: >-
  `add_member`/`bulk_add_members` (`audience/service.py:54-69,72-85,125-134`) do
  a SELECT-then-INSERT with no unique constraint on `(group_id, recipient_id)` —
  a TOCTOU race under concurrent calls can…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 504700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `add_member`/`bulk_add_members` (`audience/service.py:54-69,72-85,125-134`) do a SELECT-then-INSERT with no unique constraint on `(group_id, recipient_id)` — a TOCTOU race under concurrent calls can produce duplicate membership rows. Fix: add a DB-level unique constraint on `(group_id, recipient_id)` on `AudienceGroupMemberDB`, making it safe-by-construction instead of relying on the application-level existence check. Source: [[Interview Prep - Content, Campaigns, Audience]] → Audience Q3. **Done 2026-07-12** — constraint added; both `add_member` and `bulk_add_members` now catch the race (falling back to per-row commits in the bulk case so one conflicting row doesn't lose the rest of a legitimate batch) instead of surfacing a raw 500. Verified live: adding the same member twice is idempotent, no duplicate row.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 595, section "Done", position 47 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
