---
id: TASK-33
title: >-
  `record_auth_failure` buckets on an attacker-supplied `key_id`, so varying the
  key per request writes one row per attempt
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 103300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P2. The aggregation defeats its own premise.** **`record_auth_failure` buckets on an attacker-supplied `key_id`, so varying the key per request writes one row per attempt** — exactly the unbounded growth ADR-153 §6's aggregate-don't-list rule exists to prevent. `auth/integrations.py` takes the claimed key straight off the `Authorization` header and truncates it to 64 characters; the bucket therefore only helps against an attacker who politely reuses one key. **Fix:** bucket on something the caller cannot vary — hash the claimed key, or fall back to the client alone when the key matches no credential. Two more, same table: **nothing prunes it**, unlike the login rate-limit counters which prune on write; and **nothing reads it** — no lockout, no alerting, no admin view, so it is write-only evidence today. The integration list screen is its natural reader. *Correction to the source question, which claimed there is no unique constraint: `uq_integration_auth_failure_window` exists in the model and in the live schema. Concurrent failures therefore raise `IntegrityError`, which `record_auth_failure` swallows by design — still an undercount, by a dropped increment rather than a duplicate bucket.* Source: [[Interview Prep - Auth, Permissions, Machine Principals]] → Q6.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 102, section "Bugs", position 33 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
