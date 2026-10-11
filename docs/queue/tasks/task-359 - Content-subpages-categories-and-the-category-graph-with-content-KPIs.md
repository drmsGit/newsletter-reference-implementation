---
id: TASK-359
title: 'Content subpages: categories and the category graph with content KPIs'
status: To Do
assignee: []
created_date: '2026-10-11 10:01'
updated_date: '2026-10-11 20:44'
labels:
  - frontend
  - backend
dependencies: []
type: feature
ordinal: 200500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Raised by the user on 2026-10-11: the category list and the category graph exist only in the old Jinja UI. In the React client they belong under Content (subpages, not menu areas, by the same rule as Settings' parts). The user added: the graph is where the **detail** lives, on categories and on content KPIs; the monitoring screen gives the first-glance overview (task-360).

**What exists today.**
- Categories: /ui/categories and /ui/categories/{id} (backend/app/frontend/router.py:2429, :2478). JSON exists: GET /content/categories, /content/categories/{id}/children and /parents, /content/category-relations (listed in MACHINE_READS, backend/app/auth/policy.py). Known API gaps from docs/react-screen-inventory.md: unassign is gap C5, deleting a relation is gap C10.
- Graph: /ui/graph (backend/app/frontend/router.py:2921) lays out figures from GET /insight/category-graph (backend/app/insight/router.py:82), which is scoped to the working brand all together (ADR-150's 2026-10-02 addendum). Layout is the client's.

**What it needs.**
1. Content subpages: Categories (list, detail with parents, children and assigned content) and Graph.
2. The graph screen as the detail view: per category its content, resolutions and signal impact, and per content record its KPIs. Which KPIs, and from where, is the design question: task-58 limits reporting to an export boundary plus one small KPI view, so the scope of "content KPIs" has to be decided against it before building.
3. A final-design pass, including whether the graph is drawn (a library, ADR-173's dependency rules) or shown as tables first.

**Related.** task-58 (reporting scope), task-360 (monitoring overview), task-95 and task-86 (taxonomy and signals), ADR-175 (facets later).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Categories and the graph are subpages of Content in the React client
- [ ] #2 The graph shows per-category and per-content figures for the working brand
- [ ] #3 The KPI scope is decided against task-58 before it is built
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-11, from task-58's design pass (ADR-196 point 5): per-link and per-content click figures live on the content catalogue side, not in the campaign's results section. The user: links and content KPIs will be displayed on the content catalogue side. Clicks name their content only through event_data.content_record_id (tracked links).

2026-10-11, the user set the November 2026 presentations as the focus (docs/business/PRESENTATIONS-2026-11.md): the category graph is on the demo list.
<!-- SECTION:NOTES:END -->
