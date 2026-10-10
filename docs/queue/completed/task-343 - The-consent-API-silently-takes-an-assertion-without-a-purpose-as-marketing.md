---
id: TASK-343
title: The consent API silently takes an assertion without a purpose as marketing
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 18:54'
updated_date: '2026-10-10 20:21'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** Since task-42 every internal consent function requires a purpose (backend/app/recipients/consent.py:30-37, :76, :112). The reasoning there is that a silent default is how consent for one purpose gets recorded as another. But the API's consent-assertion input still defaults it: backend/app/recipients/models.py:113 has purpose: str = "marketing". It is justified only in the docstring at :103-106 ("an assertion that says nothing about channel is an assertion about email marketing, which is the only cell that exists today"), which contradicts consent.py. The database column defaults too (backend/app/recipients/db_models.py around :61).

Decided by the user in the 2026-10-09 interview review (business baseline P2-E2): the API refuses a consent assertion without a purpose. Which purposes exist, for example transfer to an ad platform, stays with task-134; the finding itself is non-blocking.

Observed, not decided: the same input also defaults channel to "email" (:112). The docstring's "the only cell that exists today" is no longer true for channels, since push exists. The final-design pass should say whether channel follows purpose. Whether the column default stays (for rows written by migrations) is open too.

Source: docs/business-interview-baseline.md → P2-E2.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A consent assertion through the API without a purpose is refused with a clear error
- [x] #2 An assertion with a purpose is recorded as before
- [x] #3 The docstring no longer claims marketing is the honest default
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10, done (commit 188c866). ADR-163; business baseline P2-E2.

What changed: ConsentSyncRequest.purpose has no default any more, so an assertion without one is refused with 422 naming the field, and nothing is recorded. The docstring now says why and no longer claims marketing is the honest default.

Not decided, so left alone: the channel default (email). It is noted in the docstring for task-134, since push exists and 'the only cell that exists today' is no longer true for channels.

Other files:
- tests/test_brand_boundary.py: its _payload helper now states purpose 'marketing'.
- frontend/src/api/schema.d.ts regenerated: the field was already typed as required; only its description and the @default changed.

Tests: backend/tests/test_consent_purpose_required.py, 3 tests. 2 failed first: without a purpose the API answered 200 and wrote the event.
Mutation: the default restored, 2 failed.
Suite: 1650 passed. Ruff and tsc clean.

CI: the run for 188c866 was cancelled by the next push to main (concurrency group). Run 38083185466 for 2f18e28, which contains it, is green.

No live check: the change is a request-validation rule fully covered over HTTP by the tests.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A consent assertion through the API must now say what it is for: ConsentSyncRequest.purpose is required, so an assertion without one is refused with 422 naming the field and nothing is recorded, instead of silently becoming marketing consent. The channel default is untouched (not decided, noted for task-134). Verified by test_consent_purpose_required.py (failed first, mutation caught), the full suite (1650), and green CI on 2f18e28, which contains the change.
<!-- SECTION:FINAL_SUMMARY:END -->
