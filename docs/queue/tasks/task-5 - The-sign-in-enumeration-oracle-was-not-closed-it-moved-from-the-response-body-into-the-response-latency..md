---
id: TASK-5
title: >-
  The sign-in enumeration oracle was not closed, it moved from the response body
  into the response latency.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: p1
type: bug
ordinal: 100500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P1, and it is logged against a launch gate recorded as CLOSED.** **The sign-in enumeration oracle was not closed, it moved from the response body into the response latency.** Gate 4b's fix made every outcome return one unconditional 303 — known address, unknown address, deactivated user, failed send — and that discipline is thorough and stays. But `request_login_code` runs inline (`auth/router.py:93`): for a **known** address it supersedes outstanding codes, inserts a row, commits, and then calls the provider **synchronously** over HTTPS through `deliver_code`, while an **unknown** address returns after a single SELECT. With a real provider that is a several-hundred-millisecond difference in how long the identical 303 takes to arrive. **Fix:** queue the delivery, or floor the response time, so the two paths cost the same. **Why P1:** `docs/business/LAUNCH-GATES.md` records gate 4b as closed and the comment at `auth/router.py:77-79` says avoiding precisely this substitution was the point — a gate recorded as closed and not closed is worse than one recorded as open. Mock mail is the default, so the gap only opens with a real provider, which is the configuration public exposure uses. Source: [[Interview Prep - Auth, Permissions, Machine Principals]] → Q5.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 39, section "Bugs", position 5 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
