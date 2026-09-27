---
id: TASK-19
title: >-
  `delete_brand`'s `holders` dict counts five tables; there are seven NOT NULL
  brand foreign keys.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 101900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P2. A hand-kept list that two schema changes have already walked past.** **`delete_brand`'s `holders` dict counts five tables; there are seven NOT NULL brand foreign keys.** `auth/service.py:201-207` covers `content_records`, `campaigns`, `audience_groups`, `send_instances` and `role_assignments`. Missing: `consent_events.brand_id` (`recipients/db_models.py:57`, added by `migrate_0008` **after** the guard was written) and `integration_grants.brand_id` (`auth/db_models.py:298`, added with ADR-166's machine principals). **Consequence, stated exactly:** no data is lost — the transaction fails. What is lost is the clean refusal. A brand that only ever captured consent, or only ever held a machine grant, reaches the `delete()` and raises an unhandled `IntegrityError` instead of the sentence naming what blocks it, which is the entire job of the guard. **Fix:** derive the holders from the schema rather than maintaining the list by hand. Adding the two missing entries fixes today and not the pattern — the brand page already states this maintenance rule and two tables have been added without following it. Source: [[Interview Prep - Brand Boundary]] → Q7.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 74, section "Bugs", position 19 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
