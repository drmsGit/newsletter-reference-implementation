---
id: TASK-242
title: The seed's "Demo send" claims to have sent and cannot show what it sent
status: To Do
assignee: []
created_date: '2026-10-02 19:38'
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
- [ ] #1 Every send the seed creates whose status is "sent" has stored counts that agree with its executions
- [ ] #2 Every execution the seed marks "sent" either has a delivery record, so its as-sent view renders, or the send is not shown as a normal sent send
- [ ] #3 The seeded engagement history (click events and their signal contributions) is preserved in volume and spread
- [ ] #4 A test or the seed's own summary output proves both properties against a freshly seeded database
<!-- AC:END -->
