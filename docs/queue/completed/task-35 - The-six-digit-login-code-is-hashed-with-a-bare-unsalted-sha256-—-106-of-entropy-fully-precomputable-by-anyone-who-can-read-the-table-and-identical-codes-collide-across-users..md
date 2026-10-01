---
id: TASK-35
title: >-
  The six-digit login code is hashed with a bare unsalted sha256 — 10^6 of
  entropy, fully precomputable by anyone who can read the table, and identical
  codes collide across users.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-10-01 21:37'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 103500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P2, narrow and cheap.** **The six-digit login code is hashed with a bare unsalted sha256 — 10^6 of entropy, fully precomputable by anyone who can read the table, and identical codes collide across users.** `hash_secret` (`auth/service.py:61-62`) is one primitive serving four roles: session tokens, machine-credential secrets, rate-limit identifiers and `login_codes.code_hash`. For the first three the argument is sound — there is no dictionary of 32 random bytes, and a KDF would sit on the hot path of every machine request. **The one input that genuinely fits the KDF rationale is the one that does not get it**, because the weakest input inherited the strongest one's justification. **Fix:** salt or KDF the login code specifically; leave the other three paths alone. Compensating controls are real and are why this is P2 not P1 — five attempts, the code burned on use, a 10-minute TTL, outstanding codes superseded, and a reader of `login_codes` can read `auth_sessions` anyway. Note `csrf_token_for` already had to be manually domain-separated for the same reason: one primitive, four roles. Source: [[Interview Prep - Auth, Permissions, Machine Principals]] → Q4.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 106, section "Bugs", position 35 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Login codes are stored with salted scrypt (hash_login_code), ~25 ms per guess — about seven CPU-hours per code against a 10-minute TTL; the other three hash_secret roles are untouched. Also closed a timing oracle the fix would otherwise have opened: verify now runs the KDF exactly once on every path. migrate_0026 widens the column; pre-change codes fail closed and expire. Tests count KDF runs per path; two mutations caught; applied to dev; 787 pass.
<!-- SECTION:FINAL_SUMMARY:END -->
