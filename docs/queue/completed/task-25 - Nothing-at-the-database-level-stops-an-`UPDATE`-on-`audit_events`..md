---
id: TASK-25
title: Nothing at the database level stops an `UPDATE` on `audit_events`.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-10-01 20:32'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 102500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P2. Append-only is discipline, and a `REVOKE` would make it a guarantee.** **Nothing at the database level stops an `UPDATE` on `audit_events`.** What enforces immutability today is that the table offers no field inviting one — no `status`, no `updated_at` — and the service exposes only `record()`. That is the right design and is not what changes. But it stops holding the moment somebody adds a mutable column, and **neither the database nor the test suite would catch that**. **The threat model settles the effort question:** what is being defended against is a careless future contributor, not a privileged operator — and a contributor is exactly who a database-level refusal stops and a docstring does not. A `REVOKE UPDATE` is cheap; cheap-and-not-taken is the one combination that needs a reason rather than a rationale. Note it must survive `create_all`, which is how the test database is built. Source: [[Interview Prep - Channels, Audit]] → B-Q1.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 86, section "Bugs", position 25 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The database now refuses UPDATE on audit_events via a BEFORE UPDATE trigger — not the proposed REVOKE, which was measured to do nothing because the app's role is a superuser. Created by create_all (after_create listener) and by migrate_0025; the schema comparison now checks triggers, so both paths must agree. DELETE left possible (test cleanup; erasure is ADR-153 point 5's question). Tests include an update refused even with every privilege granted; three mutations caught; applied to dev via the runner; 768 pass.
<!-- SECTION:FINAL_SUMMARY:END -->
