---
id: TASK-150
title: >-
  `assign_category_to_content` (`content/service.py:241-257`) has no duplicate
  check, unlike `audience`'s `add_member` — the same content/category pair can
  be assigned more than once, creating duplicat…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 501400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `assign_category_to_content` (`content/service.py:241-257`) has no duplicate check, unlike `audience`'s `add_member` — the same content/category pair can be assigned more than once, creating duplicate rows and duplicate entries in `list_categories_for_content` output. Fix: reject (or upsert) on duplicate `(content_id, category_id)` pairs — no duplicates allowed. Cosmetic/data-hygiene only (no correctness risk beyond a repeated list item), lowest priority of the bugs logged so far. Source: [[Interview Prep - Content, Campaigns, Audience]] → Content Q7. **Done 2026-07-12** — rejects with a 409 rather than upserting.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 529, section "Done", position 14 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
