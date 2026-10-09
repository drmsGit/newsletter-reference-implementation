---
id: TASK-320
title: >-
  A no-pick decision leaves an older ineligible resolution available to
  rendering
status: To Do
assignee: []
created_date: '2026-10-09 08:01'
updated_date: '2026-10-09 08:23'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Severity: high. Rendering can use content that the current decision explicitly cannot select. Reachable today.

Evidence: backend/app/decision/service.py:60-63 returns None on an empty candidate result without representing that outcome in the resolution state. backend/app/rendering/frame.py:148-185 then selects the latest historical per-recipient or generic resolution and resolves its pinned version, without reapplying current candidate eligibility.

Reproduction: obtain a successful pick, remove that record's channel-readiness entry, execute the slot again and observe None, then render the slot. The previous now-unready record still appears. Reproduced during the first review stage. The same stale-result mechanism defeats changed category/status eligibility and can defeat the no-meaningful-content floor.

ADR-174 and ADR-179 require machine-eligible candidates; ADR-086 permits empty slots. Represent the current no-pick result and make a fresh render/send honor it while preserving legitimate historical as-sent evidence.

Related: completed task-284 repaired candidate eligibility and task-228 introduced the send floor. This downstream fallback bypasses those controls; task-234's decision-execution efficiency is related but different.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 After a previously successful pick becomes ineligible and a new execution returns no pick, a fresh render/send does not use the previous pick.
- [ ] #2 Current no-pick outcomes remain distinct from immutable historical delivery evidence.
- [ ] #3 The meaningful-content floor observes the actual current decision outcome.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's code review (docs/queue/docs/doc-1, draft-4) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: execute_decision_slot returns None on no result without recording it (backend/app/decision/service.py:62-63), and _pick_for_slot (backend/app/rendering/frame.py:148) takes the newest stored resolution.
<!-- SECTION:NOTES:END -->
