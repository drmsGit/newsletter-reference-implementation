---
id: TASK-239
title: >-
  Planning and firing a send from the Jinja UI raises NameError:
  `send_instance_create` and `send_instance_trigger` use `request` without
  declaring it
status: Done
assignee:
  - '@claude'
created_date: '2026-10-02 07:11'
updated_date: '2026-10-02 07:13'
labels:
  - backend
dependencies: []
priority: p1
type: bug
ordinal: 104100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found 2026-10-02 while researching task-49 (C8). `backend/app/frontend/router.py` `send_instance_create` (POST /ui/campaigns/{campaign_id}/snapshots/{snapshot_id}/send-instances) and `send_instance_trigger` call `working_brand_id(request, db)` but neither signature declares `request`, so both raise NameError (500). It arrived with the ADR-172 stage 4/6 brand rollout (commit 395f8be). Planning and firing a send from the Jinja UI is therefore broken. Nothing caught it: `tests/test_auth_policy.py:71` only resolves the policy for the route and no HTTP test posts to either route (`prepare_send_from_audience` is covered only by direct calls in `tests/test_channels.py` and `tests/test_consent_gates.py`). Not yet reproduced; the entry is unverified until the failing test exists. Governing ADR: ADR-172.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A failing HTTP test for each of the two routes exists first and is shown to fail before the fix
- [x] #2 Both routes declare `request: Request` and a signed-in session plans, then fires, a send via the Jinja flow
- [x] #3 Each new test is mutation-checked (removing the argument makes it fail)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reproduced 2026-10-02: both routes returned 500 before the fix. Fix: declare request: Request on both. tests/test_ui_send_flow.py; mutation-checked by restoring the original router (both tests fail). Full suite 789 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added request: Request to send_instance_create and send_instance_trigger in app/frontend/router.py. Two HTTP tests (tests/test_ui_send_flow.py) failed with 500 on the original code and pass now; full suite 789 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
