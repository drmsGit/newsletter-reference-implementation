---
id: TASK-184
title: >-
  `AudienceGroupDB.name` uniqueness is case-sensitive and unhandled —
  "Newsletter VIPs" and "newsletter vips" succeed as two distinct groups, and a
  genuine duplicate name raises an unhandled 500 instea…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 504800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `AudienceGroupDB.name` uniqueness is case-sensitive and unhandled — "Newsletter VIPs" and "newsletter vips" succeed as two distinct groups, and a genuine duplicate name raises an unhandled 500 instead of a clean error (`router.py:16-18`, `service.py:15-33`). Fix: enforce case-insensitive uniqueness and catch `IntegrityError` to return a clean 409 with a clear message. Source: [[Interview Prep - Content, Campaigns, Audience]] → Audience Q5. **Done 2026-07-12** — replaced the plain case-sensitive `unique=True` with a functional unique index on `lower(name)`; both the API and UI now catch the conflict and return a clean 409 with an error banner instead of a 500. Verified live: `"newsletter vips"` correctly rejected as a duplicate of `"Newsletter VIPs"`.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 597, section "Done", position 48 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
