---
id: TASK-316
title: Concurrent login-code verification bypasses single use and the attempt limit
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-09 08:01'
updated_date: '2026-10-09 08:32'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Severity: high. One code can issue multiple sessions and parallel guesses evade the attempt budget. Reachable today.

Evidence: backend/app/auth/service.py:831-872 reads an unconsumed LoginCodeDB without a row lock; checkable uses the previously read attempts, the KDF runs, then attempts and consumed_at are assigned and committed. Concurrent transactions read the same values and overwrite each other's counter.

Reproduction: issue one code in the disposable test database, use independent sessions and a barrier around the real login_code_matches call. Two concurrent correct submissions both return valid sessions; eight concurrent incorrect submissions leave attempts at one. Both cases were reproduced during the first review stage. Existing sequential single-use tests do not exercise this race.

ADR-151 section 2 requires single use and bounded guesses. Serialize the eligibility check and consumption/attempt accounting or use a conditional atomic write, while keeping equivalent KDF work on rejected paths.

Related: task-35 strengthened hashing; task-124 covers broader contention but does not establish atomic login-code consumption.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Simultaneous correct verification of one code can create at most one authenticated session.
- [ ] #2 Concurrent incorrect submissions consume attempts atomically and cannot exceed the configured guessing budget.
- [ ] #3 Rejected verification paths retain the existing uniform KDF-work property.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's code review (docs/queue/docs/doc-1, draft-2) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: verify_login_code (backend/app/auth/service.py:831) reads the unconsumed LoginCodeDB row without with_for_update and increments attempts in Python (:864), so concurrent verifications race. Consider fixing together with task-317, the other sign-in finding.
<!-- SECTION:NOTES:END -->
