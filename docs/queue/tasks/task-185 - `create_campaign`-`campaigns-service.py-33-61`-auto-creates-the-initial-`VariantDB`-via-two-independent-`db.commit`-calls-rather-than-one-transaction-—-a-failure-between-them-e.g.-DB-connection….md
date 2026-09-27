---
id: TASK-185
title: >-
  `create_campaign` (`campaigns/service.py:33-61`) auto-creates the initial
  `VariantDB` via two independent `db.commit()` calls rather than one
  transaction — a failure between them (e.g. DB connection…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 504900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `create_campaign` (`campaigns/service.py:33-61`) auto-creates the initial `VariantDB` via two independent `db.commit()` calls rather than one transaction — a failure between them (e.g. DB connection drop) leaves a persisted campaign with zero variants, violating the "a campaign always has a variant" invariant. Fix: wrap both inserts in a single transaction (flush + one commit at the end) so it's atomic. Source: [[Interview Prep - Content, Campaigns, Audience]] → Campaigns Q1. **Done 2026-07-12** — `db.flush()` after the campaign insert (assigns the id without ending the transaction), then one `db.commit()` for both rows.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 599, section "Done", position 49 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
