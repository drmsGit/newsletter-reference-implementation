---
id: TASK-114
title: >-
  `outcome_delta` can be recorded and cannot be computed — and a "delta"
  presupposes a comparison nothing specifies.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 206700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — the trust loop is half-built, and the missing half is not code. Found 2026-09-26, [[Variant Editor - design interview]] question 3.9.** **`outcome_delta` can be recorded and cannot be computed — and a "delta" presupposes a comparison nothing specifies.** `record_outcome_delta` (`backend/app/overrides/service.py:221`) exists with a route, a merge and concurrency handling, and **only the router calls it**: nothing in the insight or engagement layer produces a value. That is the shallow gap. **The deeper one is that measuring whether an override performed better needs a baseline — the unoverridden version, which by definition was not sent.** It requires a holdout group, a counterfactual, or an A/B between overridden and unoverridden content, and **none of the three exists or is designed**. So the column is further from meaningful than a missing producer suggests. **Why it matters beyond curiosity:** question 1.8 made override frequency a **maturity signal** — the rate should fall as automation earns trust — and that is the first reason in the repository for this column to exist at all. A falling rate says progress is happening; `outcome_delta` would say whether the overrides that remain are good ones. **Already decided:** none of this appears in the composer (question 3.9 — *"it must stay a focused tool"*), it belongs on the override history screen, and when the comparison is built it gets its own monitoring screen. **Do not build the producer before the experimental design** — a number with no baseline is worse than no number, because people act on it.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 402, section "Features", position 67 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
