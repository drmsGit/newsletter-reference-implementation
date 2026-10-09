---
id: TASK-342
title: 'Session lengths are fixed in code, though they are company policy'
status: To Do
assignee: []
created_date: '2026-10-09 18:49'
updated_date: '2026-10-09 18:52'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 201050
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** The absolute session lifetime (12 hours) and the idle timeout (60 minutes) are code constants: SESSION_ABSOLUTE_HOURS and SESSION_IDLE_MINUTES in backend/app/auth/service.py around :51-52. backend/app/settings/service.py has no getter for either. These two are company policy: a works council or an ISO 27001 auditor may require other lengths, and the repo's own rule gives numbers to the company and the mechanism to the product.

Decided by the user in the 2026-10-09 interview review (business baseline P2-B1; recorded in a 2026-10-09 addendum to ADR-151): the two session lengths become company settings, each clamped to a safe range. The attack-resistance numbers stay in code as a stated exception: sign-in code lifetime, guesses, and code-request rate limits. Decided now, built later.

Left to the final-design pass:
- the safe ranges;
- whether a changed length applies to sessions that already exist;
- that the change is audited like other settings (backend/app/settings/audited.py).

Source: docs/business-interview-baseline.md → P2-B1.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Absolute session lifetime and idle timeout are company settings with enforced safe ranges
- [ ] #2 Sign-in code lifetime, attempts and request limits remain code constants
- [ ] #3 Changing a session length is audited
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09, from writing the ADR-151 addendum: the session constants are at backend/app/auth/service.py:52-53, not :51-52. Facts for the final-design pass:
- TOUCH_INTERVAL is 60 seconds (:905) and is commented as short against the idle timeout, so an idle floor near it would break that.
- The cookie max_age derives from SESSION_ABSOLUTE_HOURS (backend/app/auth/router.py:194 and :663).
- Absolute expiry is stamped into each session row at creation (:892), while idle is checked against the constant on every request (:930). So 'does a change apply to existing sessions' plays out differently for the two.
<!-- SECTION:NOTES:END -->
