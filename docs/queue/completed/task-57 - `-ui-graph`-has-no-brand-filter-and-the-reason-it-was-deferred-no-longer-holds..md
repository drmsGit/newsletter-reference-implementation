---
id: TASK-57
title: >-
  `/ui/graph` has no brand filter, and the reason it was deferred no longer
  holds.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-10-02 12:54'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 201000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — the blocker it was parked behind has cleared.** **`/ui/graph` has no brand filter, and the reason it was deferred no longer holds.** `frontend/router.py:3071-3140` filters by no brand at all. [[ADR-150 — Tenancy and Access Model]]'s addendum (`:200-202`) deliberately parked it rather than half-shipping it: the content count and selection count are brand-scopeable via `content_records`, the signal-impact figure is not, and scoping two of three *"would put two different populations side by side on one page."* **Brand step 2 (consent) shipped 2026-09-15**, so the stated blocker is gone and the work was never picked up. Note the third figure is still not brand-scopeable by a column — the later addendum (`:192-198`) argues signal contributions need none, because *"what is scoped is which people are summed, and that is a query, not a column"* — so this is a decision about whether that argument is enough to scope all three consistently, not just an added `WHERE`. Related: the per-brand affinity question ADR-150 `:188` leaves open for *"whoever picks it up"*. Source: `/interview-prep-baseline` 2026-09-18.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every figure on /ui/graph (content, selections, node impact, co-occurrence, edge impact) is scoped to the working brand
- [x] #2 The audience is latest marketing consent opted in on any registered channel
- [x] #3 Each scoping filter has a test that fails without it
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Verify the entry: ADR-150's 2026-09-15 addendum already resolved the filter (scope which people are summed); consent carries a brand since 2026-09-15, so the blocker had cleared. 2. Ask the open detail: which consent cell defines the audience. 3. Move the figures to insight.graph, scope all of them together, keep layout in the route. 4. Tests per scoping filter, mutation-checked. 5. ADR-150 addendum via adr-author.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 162, section "Features", position 10 in that section (top = do next). The description is the original entry, verbatim.

2026-10-02: entry was half-stale — the 'decision' it asked for was already taken by ADR-150's 2026-09-15 addendum; only the audience definition was open. User chose 'marketing consent on any channel'. Built in backend/app/insight/graph.py (category_graph, brand_audience); /ui/graph lays out only. tests/test_category_graph.py: 5 tests, six mutants caught (node impact, selections, content counts, email-only audience, edge impact, co-occurrence). ADR-150 addendum 2026-10-02 (adr-author; diff additions only). Suite 855 passed. Not done: no JSON route for the graph (thin now).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The category graph is the working brand's in every figure at once, per ADR-150: content and co-occurrence count the brand's content, selections count resolutions of it, signal impact on nodes and edges sums the brand's audience (latest marketing consent opted in on any channel). The computation moved to insight.graph.category_graph; the Jinja route only lays it out. Verified by tests/test_category_graph.py with each scoping filter mutation-checked; full suite 855 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
