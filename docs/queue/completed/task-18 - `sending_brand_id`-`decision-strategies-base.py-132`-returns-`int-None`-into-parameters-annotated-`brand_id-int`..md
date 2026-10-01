---
id: TASK-18
title: >-
  `sending_brand_id` (`decision/strategies/base.py:132`) returns `int | None`
  into parameters annotated `brand_id: int`.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-10-01 19:37'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 101800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P2. Correct by accident, which is a property with an expiry date.** **`sending_brand_id` (`decision/strategies/base.py:132`) returns `int | None` into parameters annotated `brand_id: int`.** `top_score.py:53` and `recipient_top_score.py:91` build `.filter(ContentRecordDB.brand_id == sending_brand_id(db, slot))` and `decision/service.py:41` hands the same value to `require_consent`. It fails **closed**, but only because SQLAlchemy renders `== None` as `IS NULL`, the column is NOT NULL, nothing matches, and the consent check then finds no grant. Nothing checks anything. That holds until somebody changes a column's nullability or swaps a comparison — neither of which would look like it was touching brand safety. **Second cost, diagnostic:** a broken variant→campaign chain currently reads as "no suitable content" and graceful degradation under ADR-086 — the right response to a strategy that found nothing and the wrong one for a structural error. A `ConsentDenied` naming "brand None" is the tell. **Fix:** raise, matching the two call sites that touch the send record and already do. Source: [[Interview Prep - Brand Boundary]] → Q4.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 72, section "Bugs", position 18 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
sending_brand_id now returns int or raises BrokenCampaignChain, a RuntimeError — deliberately not a ValueError (the send loop would hide it as an empty slot under ADR-086) nor a ConsentDenied (what it used to surface as, naming brand None). It propagates and fails the send through task-14's handler; the decision route answers 409. The chain cannot break under today's schema (every link NOT NULL + FK), so tests build the broken case directly; four tests, no skips, three mutations caught; 744 pass.
<!-- SECTION:FINAL_SUMMARY:END -->
