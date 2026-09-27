---
id: TASK-172
title: >-
  Two competing category hierarchy mechanisms exist:
  `CategoryDB.parent_category_id` (leftover from an earlier, wrong
  implementation) and `CategoryRelationDB`
  (parent_category_id/child_category_id/rela…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 503600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** Two competing category hierarchy mechanisms exist: `CategoryDB.parent_category_id` (leftover from an earlier, wrong implementation) and `CategoryRelationDB` (parent_category_id/child_category_id/relation_type edge table, already what the graph view at `frontend/router.py:1608-1621` actually uses). Fix: drop `CategoryDB.parent_category_id` entirely and consolidate on `CategoryRelationDB` as the single mechanism. Deliberately keep it fully flexible, no new restrictions: a child may have multiple parent relations, and parent-level (main) categories may relate to each other or to children freely — needed for real-world multi-parent taxonomies and for AI-discovered relations later, and adding artificial constraints now isn't necessary. Do add a cycle guard (reject a relation that would create a direct or transitive parent_child loop, e.g. A→B and B→A) since that's a genuine logical contradiction, not a business-flexibility case. Source: [[Interview Prep - Content, Campaigns, Audience]] → Content Q5. **Done 2026-07-12** — column dropped (it was already null on every existing row); a BFS cycle guard rejects any relation that would close a direct or transitive parent_child loop, including simple reversal and self-loops, while still allowing legitimate multi-parent taxonomies. Verified live: reversing an existing edge rejected, a self-loop rejected, a genuine new multi-parent relation accepted. Bonus: while verifying, found and fixed a real, separate pre-existing bug — `GET /content/categories` and `GET /content/category-relations` were completely unreachable (always 422) because `GET /{content_id}` was registered first and swallowed both fixed paths; reordered route registration to fix.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 573, section "Done", position 36 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
