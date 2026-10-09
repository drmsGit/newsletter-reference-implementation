---
id: TASK-307
title: >-
  The consent-drift report ignores brand: it invents and hides drift, and
  answers across brands
status: Done
assignee:
  - '@claude'
created_date: '2026-10-08 22:44'
updated_date: '2026-10-09 07:20'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Bug: the consent-drift report ignores brand. It reads and answers across every brand, and it can both invent drift and hide it.** Found by the code-slimmer sweep of 2026-10-08 (finding D1) and verified by hand the same day.

**What the code does.** `detect_consent_drift` (`backend/app/recipients/service.py:409`) reads the whole `consent_events` table with no brand filter. It walks the table oldest to newest and keeps the latest event, and the latest CRM-sourced event, per key `(recipient_id, channel, purpose)`, so the brand is not part of the key. `ConsentDriftItem` (`backend/app/recipients/models.py:142`) has no brand field. The route `GET /recipients/consent/drift` (`backend/app/recipients/router.py:136`) takes no working brand.

**Why that is wrong.** Since the ADR-163 addendum of 2026-09-15, consent is per brand: an opt-out lands on the brand that mailed the person (`backend/app/providers/service.py:196-216`), and `consent_events.brand_id` is NOT NULL. Comparing across brands produces three faults:
- **Invented drift.** Brand B's later opt-out (from a bounce, say) is compared with brand A's CRM assertion and reported as drift, though both brands are internally consistent.
- **Hidden drift.** If brand B's CRM event is newer, it masks brand A's real disagreement.
- **Cross-brand exposure.** The route answers for every brand, with each person's email address (`ConsentDriftItem.email`), to anyone allowed to read it in their working brand. ADR-150 point 2 makes the brand switcher a hard boundary.

**Why nothing caught it.** The drift tests use one brand (`backend/tests/test_consent_gates.py:615`, `:656`).

**One decision first:** report drift **per brand**, as the working brand's drift only, the way every other list behaves, or **platform-wide with a brand column**, for an operator who reconciles every brand's CRM at once. Per brand matches ADR-150 point 2 and the rest of the API. A platform-wide view would need its own permission and a reason.

**Fix, once decided:**
1. Write a two-brand test that fails today: an opt-out in B and a CRM assertion in A must not show as drift in either, and a real disagreement in A must show even when B's CRM event is newer.
2. Add `brand_id` to the grouping key and, if platform-wide, to `ConsentDriftItem`.
3. Scope the route by working brand (or gate a platform view behind a permission).
4. Optionally, name the "latest event wins" ordering once. It is written out at `backend/app/recipients/consent.py:135`, `:178`, `:212`, `:249`, `:300` and `:415`, and this function walks the opposite direction, which is how one copy drifted.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A two-brand test reproduces the invented and hidden drift and fails before the fix
- [x] #2 Drift is computed per (brand, recipient, channel, purpose), and the route answers only for the working brand (or a platform-wide view is gated by its own permission, by decision)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: decided and fixed (commit d60c8cd; CI green).

Decided with the user: the report is per working brand, like every other list (ADR-150 point 2, ADR-172). Rejected: a platform-wide report with a brand column behind its own permission.

Fix:
- backend/app/recipients/service.py: detect_consent_drift(db, *, brand_id) filters ConsentEventDB.brand_id, so the latest-event comparison runs per (recipient, channel, purpose) within one brand. That is the key ConsentEventDB's own docstring states (backend/app/recipients/db_models.py:36). The brand is required and keyword-only, so forgetting it is a TypeError.
- backend/app/recipients/router.py: GET /recipients/consent/drift takes Depends(working_brand). The OpenAPI schema is unchanged apart from the docstring, and schema.d.ts was regenerated.
- backend/tests/test_consent_gates.py: _drift_for passes the default brand.
- The optional step 4 (naming the "latest event wins" ordering once) was not done. It is still a candidate for a consent cleanup.

Tests: backend/tests/test_consent_drift_brand.py covers four cases:
- invented drift: brand B's opt-out must not show in A;
- hidden drift: brand B's newer CRM event must not mask A's disagreement;
- the brand is required;
- the route, called as a machine with view in each brand, serves only that brand's drift.
All four failed before the fix; the route test reproduced the cross-brand leak. Mutation check: 3 of 3 caught (brand filter dropped, brand made optional, route ignoring the working brand). Full suite: 1535 passed.

Live check, read-only, on the dev data after signing in: the route answers 200 in the working brand (Default). The dev data has no drift in either brand (Default: 55 events; Demo Brand B: 20), and none under the old cross-brand rule either, so the live check proves the scoped route works but cannot show the difference. Writing scratch consent events would change real recipients' effective consent, so the difference is proven by the tests instead.

Finding, not fixed (outside this task): the crm_ahead direction appears unreachable. Latest event wins, so the effective event is never older than the CRM's. The code's own comment in detect_consent_drift concedes this, yet ConsentDriftItem.direction and the docstring still describe crm_ahead as a live case. Raised with the user, not filed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The consent-drift report is now computed and answered per working brand. detect_consent_drift requires the brand and reads only that brand's events, and the route passes the working brand. Before, it invented drift from another brand's opt-out, hid real drift behind another brand's newer CRM event, and served every brand's drift with email addresses. Verified by test_consent_drift_brand.py (4 tests failing before the fix, 3/3 mutants caught), the full suite (1535 passed), CI green and a read-only live check of the route.
<!-- SECTION:FINAL_SUMMARY:END -->
