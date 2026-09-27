---
id: TASK-40
title: '`delete_brand` blocks on five tables; seven carry a NOT NULL brand FK.'
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 104000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P2.** **`delete_brand` blocks on five tables; seven carry a NOT NULL brand FK.** `auth/service.py:201-207` counts content records, campaigns, audience groups, sends and role assignments. Missing: **`consent_events.brand_id`** (`recipients/db_models.py:57`, added by `migrate_0008_consent_brand.sql` *after* the guard was written) and **`integration_grants.brand_id`** (`auth/db_models.py:298`). A brand holding only consent rows, or only a machine grant, passes the `blocking` check and reaches `db.query(BrandDB)...delete()` at `:215`, raising `IntegrityError` — the exact foreign-key failure the docstring says the guard exists to prevent. No data is lost (the transaction fails), but the user gets a 500 instead of the sentence naming what blocks them. **The consent one matters beyond the crash:** refusing on consent rows is also what would stop a brand being deleted and recreated as a way of dropping an opt-out record. [[brand]] states the maintenance rule — a new brand-carrying table must be added to these counts — and two tables have since been added without it. Source: `/interview-prep-baseline` 2026-09-18 (Brand Q7), verified same day.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 118, section "Bugs", position 40 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
