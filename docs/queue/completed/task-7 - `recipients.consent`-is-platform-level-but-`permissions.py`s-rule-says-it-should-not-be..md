---
id: TASK-7
title: >-
  `recipients.consent` is platform-level, but `permissions.py`'s rule says it
  should not be.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-09-29 18:03'
labels:
  - backend
dependencies: []
priority: p1
type: bug
ordinal: 100700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P1. A stated rule whose own worked example contradicts it, and the row in question is the compliance record.** **`recipients.consent` is platform-level, but `permissions.py`'s rule says it should not be.** That rule reads: *"a permission is brand-scoped if the rows it guards carry a `brand_id`"*, and the comment excluding this key says "recipients carry no brand" — true when written, **false since ADR-163's addendum made `consent_events.brand_id` NOT NULL** (`migrate_0008`). **Consequence:** `policy.py` maps `/recipients/{external_id}/consent` to `RECIPIENTS_CONSENT`, `_permitted` takes the non-scoped branch, so a Manager granted `recipients.consent` on brand A can write a consent row for brand B — the record [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §7 calls the answer to a UWG §7 complaint. **Either answer is defensible; the silence is not.** Consent capture may genuinely be platform-level — a CRM records that a person agreed, not that they agreed to one brand's copy of themselves — in which case add it as a second acknowledged exception beside `ai.run`, with its reason. Otherwise move it into `BRAND_SCOPED`. `ai.run` proves the file already has a way to record an exception. Source: [[Interview Prep - Brand Boundary]] → Q3.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 43, section "Bugs", position 7 in that section (top = do next). The description is the original entry, verbatim.

ALREADY FIXED before this entry was migrated — found 2026-09-29. Commit 18d3de7 (2026-09-20) moved recipients.consent into BRAND_SCOPED (backend/app/auth/permissions.py) and recorded it as ADR-150's addendum of 2026-09-20 ('recipients.consent moves to brand-scoped'). The route checks the declared brand like any brand-scoped write, and the body's brand_id must agree with it or the request is refused with 409 and no consent event is written. The migration of docs/backlog.md on 2026-09-27 carried this entry over as open because the old file still listed it — a stale entry, not a live bug.

Verified, not assumed: removing RECIPIENTS_CONSENT from BRAND_SCOPED fails test_brand_boundary.py::TestAConsentRecordLandsOnTheBrandItWasAuthorisedFor::test_holding_the_permission_on_another_brand_is_not_holding_it_here (the exact scenario this entry describes) and test_permission_split.py's classification test; the 409 case is asserted at test_brand_boundary.py:811 with a check that no consent row was written. No code change needed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
No change needed: fixed by 18d3de7 on 2026-09-20, a week before this entry was migrated as open. recipients.consent is brand-scoped, a declared/body brand disagreement is a 409, and ADR-150 carries the addendum. Confirmed by mutation — reverting the classification fails the cross-brand test that describes this bug.
<!-- SECTION:FINAL_SUMMARY:END -->
