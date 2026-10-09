---
id: TASK-343
title: The consent API silently takes an assertion without a purpose as marketing
status: To Do
assignee: []
created_date: '2026-10-09 18:54'
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
- [ ] #1 A consent assertion through the API without a purpose is refused with a clear error
- [ ] #2 An assertion with a purpose is recorded as before
- [ ] #3 The docstring no longer claims marketing is the honest default
<!-- AC:END -->
