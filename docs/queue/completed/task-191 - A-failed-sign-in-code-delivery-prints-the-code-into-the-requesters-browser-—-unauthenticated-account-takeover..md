---
id: TASK-191
title: >-
  A failed sign-in-code delivery prints the code into the requester's browser —
  unauthenticated account takeover.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
priority: p0
type: bug
ordinal: 505500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — P0, security. Blocks public exposure.** **A failed sign-in-code delivery prints the code into the requester's browser — unauthenticated account takeover.** `deliver_code()` returns `True` only on `result.success` (`auth/service.py:276`); every other outcome — misconfigured provider, expired or revoked API key, rate-limit rejection, network error, caught exception (`:277-279`) — returns `False`. `request_login_code()` then ends `return None if delivered else code` (`:310-311`), and the router renders that code with `"prefilled": code` and a hard-coded `"dev_mode": True` (`auth/router.py:63-76`). **So an unauthenticated visitor types an Admin's address, delivery fails for any reason, and the platform shows them the victim's live six-digit code and pre-fills the verification field with it.** The function's own docstring (`service.py:284-288`) says it returns the code *"only when the dev path is active"* — the intent is right, the implementation does not do it; the `dev_code_visible()` gate at `:253` is an early return that the failure path below falls straight through. The router comment asserting the branch is "confined to a branch production never reaches" is the assumption that is wrong. **Fix (~3 loc):** have `deliver_code` distinguish "not attempted (dev)" from "attempted and failed", and return the code only for the first — e.g. `return None if not dev_code_visible() else code`. **Decide the recovery path in the same change:** this makes a real delivery failure silent for the user (neutral notice, no code, only a `logger.warning` at `:275`), which is the correct posture and a worse support experience — the module docstring at `:14-16` already worries about exactly this lockout, and `AUTH_DEV_SHOW_CODE` (`:241`) is one answer. Not covered by `tests/test_auth.py`, which never exercises a delivery failure. **Not** P1-01 (fail-open enforcement), **not** P2-03 (rate limiting), **not** P2-01 (cookie) — grepped, it is new. **Traced statically, not reproduced:** confirm by pointing `SYSTEM_MAIL_PROVIDER` at a real provider with a deliberately invalid key and requesting a code for a known address. Source: code-slimmer sweep 2026-08-21, Cluster 6 A1. **DONE 2026-09-13, together with the P1 enumeration oracle — they were the same three lines.** `deliver_code` now returns a tri-state (`dev_not_attempted` / `sent` / `failed`) so "nothing was sent" can never again be confused with "the send failed", and only the first may return the code. **The recovery path, decided:** a failed real send shows the user the *same neutral response as success*, because telling them delivery failed reveals that delivery was attempted — which happens only for addresses that exist. The failure is logged at `error` instead, since that line is the only signal anyone gets. Closes **launch gate 4b**.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 613, section "Done", position 55 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
