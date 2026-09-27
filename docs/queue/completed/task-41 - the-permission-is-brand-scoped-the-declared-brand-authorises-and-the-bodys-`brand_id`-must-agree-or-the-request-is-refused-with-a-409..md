---
id: TASK-41
title: >-
  the permission is brand-scoped, the declared brand authorises, and the body's
  `brand_id` must agree or the request is refused with a 409.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 104100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — P2, and the fix was a decision, not an edit. DECIDED and DONE 2026-09-20** (ADR-150 addendum of that date): the permission is brand-scoped, the declared brand authorises, and the body's `brand_id` must agree or the request is refused with a 409. Both fields stay, because they answer different questions — the header says which brand the caller may act in, the body says which brand the CRM is asserting about — and keeping both is what makes a disagreement visible instead of silently picking a winner. Original finding: **`recipients.consent` is classified platform-level on grounds that migrate_0008 falsified.** `auth/permissions.py:70` states the rule: *"a permission is brand-scoped if the rows it guards carry a `brand_id`."* The justification for excluding this one (`permissions.py:101-104`) reads: *"recipients carry no brand (point 9) and neither do signal contributions (point 8), so `recipients.manage`, `recipients.consent` and `insight.write` have no brand to be checked against."* True when written; false since `consent_events.brand_id` became NOT NULL. Effect: `policy.py:129` maps `/recipients/{external_id}/consent` to `RECIPIENTS_CONSENT`, `_permitted` takes the non-scoped branch, and a Manager granted `recipients.consent` on brand A can write a consent row for brand B — the record [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §7 calls the answer to a UWG §7 complaint. **Two honest options, and this needs the call before any edit:** add `RECIPIENTS_CONSENT` to `BRAND_SCOPED`, which makes every existing machine caller without `X-Brand` start failing with a 400; or keep it platform-level and rewrite the comment to say *why* — consent capture is arguably a platform-level act, and the file already carries exactly one acknowledged exception to its own rule (`ai.run`, because spend is one company-wide pot). What is not defensible is the current state, where the stated rule does not produce the current answer. Source: `/interview-prep-baseline` 2026-09-18 (Brand Q3), verified same day.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 120, section "Bugs", position 41 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
