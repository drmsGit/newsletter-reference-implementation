---
id: TASK-174
title: >-
  `ModuleInstanceDB` has both `content_record_id` and `decision_slot_id` as
  independent nullable FKs with nothing enforcing mutual exclusivity — if both
  are set, rendering silently prefers `content_rec…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 503800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `ModuleInstanceDB` has both `content_record_id` and `decision_slot_id` as independent nullable FKs with nothing enforcing mutual exclusivity — if both are set, rendering silently prefers `content_record_id` and ignores the decision slot (`rendering/service.py:196-205`); if neither is set, the module renders nothing. Considered replacing with a generic `type`+`id` polymorphic column but rejected — that's a known anti-pattern that loses real FK referential integrity and forces conditional/manual joins, for a type-count (2) too small to justify it. Fix: keep the two nullable FK columns, add a mutual-exclusivity constraint (DB `CHECK` or Pydantic/service-layer validator) enforcing exactly one is set. `campaigns/db_models.py:37-53`, `models.py:50-55`. Source: [[Interview Prep - Content, Campaigns, Audience]] → Campaigns Q2. **Done 2026-07-12** — implemented as **mutual exclusivity** ("never both"), not literally "exactly one required" as the fix text said: real seed data (the `cta` module) legitimately leaves both null (module_data-only, no CMS content), so requiring exactly one would have broken working functionality. A DB `CHECK` (`content_record_id IS NULL OR decision_slot_id IS NULL`) plus a service-layer validator now reject only the genuinely ambiguous both-set case. Verified live: both-set rejected with a clear message, neither-set (static module) still works.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 577, section "Done", position 38 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
