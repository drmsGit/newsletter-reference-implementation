---
id: TASK-384
title: Bring in Codex's ranked Column delivery test
status: Done
assignee:
  - '@claude'
created_date: '2026-10-16 11:31'
updated_date: '2026-10-16 13:00'
labels:
  - backend
dependencies: []
type: chore
ordinal: 200350
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Bring in Codex's regression test for the MJML block set (task-371): `backend/tests/test_column_slot_delivery.py`, tests-branch commit ef0e62e on `origin/codex/regression-tests`, pre-stage note doc-23 (source bc3a3e9).

It sends a variant whose Column module is filled by a decision slot showing three picks, and checks that the email holds one pair and a lone Column (ADR-198 point 4), that each link credits its own record (ADR-182), and that the sent email rebuilds byte for byte after later edits to hidden fields and to the slot's "show up to" (ADR-183, ADR-084).

Read and run against main on 2026-10-16: it passes, so it can land on its own (CLAUDE.md: only a test exposing an open bug must wait for its fix). It imports fixtures from `tests/test_several_picks.py` and `_sections` from `tests/test_block_set.py`; keep those names stable or adjust the import.

Handling note from the user (2026-10-16), for the demo and the how-to rather than for code: in Two columns, a slot on one Column is best set to show up to 1, so the other Column can hold a fixed record; a slot showing three repeats the Column three times (a pair and a lone one).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 test_column_slot_delivery.py is on main and the suite passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Brought in 2026-10-16 (commit 5c1a52a), unchanged from tests-branch commit ef0e62e (identical to the version read on 2026-10-16). Passes on main; Ruff clean. Two mutations caught: Columns never paired; the right side crediting the left record. pytest 1991 passed; CI green on 5c1a52a.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Codex's ranked Column delivery test is on main, unchanged; it passes and catches unpaired Columns and wrong-side attribution. pytest 1991, CI green on 5c1a52a.
<!-- SECTION:FINAL_SUMMARY:END -->
