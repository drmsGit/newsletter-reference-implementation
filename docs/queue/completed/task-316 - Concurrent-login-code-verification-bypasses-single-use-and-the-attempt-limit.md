---
id: TASK-316
title: Concurrent login-code verification bypasses single use and the attempt limit
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 08:01'
updated_date: '2026-10-09 08:39'
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
- [x] #1 Simultaneous correct verification of one code can create at most one authenticated session.
- [x] #2 Concurrent incorrect submissions consume attempts atomically and cannot exceed the configured guessing budget.
- [x] #3 Rejected verification paths retain the existing uniform KDF-work property.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's code review (docs/queue/docs/doc-1, draft-2) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: verify_login_code (backend/app/auth/service.py:831) reads the unconsumed LoginCodeDB row without with_for_update and increments attempts in Python (:864), so concurrent verifications race. Consider fixing together with task-317, the other sign-in finding.

2026-10-09: fixed together with task-317 (commit 68b3589; CI green).

Change: verify_login_code reads the unconsumed code with .with_for_update() (backend/app/auth/service.py). A second concurrent verification waits on the lock. Under READ COMMITTED, Postgres then re-checks it against the committed row: a consumed code no longer matches the WHERE clause, and attempts is the current value. The KDF still runs exactly once on every path (task-35). The lock is held through the KDF, which serialises verifications for one user only.

Tests (backend/tests/test_login_code_races.py):
- two threads with their own sessions submit the correct code, lined up at the KDF by a barrier that times out once the lock serialises them: at most one session opens;
- CODE_MAX_ATTEMPTS parallel wrong guesses: all of them count, and the correct code is refused afterwards.
Both reproduced the review's finding before the fix: two sessions from one code, and five guesses counted as one. Mutation check: removing with_for_update fails both. The full suite passed, as did the existing sign-in, timing and JSON-session tests.

Live check: a real sign-in on the dev app (request a code, enter it) works through the locked verification.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A sign-in code is single use and its guess budget holds under concurrency: the code row is locked while it is checked. Verified by two concurrency tests that reproduced the race before the fix, a mutation check, the full suite, CI green and a live sign-in.
<!-- SECTION:FINAL_SUMMARY:END -->
