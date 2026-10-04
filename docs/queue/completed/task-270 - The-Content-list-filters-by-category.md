---
id: TASK-270
title: The Content list filters by category
status: Done
assignee:
  - '@claude'
created_date: '2026-10-04 10:21'
updated_date: '2026-10-04 11:10'
labels:
  - frontend
dependencies:
  - TASK-268
type: feature
ordinal: 200070
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-263 design session (2026-10-04, user, decision 8): the Content list gets the same category filter as the bind picker. It is a small task of its own, built alongside task-267's content-screen work rather than inside the picker task. The filter lives on the server (task-268), so here it costs a dropdown, and "find by topic" then works the same in the picker and on the Content screen.

Today the Content list (`frontend/src/screens/Content.tsx`) has a `SearchBox` labelled "Find content by title" and a Status `Choice` (Any, Active, Inactive). Both are held in the URL (`Content.tsx:31-47`). There is no category filter, no category column and no sort control. After task-268, `q` matches title and description (decision 3), so the search label changes to say so.

Same rules as the picker:
- the category is read-only and one at a time;
- the hierarchy is shown indented;
- direct assignment only, with no child expansion (decision 4);
- with a category chosen, score order, then newest (decision 5).

The ADR-175 addendum of 2026-10-04 records why categories are the topic axis until facets (task-207) exist. When facets land, they join this screen as further filters, and ADR-175 point 7 owes them here.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The Content list has a category filter, held in the URL like the status filter, that narrows rows and total to records directly in that category
- [x] #2 The search is labelled as finding by title or description
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. useContentList(offset, q, status, categoryId?) sends category_id.
2. Content.tsx: CategoryChoice beside the status filter, held in the URL as ?category=<id>. Choosing one resets offset. The search label becomes "Find content by title or description".
3. Tests in ListFilters.test.tsx: a category from the URL is sent; choosing one sends it and starts from page 1; "Any category" removes it. Mutation-check each.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-04.
- useContentList takes an optional categoryId. Content.tsx reuses CategoryChoice (task-269), held in the URL as ?category=<id>. Status and category share one setFilter, which resets offset. The search is labelled "Find content by title or description".
- In passing: with a filter set, an empty list said "No content in this brand yet." It now says "No content matches these filters."; the old text stays when nothing is filtered.
- Tests: 4 new in ListFilters.test.tsx, and the existing ones stub the category routes. Mutation-checked against 6 mutants, each caught: category not sent, URL not read, offset kept, "Any category" ignored, old label, empty message unconditional. Client: tsc -b clean, vitest 140 passed.
- Checked live on the dev server: ?category=8 (Wellness) lists Wellness-tagged records in fit order.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The Content list filters by one category, held in the URL beside status, narrowing rows and total to directly assigned records in fit order. Its search now says it finds by title or description, and an empty filtered list no longer claims the brand has no content. Verified by 4 new tests mutation-checked against 6 mutants, the full client suite (140) and typecheck, and a live check on the dev server.
<!-- SECTION:FINAL_SUMMARY:END -->
