---
id: TASK-359
title: 'Content subpages: categories and the category graph with content KPIs'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-11 10:01'
updated_date: '2026-10-16 15:39'
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
- [x] #1 Categories and the graph are subpages of Content in the React client
- [x] #2 The graph shows per-category and per-content figures for the working brand
- [x] #3 The KPI scope is decided against task-58 before it is built
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final design (2026-10-16), with the user one question at a time:
- KPI scope (AC 3, against task-58/ADR-196): the campaign results' definitions, per content record, all time, computed on read, counted per delivery: deliveries that carried it (sent executions whose frame held it as a content module or whose recorded picks hold it), of which by a slot pick; clicks on its links (total) and unique clickers (deliveries with a click on it); click share = its clicks / all clicks in the deliveries that carried it (the user: share of clicks, not clicks over deliveries, which would read very low). No opens (ADR-196). Overall and per campaign.
- Shown on the record's page (Performance: overall and per campaign) and as columns wherever a category lists its records (category detail, the graph's side panel). The graph shows per-category totals.
- Graph drawn as plain SVG, no library (ADR-173): the Jinja layout moved to the client (main categories inner circle, the rest outside; size by picks and signal; relation and shared-record edges), a click opens the category's panel, and a table of the same figures beside it for keyboard and screen reader.
- Categories subpage: everything Jinja has (create main/sub, delete asking first when assignments or relations go with it, add/remove parent-child relations) plus rename and change type through a new PATCH /content/categories/{id}. Assigning content stays on the record page. Categories are global (no brand column): rename and delete reach every brand, as delete already does under content.manage; kept, noted. Category create/rename/delete and relation writes get audited.

Slices: A backend KPIs (app/content/kpis.py), GET /content/{id}/performance, KPIs on GET /insight/categories/{id} assigned_content, record page Performance section. B Content subnav (Records, Categories, Graph) and the Categories list/detail with PATCH and audits. C the Graph screen. ADR-196 addendum (click share) by adr-author. Tests, mutation checks, live check on scratch data.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-11, from task-58's design pass (ADR-196 point 5): per-link and per-content click figures live on the content catalogue side, not in the campaign's results section. The user: links and content KPIs will be displayed on the content catalogue side. Clicks name their content only through event_data.content_record_id (tracked links).

2026-10-11, the user set the November 2026 presentations as the focus (docs/business/PRESENTATIONS-2026-11.md): the category graph is on the demo list.

Built 2026-10-16 in three slices; CI green on 41a6743 (A) and 05a2632 (B and C; B's own run was cancelled by the next push). Codex's three task-365 tests came in first (0e61c5a).

Decided with the user, one at a time: figures per record on the campaign results' definitions, but the rate is a share of clicks (its clicks over all clicks in the deliveries that carried it), not clicks over deliveries, which reads very low; shown on the record page and wherever a category lists its records, the graph showing category totals; the graph drawn in plain SVG with a table beside it; the Categories subpage does everything Jinja did plus rename and type change. Recorded in the ADR-196 addendum of 2026-10-16.

A (41a6743): app/content/kpis.py content_figures, counted per delivery, all time, on read; GET /content/{id}/performance (overall and per campaign); figures on GET /insight/categories/{id} assigned records; a Performance section on the record page. What a delivery carried is one function now (carried_content in app/delivery/service.py), shared with click attribution. Two test gaps found by mutation (another brand's deliveries; non-click events) were closed.
B (26e5b9e): Content subnav (Records, Categories, Graph); Categories list and detail; PATCH /content/categories/{id}; every category write audited (category.created, .changed, .deleted, .relation_added, .relation_removed); a type is main or sub. Choice now shows an English placeholder ("Choose…") instead of React Aria's browser-language default ("Element wählen"), app-wide.
C (05a2632): Content > Graph, the Jinja layout in the client, nodes are keyboard buttons that say their figures and trend in words, a side panel with the category's records and figures, a table of the same figures.

Facts worth knowing: categories are global (ADR-150), so rename and delete reach every brand, under content.manage as delete already was; the pages say so. Deliveries from before delivery records carry no record of what they held and so count for no record. The figures read every sent delivery of the brand on each call: fine here, to be stored at scale. Dev data's 141 clicks name no record (older demo events), so shares there read 0 % until tracked clicks exist. docs/react-screen-inventory.md:63 still lists gaps C5 and C10, which have been closed since 2026-10-02.

Verification: pytest 2084, vitest 333, tsc, build, eslint (no errors), Ruff; mutations: A six, B six, C four, all caught; live check: record 101's Performance (32 deliveries, 0 % of 141 clicks), a scratch category created, renamed and deleted, the graph drawn from demo data with Beach's panel.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Content has Records, Categories and Graph as subpages. A record shows its figures (deliveries, clicks, unique clickers and its share of the clicks in the emails that carried it, overall and per campaign) on its page and in every category list; categories are created, renamed, linked and deleted with every write audited; the graph is drawn in plain SVG with a keyboard-usable side panel and table. KPI scope decided with the user against ADR-196 (addendum 2026-10-16). Verified by pytest 2084, vitest 333, mutation checks, a live check and CI.
<!-- SECTION:FINAL_SUMMARY:END -->
