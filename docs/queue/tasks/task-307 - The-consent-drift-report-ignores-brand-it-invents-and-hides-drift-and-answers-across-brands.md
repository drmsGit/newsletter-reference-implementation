---
id: TASK-307
title: >-
  The consent-drift report ignores brand: it invents and hides drift, and
  answers across brands
status: To Do
assignee: []
created_date: '2026-10-08 22:44'
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
- [ ] #1 A two-brand test reproduces the invented and hidden drift and fails before the fix
- [ ] #2 Drift is computed per (brand, recipient, channel, purpose), and the route answers only for the working brand (or a platform-wide view is gated by its own permission, by decision)
<!-- AC:END -->
