---
id: TASK-213
title: >-
  resolve_audience returns only the final list, discarding the arithmetic it
  computed
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 14:20'
updated_date: '2026-10-06 18:42'
labels:
  - backend
dependencies: []
priority: p2
type: feature
ordinal: 200380
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **`resolve_audience` returns only the final list** (Q3), discarding the arithmetic it computed: included by rules, added by hand, removed by exclusions, dropped by consent. The numbers exist inside the function.

Source: [[Manager Workflow - design interview]] → What Cluster 4 produced, gap 13 (Q4.3).

**Verified against the code 2026-09-27:** `resolve_audience` (`backend/app/audience/service.py:514-516`) returns `list[RecipientDB]`; the include / exclude / pin / consent sets are local variables at `:563-590`.

Related: task-47 changes the precedence inside the same function ([[ADR-176 — A Negative Decision Outranks a Positive One]] point 1).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Background: Manager Workflow Q4.3 (the arithmetic: rules, by hand, exclusions, consent, total), Q4.4 (always per channel), Cluster 5 Q2 (as of now: the send recomputes). task-47 (ADR-176 precedence) is done.
2. Decision with the user (2026-10-06): people who match the rules but have not agreed to the channel are counted, never listed — only among people this brand has a consent record with.
3. Tests first: backend tests/test_audience_arithmetic.py (every term, adds up, equals the send's audience, per channel, the preview carries it); client AudienceDetail tests (the working's rows, the hand-added note only when non-zero, the as-of-now line).
4. audience/service.py: find_by_criteria(not_agreed=True) for the count; one _resolve behind resolve_audience and audience_arithmetic; preview_group returns the arithmetic. models/router: AudienceArithmetic on AudiencePreview.
5. AudienceDetail.tsx: the working as a table, the as-of-now line; the wrong 'Matched by the rules' label (it sat on the post-consent audience) replaced.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

Definitions chosen in building, so the terms add up exactly: matched_rules = rule matches among brand-known people (agreed or not); not_agreed = of them, not agreed to the channel (count only); added_by_hand = pins the rules did not already include; removed_by_exclusion = removed from (rules ∪ pins) by an exclude block, removed_hand_added = the pinned part of it; dropped_by_consent = what the consent floor drops after that (only hand-adds can be dropped there, since rule blocks already match only people who agreed); total = the audience. The arithmetic is computed only when asked for (the preview), so a send pays nothing extra. A preference-category criterion reads behavioural signals for the not-agreed count too; it stays a count.
Not in this task: the send review screen (C8, not built) — it will read the same arithmetic.
Validation: 4 backend tests + 2 client tests, failing first; 9 backend and 6 client mutants caught (one gap — every excluded person was also in the union — closed with an excluded-only person before mutating). Backend 1380, client 191, tsc, contract. Live, read-only on the dev groups: every working adds up and equals the audience a send resolves, on email and push (e.g. All demo recipients on push: 40 match, 25 not agreed, 15 in).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The audience screen now shows how its number is arrived at, per channel: match the rules, not agreed to the channel (a count only, among this brand's contacts), added by hand, removed by exclusion segments (and how many of those were hand-added), hand-added without agreement, in the audience — with "as of now: a send works this out again". One computation serves the audience and its arithmetic, so they cannot disagree. Verified by 6 tests, 15 caught mutants, both suites, the contract and a read of every dev group on both channels.
<!-- SECTION:FINAL_SUMMARY:END -->
