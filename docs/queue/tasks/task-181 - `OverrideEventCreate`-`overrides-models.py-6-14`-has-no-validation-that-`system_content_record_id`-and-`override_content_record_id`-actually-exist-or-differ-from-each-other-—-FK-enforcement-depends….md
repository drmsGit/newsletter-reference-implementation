---
id: TASK-181
title: >-
  `OverrideEventCreate` (`overrides/models.py:6-14`) has no validation that
  `system_content_record_id` and `override_content_record_id` actually exist or
  differ from each other — FK enforcement depends…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 504500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `OverrideEventCreate` (`overrides/models.py:6-14`) has no validation that `system_content_record_id` and `override_content_record_id` actually exist or differ from each other — FK enforcement depends on whether `PRAGMA foreign_keys` happens to be on for the dev DB, so a bad ID silently creates an orphaned audit row. Same systemic silent-orphan pattern as Campaigns Q5 below. Fix: validate both referenced IDs exist (and aren't identical) before insert. Source: [[Interview Prep - Decision, Overrides, Insight]] → Overrides Q2. **Done 2026-07-12.** Verified live: same-ID override rejected, nonexistent content record rejected, both with clear messages.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 591, section "Done", position 45 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
