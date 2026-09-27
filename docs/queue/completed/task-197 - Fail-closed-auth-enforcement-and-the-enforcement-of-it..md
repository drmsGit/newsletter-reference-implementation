---
id: TASK-197
title: 'Fail closed: auth enforcement, and the enforcement of it.'
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 506100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Feature] — security, do before any public exposure.** **Fail closed: auth enforcement, and the enforcement of it.** Two related gaps from the 2026-08-07 review. **(a)** `auth_enforced()` defaults to **False** (`auth/dependencies.py`), so both `require_permission()` and `enforce_policy()` return without a user while it is off. That was a deliberate first-slice choice — turning it on before anyone had signed in would have locked the operator out of the page holding the switch — and a startup warning announces it. **It is still fail-open by default**, which means a deployment can ship a complete role model with no access control. The reviewer's recommendation is right for anything beyond local use: default to enforced, and make the frictionless mode an **explicit** `APP_MODE=development` / `AUTH_DISABLED=true` that a production mode refuses. **(b)** Add **CSRF tokens** to mutating UI forms and validate them centrally (P2-02). `SameSite=Lax` blunts classic cross-site POST but is not an application-level strategy, particularly for same-site and subdomain deployments. **(c)** Add **rate limiting to login-code requests** (P2-03) — per normalised email and IP, small rolling window, plus a global circuit breaker. Codes already have a TTL, single use and an attempt limit, but *requesting* is unbounded, and each request invalidates the previous code and may send a real email: mailbox spam, provider cost, lockout-by-churn, and an easy operational DoS. Source: code review 2026-08-07 P1-01, P2-02, P2-03. **DONE 2026-09-13 — this is launch gate 4, and all three parts are closed.** **(a)** `auth_enforced()` defaults to **True** (`410b5fc`); the reviewer's suggested `AUTH_DISABLED=true` escape hatch was **not** built, because the narrower `AUTH_DEV_SHOW_CODE=true` puts the sign-in code back in the log so an operator signs in *as themselves* rather than switching access control off for everyone — same bar, much smaller hole. **(b)** CSRF covers all 62 forms through one router-level dependency beside `enforce_policy`, failing closed (`410b5fc`). **(c)** Login-code requests are rate limited per address and per IP in database rows (`dfc84a3`), five per address per 15 minutes and twenty per client per hour. The "global circuit breaker" the review also suggested was not built and is not missed: the per-client limit already caps aggregate volume, and a global breaker would let one attacker lock every operator out of sign-in. **A throttled request returns the same neutral 303 as every other outcome**, so the limit cannot be used to probe which addresses exist.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 625, section "Done", position 61 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
