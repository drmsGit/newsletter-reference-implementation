---
id: TASK-317
title: >-
  Login-code issuance runs scrypt only for existing accounts and reopens the
  timing oracle
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-09 08:02'
updated_date: '2026-10-09 08:32'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Severity: high. Unauthenticated callers can distinguish existing accounts by a deliberately expensive hashing operation. Reachable today through both login-code request routes.

Evidence: backend/app/auth/service.py:775-778 returns immediately for an unknown/inactive user. For an active user it calls hash_login_code at line 789 before committing and returning. hash_login_code at 90-94 uses scrypt with the parameters at line 84; the source documents approximately 25 ms per hash. Delivery is deferred, but hashing remains in the response-critical path. The issue_login_code docstring's 0.6 ms residual-work measurement predates this new cost. backend/tests/test_signin_timing.py tests that a half-second mail delay does not hold up the response; it does not require equal KDF work for known and unknown requests.

Reproducer test to implement: instrument hash_login_code on known and unknown account requests and assert the known request executes one KDF while the unknown request executes none. A real-server comparison with delivery mocked and equal request budgets should then demonstrate the residual response-latency difference. The code path is verified; no new timing measurement was run in this continuation, so the cited duration is the source's estimate, not a fresh measurement.

ADR-151 section 2 and its timing addendum prohibit account enumeration. Equalize the expensive issuance work across address outcomes, or move all account-dependent expensive work beyond the response boundary while preserving safe issuance and throttling.

Related: completed task-5 removed synchronous transport latency and task-35 later introduced the KDF. The verify route already does uniform KDF work; the issue route missed the corresponding integration.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Known and unknown account requests perform equivalent response-critical KDF work, or both defer it beyond the response.
- [ ] #2 Both JSON and form request routes preserve identical response behavior and request throttling.
- [ ] #3 A regression check detects reintroducing account-dependent expensive work even when mail delivery remains deferred.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's code review (docs/queue/docs/doc-1, draft-9) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: issue_login_code returns for an unknown or inactive address (backend/app/auth/service.py:775-778) before any hashing, while a known address runs hash_login_code (scrypt) at :789 before the response. This regression came from task-35. Fix together with task-316 if convenient.
<!-- SECTION:NOTES:END -->
