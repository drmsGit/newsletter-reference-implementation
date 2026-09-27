---
id: TASK-151
title: >-
  Redesign content schema: move full CMS content fields onto `ContentRecordDB`
  as a `content` JSON column (same shape as `ContentVersionDB.content`, e.g.
  `headline_medium`/`body_medium`), so record cre…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 501500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Feature]** Redesign content schema: move full CMS content fields onto `ContentRecordDB` as a `content` JSON column (same shape as `ContentVersionDB.content`, e.g. `headline_medium`/`body_medium`), so record creation/editing carries the real renderable content directly instead of requiring a separate "create version" step to enter it. Keep `title` (+ short `description`) as metadata columns for catalog listing/filtering. "Create version" becomes a freeze/snapshot action (stand-in for future publish) that copies the record's current `content` into an immutable `ContentVersionDB` row for audit/rollback (ADR-128) — not a "now type your content" step. Also resolves the root cause of the hardcoded `headline_medium`/`body_medium` alias patch in `rendering/service.py` (record and version will finally share one content shape). Source: [[Interview Prep - Content, Campaigns, Audience]] → Content Q1. **Done 2026-07-12** — `body` column dropped in favor of `content` JSON + `description`; content-entry forms updated to match; verified live via a real `img_left` module render pulling `headline_medium`/`body_medium`/`button_label`/`button_url` from the new column.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 531, section "Done", position 15 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
