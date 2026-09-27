---
id: TASK-38
title: >-
  Brand-scoped roles are modelled but not enforced, so a grant on one brand
  works on all of them.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: p1
type: bug
ordinal: 103800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — P1.** **Brand-scoped roles are modelled but not enforced, so a grant on one brand works on all of them.** `RoleAssignmentDB` is `(user × role × brand)` and `permissions_for()` accepts a `brand_id`, but both guards call `has_permission(db, user, permission)` with no brand (`auth/dependencies.py:74,111`), which unions permissions across every assignment. A Manager on Brand A holding Viewer on Brand B passes Manager-level checks while working in Brand B. **Introduced 2026-08-02 with the access model** — the ADR-150 semantics are right, the enforcement is missing. **Two honest options:** resolve the owning brand for each scoped request and pass it in; or, since no resource is brand-owned yet, **defer brand RBAC and stop exposing a dimension that does not enforce its own meaning** — a false isolation guarantee is worse than none. Source: code review 2026-08-07 P1-02. **DECIDED 2026-09-14 — and the fork this entry offered turns out to rest on a false premise, so read this before starting.** The user's call: a brand filter on the permissions for humans, and for machine callers **one API key per brand** (n8n on brand 1 holds key 1, on brand 2 key 2), so the credential carries the scope. **The machine half is settled and also closes [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]'s open question about how an inbound request selects its brand** — it does not have to, because the key already did. **The human half is bigger than 'add a filter'.** `has_permission(db, user, permission, brand_id=None)` *already* takes a brand and already filters on it; no caller ever passes one. The reason is not an oversight: `SELECT table_name, column_name FROM information_schema.columns WHERE column_name LIKE '%brand%'` returns exactly one row — `role_assignments.brand_id`. **No campaign, content record, audience or send belongs to a brand at all**, so a grant saying "Manager on brand 2" has nothing to be checked against. Enforcing it means putting a brand on the resources and giving a request a way to say which brand it is acting in — which is the 'or delete the feature' branch, not the filter branch. Verified 2026-09-14. **Done — closed 2026-09-18, and this entry was stale for four days.** The 'or delete the feature' branch was taken and then completed: resources carry a brand (seven tables now hold a NOT NULL `brand_id`), a request states its working brand, and `_permitted` (`auth/dependencies.py:81-107`) checks brand-scoped permissions against it — refusing outright when there is no working brand rather than passing `None`, which would union across every grant. Covered by `test_brand_scoping.py:558` (`TestThePermissionCheckIsBrandAware`). The line numbers cited above (`auth/dependencies.py:74,111`) no longer exist. Found by `/interview-prep-baseline` 2026-09-18.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 112, section "Bugs", position 38 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
