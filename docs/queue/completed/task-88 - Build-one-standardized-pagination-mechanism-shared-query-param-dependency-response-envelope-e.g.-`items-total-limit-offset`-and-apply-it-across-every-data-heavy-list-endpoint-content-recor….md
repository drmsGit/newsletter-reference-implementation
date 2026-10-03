---
id: TASK-88
title: >-
  Build one standardized pagination mechanism (shared query-param dependency +
  response envelope, e.g. `{items, total, limit, offset}`) and apply it across
  every data-heavy list endpoint: content recor…
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 13:57'
updated_date: '2026-10-03 12:21'
labels:
  - backend
dependencies: []
type: feature
ordinal: 204100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** Build one standardized pagination mechanism (shared query-param dependency + response envelope, e.g. `{items, total, limit, offset}`) and apply it across every data-heavy list endpoint: content records, audience groups (`find_by_criteria`/`list_members`), content versions, decision slots/resolutions, engagement events, recipients. No pagination pattern exists today — only scattered hardcoded `.limit(20)`/`.limit(50)` calls in `frontend/router.py` with no offset/page param, no consistent shape. One offset/limit-based approach is sufficient for all of these at this project's realistic scale (none will hit true big-data volumes needing cursor/keyset pagination). Ranked reasonably high: even in the POC, presenting to people needs realistic test data volumes (recipients, events especially), and a positive UX matters in the POC too, not just "the real version." Supersedes the earlier "keep in poc" call on content-record pagination — folded in here. Source: [[Interview Prep - Content, Campaigns, Audience]] → Audience Q6 (supersedes Content Q3).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final-design pass 2026-10-03, implementing ADR-185 (decided by the user: envelope; lists that grow with use).
1. `backend/app/pagination.py`: PageParams dependency (limit 1-200 default 50, offset >= 0); generic Page[T] {items, total, limit, offset}; page_of_query(query, params, order) (count of the filtered query plus slice, id tie-breaker) and page_of_list(rows, params) for routes that assemble rows in Python (honest total, still computes all rows).
2. Commit A, the routes the React client reads, with the screens: approvals, deliveries (send-instances), campaigns, content, audience groups, campaign monitoring. Screens read .items; the approvals and deliveries pagers use total, which removes the 'empty last page' compromise.
3. Commit B, the lists that grow with no screen yet: recipients, a group's members, a slot's resolutions, a send's executions, an execution's events, overrides, provider quarantine, consent sync log, consent drift, decision slots. Backend and tests.
4. One guard test enumerating the paged routes from app.routes: each declares limit/offset and a Page response model, so a route cannot half-adopt.
Not here: filtering (ADR-185 point 6, Cluster 2 req 5). Fixed lists stay arrays (ADR-185 point 1).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 252, section "Features", position 41 in that section (top = do next). The description is the original entry, verbatim.

2026-09-27: [[Manager Workflow - design interview]] Cluster 2 requirement 5 widens this — server-side filtering as well as paging, on content, campaigns, audiences, recipients and approvals (campaigns and approvals are not named above). Cluster 3 gap 10: GET /campaigns/decision-slots/{id}/resolutions is the worst instance (backend/app/campaigns/router.py:286-296, .all() at backend/app/campaigns/service.py:809). The approvals list's other filters are task-209.

Step A built 2026-10-03: `backend/app/pagination.py` (page_params, Page[T], page_of_query, page_of_list). Six routes moved to the envelope, with their screens: approvals (filters and count share one _inbox_query), deliveries, campaigns, content (no timestamps on content_records, so newest first is id desc; an early created_at order 500'd and was caught only by an unrelated brand-boundary test, so every paged route now has its own envelope test), audience groups and monitoring (page_of_list). `backend/tests/test_pagination.py` classifies every GET list route (PAGED / FIXED / NOT_YET), so a new one must be decided under ADR-185 point 1. 5 backend mutants caught. Frontend: a shared Pager with the offset in the URL (`frontend/src/components/Pager.tsx`); Older is disabled exactly on the last page (checked in the browser: content, 105 records, 101-105 of 105). stubFetch now passes the request so a stub can echo the offset. 4 frontend mutants caught, after one survivor led to a single-page assertion. Backend and frontend suites green.

Step B built 2026-10-03: ten more routes on the envelope: recipients (a whole-page batch projection via page_of_query's new convert_all), a group's members, decision slots (page_of_list over its one grouped query), a slot's resolutions (the worst unbounded read, now paged in SQL), a send's executions (Delivery detail screen updated, with a Pager), an execution's events, overrides (filters shared by rows and total), provider quarantine, consent sync log, consent drift (page_of_list). FOUND AND FIXED: GET /insight/delivery-executions/{id}/events returned 500 on every call (the route passed brand_id to a service that never took one) and would have been unscoped; it's now brand-scoped through the execution's send, with a test (mutant: unscoped, caught). Brand-boundary tests now also assert total == 0 for another brand. NOT_YET in `backend/tests/test_pagination.py` is empty: every growing list is paged, every fixed list classified. Backend 1079, frontend 60; checked in the browser (Delivery detail, 32 recipients).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
ADR-185 implemented: one paging mechanism (`backend/app/pagination.py`) and one envelope {items, total, limit, offset} on all 16 list routes that grow with use, with the React screens and a shared URL-backed Pager. Older is disabled exactly on the last page. Fixed lists stay arrays, and a guard test classifies every list route. Also fixed: the events route had returned 500 on every call. Verified: guard plus per-route envelope tests, 11 mutants caught across both steps, both suites green, browser checks.
<!-- SECTION:FINAL_SUMMARY:END -->
