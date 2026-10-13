---
id: TASK-378
title: >-
  Send screen froze on every press, tested only after planning, lost started
  sends, planned silently nothing
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 21:48'
updated_date: '2026-10-13 21:49'
labels:
  - frontend
  - backend
dependencies: []
type: bug
ordinal: 100100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** Found by the user on 2026-10-13, trying the send screen built for task-67 the day before.
1. "Freeze this version" stored a snapshot on every press, including "Freeze again" and when the person left the screen. That left frozen versions nobody will ever send (snapshots 8 and 10-12 on the scratch campaign).
2. The test appeared only after planning, so it looked missing.
3. A started send could not be continued after leaving the screen.
4. "Plan the send" stayed disabled without saying why: no audience chosen, or "At a time" with a date but no time, because a datetime field without a time has no value. The user's plans never reached the server (the API log showed no plan request), so nothing showed up under Deliveries.
Decided with the user: freeze at planning; test any time; continue open sends. Recorded in the ADR-183 addendum of 2026-10-13, amending points 1 and 3 of the 2026-10-12 one.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Planning freezes and plans in one action; a refused plan leaves no snapshot
- [x] #2 What goes out and the test render an unstored frame; a test can come before planning
- [x] #3 Planned and scheduled sends of the variant can be continued from the screen and from the delivery page
- [x] #4 The plan action says what is still needed; At a time is prefilled with a complete date and time
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-13, fixed in 206ca18 (CI green). Backend: GET /snapshots/variants/{id}/preview (frame built in memory, never stored), POST /delivery/variants/{id}/test replacing the 2026-10-12 test on a planned send, POST /delivery/variants/{id}/send-instances (freeze_and_plan: a refused plan deletes its snapshot), the send list filter variant_id, campaign_id and variant_id on a send's detail. Client: SendVariant steps what goes out, test (optional), plan, send; open sends listed to continue; the plan button says what is still needed; At a time prefilled with tomorrow 09:00; Continue on the send screen on a draft or scheduled delivery. Verified: test_send_screen (15) with 7 backend mutations killed; SendVariant.test.tsx (11) with 8 frontend mutations killed (one survivor fixed: sent sends are not offered to continue); full pytest 1929, vitest 286, tsc, Ruff, eslint (8 old warnings). Live, scratch campaign 16 variant 22, mock only: the preview rendered with the scratch profile's footer, a test went out before planning, Plan with nothing chosen said Still needed: an audience, At a time came prefilled, planning made exactly one snapshot (5 to 6) and a scheduled send, and the delivery page linked back to the screen. The leftover snapshots 8 and 10-12 on the scratch variant are left in place.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The send screen no longer stores a frozen version on every click: it freezes only when a send is planned, shows and tests the email without storing anything, lets a started send be continued, and says what is missing instead of silently doing nothing (ADR-183 addendum 2026-10-13). Verified by 26 tests with all mutations killed, full suites, CI and a live run on scratch data.
<!-- SECTION:FINAL_SUMMARY:END -->
