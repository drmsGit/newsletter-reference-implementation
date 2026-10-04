---
id: TASK-270
title: The Content list filters by category
status: To Do
assignee: []
created_date: '2026-10-04 10:21'
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
- [ ] #1 The Content list has a category filter, held in the URL like the status filter, that narrows rows and total to records directly in that category
- [ ] #2 The search is labelled as finding by title or description
<!-- AC:END -->
