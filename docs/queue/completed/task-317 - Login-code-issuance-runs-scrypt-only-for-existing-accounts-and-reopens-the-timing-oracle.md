---
id: TASK-317
title: >-
  Login-code issuance runs scrypt only for existing accounts and reopens the
  timing oracle
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 08:02'
updated_date: '2026-10-09 08:39'
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
- [x] #1 Known and unknown account requests perform equivalent response-critical KDF work, or both defer it beyond the response.
- [x] #2 Both JSON and form request routes preserve identical response behavior and request throttling.
- [x] #3 A regression check detects reintroducing account-dependent expensive work even when mail delivery remains deferred.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's code review (docs/queue/docs/doc-1, draft-9) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: issue_login_code returns for an unknown or inactive address (backend/app/auth/service.py:775-778) before any hashing, while a known address runs hash_login_code (scrypt) at :789 before the response. This regression came from task-35. Fix together with task-316 if convenient.

2026-10-09: fixed together with task-316 (commit 68b3589; CI green).

Change: issue_login_code runs hash_login_code on a throwaway random code for an unknown or inactive address before returning None, so both outcomes do the same scrypt work before the response (backend/app/auth/service.py). This is the approach verification already takes on every path (login_code_matches). The regression came from task-35, which added scrypt to issuing for known addresses only. The residual difference is the database write for a known address (supersede, insert, commit), which is what task-5's measured bound already covered.

Test: test_issuing_runs_the_same_kdf_work_for_every_address (backend/tests/test_login_code_races.py) counts hashlib.scrypt calls inside issue_login_code for a known and an unknown address, and asserts they are equal and at least one. It failed before the fix (1 against 0). Mutation check: removing the dummy hash fails it. This is a structural check, not a latency measurement. It catches the expensive work being reintroduced for one outcome only, which is AC #3.

Both routes (the JSON /auth/session/request and the form /ui/login) call the same issue_login_code (backend/app/auth/service.py:820, backend/app/auth/router.py:85), so their behaviour and throttling are unchanged and identical.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Issuing a sign-in code now does the same scrypt work for unknown and known addresses, closing the account oracle task-35's hash had reopened. Verified by a KDF-count test that failed before the fix, a mutation check, the full suite and CI green.
<!-- SECTION:FINAL_SUMMARY:END -->
