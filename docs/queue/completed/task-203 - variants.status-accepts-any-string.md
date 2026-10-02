---
id: TASK-203
title: variants.status accepts any string
status: Done
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-02 14:41'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 104800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** `variants.status` accepts any string. The interview settled its values: **`variants.status` is two values (4.6)** — `draft` and `ready`, constrained in code the way `CONTENT_STATUSES` is. `approved` belongs to the send, `sent` to send instances, `archived` to the data-lifecycle ADR. `ready` is question 4.7's assertion given a home, and it is the column the variant list reads instead of recomputing completeness.

| # | Gap | Where |
|---|---|---|
| 25 | `variants.status` accepts any string | `campaigns/service.py:191` |

Source: [[Variant Editor - design interview]] → What Cluster 4 produced, gap 25 (Q4.6).

**Verified against the code 2026-09-27:** the column is `String(50)` at `backend/app/campaigns/db_models.py:62`; the service takes `status: str = "draft"` at `backend/app/campaigns/service.py:191` (`create_campaign`) and `:269` (`create_variant_for_campaign`); the API models type it `str` at `backend/app/campaigns/models.py:19,29,41,53`; the router passes it straight through (`backend/app/campaigns/router.py:83,120`). No Literal or enum anywhere in `backend/app/campaigns/`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Creating a variant with a status other than draft or ready is refused, in the service and with 422 over JSON
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

2026-10-02: still true. VARIANT_STATUSES = (draft, ready) in campaigns/service.py, enforced in create_variant_for_campaign (the only writer; there is no status update path); VariantCreate.status is Literal. Read model and column untouched, no migration — existing rows (and test fixtures that write VariantDB directly with 'sent') still read. tests/test_variant_status.py: 8 tests; removing the service guard fails 4, removing the Literal fails the 422 test. Suite 912 passed. Not done: nothing sets 'ready' yet (Q4.7's assertion has no route).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
variants.status is constrained to draft and ready at the only place it is written, and the JSON create answers 422 for anything else; existing rows are left readable. Verified by tests/test_variant_status.py, mutation-checked; full suite 912 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
