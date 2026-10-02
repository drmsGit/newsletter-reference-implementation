---
id: TASK-42
title: >-
  `purpose` defaults to `"marketing"` on every consent signature, where
  `brand_id` is a required positional.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-10-02 14:17'
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

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 No consent function defaults purpose
- [x] #2 Executions have no default channel or purpose; every creator sets both
- [x] #3 A recipient added by re-resolution carries the send's channel and purpose
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Verify: still true — 11 consent signatures defaulted purpose to marketing. 2. Reproduce the related ORM-default defect (a push send's late joiner planned as email). 3. Fix reconcile; drop execution column defaults; make purpose required; explicit MARKETING at the 8 app call sites. 4. Pin with structural tests and the reproduction test; mutation-check.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 122, section "Bugs", position 42 in that section (top = do next). The description is the original entry, verbatim.

2026-09-29, from task-12: the same class one layer down. The DATABASE default purpose 'marketing' (and channel 'email') on delivery_executions was dropped by migrate_0024 as fail-open. The Python-side default="email" / default="marketing" on DeliveryExecutionDB (backend/app/delivery/db_models.py) remain and were deliberately left to this task.

2026-10-02: still true when picked up. Done: purpose required on every consent function (keyword-only after channel for consenting_status_expr / is_consenting_filter); DEFAULT_PURPOSE renamed MARKETING with a comment saying it is not a default; app call sites pass purpose=MARKETING (graph audience, recipient list, create_recipient, decision consent check, audience gates, preview exclusion stack). Found and fixed in the same class: reconcile_executions_to_audience added executions with the column defaults, so a push send's late joiner was planned as email (reproduced first: tests/test_channels.py test_a_recipient_added_by_re_resolution_is_planned_as_a_push_too); channel now comes from the send's variant (channel_of_send, shared with create_delivery_execution) and purpose from the existing executions. The Python-side defaults on DeliveryExecutionDB.channel/purpose are removed (task-12's note). tests/test_purpose_is_never_assumed.py pins both rules; three mutants caught. ~55 test call sites now pass purpose explicitly (AST-driven edit). Not done, by scope: 'transfer' is still not in the vocabulary — the transactional-consent model is task-134. Suite 900 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
purpose is required on every consent function, as brand_id is; every app call site says MARKETING. A related defect found on the way is fixed: re-resolution planned a push send's late joiners as email executions; they now carry the send's channel and purpose, and the execution columns have no defaults left. Verified by a reproduction test, structural tests and mutation checks; full suite 900 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
