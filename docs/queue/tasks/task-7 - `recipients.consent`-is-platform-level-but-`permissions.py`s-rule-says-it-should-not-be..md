---
id: TASK-7
title: >-
  `recipients.consent` is platform-level, but `permissions.py`'s rule says it
  should not be.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
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
<!-- SECTION:NOTES:END -->
