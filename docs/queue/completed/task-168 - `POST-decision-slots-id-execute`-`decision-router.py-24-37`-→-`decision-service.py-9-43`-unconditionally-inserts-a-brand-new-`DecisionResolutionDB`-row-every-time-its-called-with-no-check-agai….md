---
id: TASK-168
title: >-
  `POST /decision/slots/{id}/execute` (`decision/router.py:24-37` →
  `decision/service.py:9-43`) unconditionally inserts a brand-new
  `DecisionResolutionDB` row every time it's called, with no check agai…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 503200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `POST /decision/slots/{id}/execute` (`decision/router.py:24-37` → `decision/service.py:9-43`) unconditionally inserts a brand-new `DecisionResolutionDB` row every time it's called, with no check against the recipient's last resolution for that slot — confirmed to already happen in practice (re-running for a recurring journey creates another row even when nothing changed). Two fixes, prioritized data-minimization first: (1) non-personalized strategies (`top_score`, `requires_recipient=False`) should only ever have **one** resolution row per slot (`recipient_id=NULL`, already supported by the schema and rendering's read path) — never a duplicate per recipient; (2) personalized strategies (`recipient_top_score`) should only write a new row when something that could change the outcome actually changed since the recipient's last resolution (preference update, candidate content change) — "no new signal, keep the last recommendation" — rather than accumulating an unbounded, ever-growing number of per-person records over time. Storing as little per-recipient data as possible matters more here than the query-performance win, though both improve together. Source: [[Interview Prep - Decision, Overrides, Insight]] → Decision Q5. **Done 2026-07-12** — non-personalized strategies now always update the single existing `recipient_id=NULL` row in place; personalized strategies compare the freshly computed result against the recipient's last resolution and only insert a new row when content/version/score actually differ. Verified live both ways: a non-personalized slot run twice stayed at one row; a personalized slot re-run with nothing changed returned the same resolution id instead of creating a new one.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 565, section "Done", position 32 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
