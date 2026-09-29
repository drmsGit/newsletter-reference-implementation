---
id: TASK-42
title: >-
  `purpose` defaults to `"marketing"` on every consent signature, where
  `brand_id` is a required positional.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-09-29 18:53'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 104200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P2.** **`purpose` defaults to `"marketing"` on every consent signature, where `brand_id` is a required positional.** `recipients/consent.py:34` sets `DEFAULT_PURPOSE = "marketing"` and every consent function takes `purpose: str = DEFAULT_PURPOSE` — `record_consent`, `latest_consent_event`, `latest_consent_status`, `latest_consent_statuses`, `consent_grid`, `consent_grid_many`, `has_consent`, `require_consent`, `is_consenting_filter`. The same 2026-09-15 addendum that widened the cell made `brand_id` a **required positional with no default anywhere**, arguing that *"a consent row whose brand was assumed is a consent record nobody gave. Forgetting it is a TypeError, by design."* The identical argument applies to purpose: a row whose purpose was assumed is a marketing grant nobody gave. Two fields of one cell, opposite treatment, same file, same build. Compounding it, [[ADR-163 — Per-Channel Consent and Addressability]] point 3 makes `transfer` a first-class purpose and **`"transfer"` appears nowhere in `backend/app/`** — so the vocabulary ships with one member while `BETA-SCOPE.md` flags the transactional-consent model as *"a possible adoption dealbreaker."* Source: `/business-interview-baseline` 2026-09-18 (P2-E2), verified same day.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 122, section "Bugs", position 42 in that section (top = do next). The description is the original entry, verbatim.

2026-09-29, from task-12: the same class one layer down. The DATABASE default purpose 'marketing' (and channel 'email') on delivery_executions was dropped by migrate_0024 as fail-open. The Python-side default="email" / default="marketing" on DeliveryExecutionDB (backend/app/delivery/db_models.py) remain and were deliberately left to this task.
<!-- SECTION:NOTES:END -->
