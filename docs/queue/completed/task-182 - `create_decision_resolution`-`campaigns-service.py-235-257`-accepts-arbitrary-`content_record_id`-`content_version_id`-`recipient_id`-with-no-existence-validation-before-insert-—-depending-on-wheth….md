---
id: TASK-182
title: >-
  `create_decision_resolution` (`campaigns/service.py:235-257`) accepts
  arbitrary `content_record_id`/`content_version_id`/`recipient_id` with no
  existence validation before insert — depending on wheth…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 504600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `create_decision_resolution` (`campaigns/service.py:235-257`) accepts arbitrary `content_record_id`/`content_version_id`/`recipient_id` with no existence validation before insert — depending on whether the DB engine enforces FK constraints (often off by default in SQLite), a bad ID silently creates an orphaned resolution row that only breaks later, at rendering's join-based lookup. Fix: no orphan row should ever be silently accepted — validate referenced IDs exist before insert (or ensure FK enforcement is actually on, e.g. `PRAGMA foreign_keys=ON` for SQLite) and return a clear error otherwise. Worth checking whether other `create_*` functions across the codebase have the same silent-orphan gap once this is fixed, since it's likely a systemic pattern, not unique to this one function. Source: [[Interview Prep - Content, Campaigns, Audience]] → Campaigns Q5. **Done 2026-07-12** — validates `decision_slot_id`, `content_record_id`, and (if given) `content_version_id`/`recipient_id` all exist before insert, applied at the function level so it protects both the direct API endpoint and the internal decision-execution path. Verified live: bad `content_record_id` rejected with a clear message; the internal execute-decision-slot path still works unaffected.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 593, section "Done", position 46 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
