---
id: TASK-304
title: >-
  The consent tests' fallback snapshot has no modules, which task-228's floor
  would skip
status: Done
assignee:
  - '@claude'
created_date: '2026-10-08 20:54'
updated_date: '2026-10-09 09:07'
labels:
  - backend
dependencies: []
type: chore
ordinal: 200970
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The consent tests' fallback snapshot would make every recipient "nothing to show".** Found 2026-10-08 while adding task-98's tests to backend/tests/test_consent_gates.py.

The db fixture's send_to (around lines 162-275) first looks for the newest complete email snapshot in the database. If there is none, it builds a variant with **zero modules** and freezes that. The comment says a variant with no modules declares no required fields, so it passes the send check.

Since task-228 (ADR-086 addendum 2026-10-08), a recipient for whom nothing but the envelope rendered is excluded as "render: nothing to show". With the zero-module fallback, every consent test that expects a send would then fail for a rendering reason. That is the very confusion the fixture's own comments warn about.

Today the fallback never runs: the dev test database and CI's seeded one both hold a complete email snapshot. It fails the day one does not.

**The fix:** the fallback variant gets one static module that renders (a cta with a label and a url, say), so it is meaningful under the floor and still declares no catalogue fields. Add a test that forces the fallback path.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The fixture's fallback variant renders meaningful content under task-228's floor
- [x] #2 A test forces the fallback path and the consent tests still pass on it
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: fixed (commit dcb385c; CI green on 34849f4). The consent tests' fallback variant (send_to in backend/tests/test_consent_gates.py) now gets a header module (subject, preheader) and one static cta (label, url) instead of zero modules: meaningful under task-228's floor, still no catalogue fields, so the required-field gate passes. New test test_the_fixtures_fallback_snapshot_still_sends forces the fallback by making every existing snapshot look incomplete while the fixture chooses (monkeypatch.context, so the real send check still runs) and asserts the recipient is sent. It failed before the fix, excluded as 'nothing to show', which is the predicted failure. All 33 consent tests pass; full suite 1564.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The consent tests' fallback snapshot now renders a subject and a static call-to-action, so it is meaningful under task-228's floor; a test forces the fallback path and reproduced the failure before the fix. Full suite and CI green.
<!-- SECTION:FINAL_SUMMARY:END -->
