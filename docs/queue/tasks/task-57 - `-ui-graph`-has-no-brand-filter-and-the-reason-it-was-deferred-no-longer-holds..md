---
id: TASK-57
title: >-
  `/ui/graph` has no brand filter, and the reason it was deferred no longer
  holds.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 162, section "Features", position 10 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
