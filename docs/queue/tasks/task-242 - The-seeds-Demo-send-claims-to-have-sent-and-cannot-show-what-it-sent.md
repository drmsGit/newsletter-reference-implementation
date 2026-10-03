---
id: TASK-242
title: The seed's "Demo send" claims to have sent and cannot show what it sent
status: Done
assignee:
  - '@claude'
created_date: '2026-10-02 19:38'
updated_date: '2026-10-03 09:30'
labels:
  - backend
dependencies: []
priority: p3
type: bug
ordinal: 104500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug, dev data]** Found 2026-10-02 while checking the new React deliveries screens (commit cf9c591) against the seeded dev DB.

`backend/scripts/seed_demo_data.py:337-357` writes the send called "Demo send" by hand: a `SendInstanceDB` with `status="sent"`, and 32 `DeliveryExecutionDB` rows with `status="sent"`. It never goes through `send_send_instance`. So:

- its stored `sent_count` / `failed_count` / `excluded_count` stay 0, while the list shows 32 recipients. The deliveries list therefore reads "sent, 0 / 0 / 0" beside "32";
- no execution has `sent_at` or a `delivery_record` (ADR-183 point 3), so every "As sent" link on it (32 of them) answers 409 and the screen says "nothing to show";
- the send claims a state the real send loop would never produce. A demo built on it teaches the opposite of ADR-183: that "sent" and "has a record of what it got" can come apart.

The send exists for a reason worth keeping: its executions anchor 60 days of click history (`EngagementEventDB` + `apply_event_to_signals`, lines 352-372) for the signal layer and the category graph. That history needs execution rows to hang from. Edition 2 (`:443-451`) already shows the honest pattern: snapshot, plan, fire through the real path.

Constraints: mock provider only; the send cap stays at 200 and the seed must not change it (see the comment at `:437-440`). The click events must still credit content only when they name it (ADR-182).

Related: task-71 (realistic seed content). ADR-183 point 6 (frameless and pre-record sends are not live data).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Every send the seed creates whose status is "sent" has stored counts that agree with its executions
- [x] #2 Every execution the seed marks "sent" either has a delivery record, so its as-sent view renders, or the send is not shown as a normal sent send
- [x] #3 The seeded engagement history (click events and their signal contributions) is preserved in volume and spread
- [x] #4 A test or the seed's own summary output proves both properties against a freshly seeded database
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-03, approach decided by the user (real send, dated back). `backend/scripts/seed_demo_data.py`: the Demo send is snapshotted, planned to a pinned audience of min(32, send cap) and fired with the mock provider. Then send, executions and snapshot are moved to 61 days ago, and each click names only content from that recipient's delivery record (sent_content_ids) that is also all-positive. Measured on the test DB (the seed is random): click contributions 242 -> 220, categories credited by clicks 10 -> 9, recipients who clicked 32 -> 24 (8 messages carried no all-positive content), raw click events 141 -> 94, because one click on a real pick credits several categories. Judged 'preserved' on the signal-layer measures and reported to the user with the numbers rather than tuned. Tests: `backend/tests/test_seed_demo_send.py` (3), reading the suite DB that conftest seeds. The old seed fails all 3; not dating back and clicking arbitrary content each fail one. The extended seed was also run end to end against the test DB. Suite 1040 passed, rc=0. Found on the way: the suite runs on '<dev>_test', rebuilt each run, not the dev DB; several test docstrings still say 'shared dev database'. The user's dev DB was NOT re-seeded.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The seeded Demo send now goes through the real send path (mock provider), so it has real counts and a delivery record per recipient. It is dated 61 days back, so its 60 days of clicks follow it, and each click names content the recipient was actually sent. The signal history kept close to its shape (click contributions 242 -> 220). Verified: 3 tests against the seeded suite DB, 3 mutants caught, suite 1040 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
