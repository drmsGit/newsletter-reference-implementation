---
id: TASK-149
title: >-
  `get_content_record_by_id` (`content/router.py:43-49`) hand-rolls its own
  `ContentRecordDB` → `ContentRecord` mapping (plus an unnecessary local
  re-import of `ContentRecord`) instead of using a share…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 501300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `get_content_record_by_id` (`content/router.py:43-49`) hand-rolls its own `ContentRecordDB` → `ContentRecord` mapping (plus an unnecessary local re-import of `ContentRecord`) instead of using a shared mapper — duplicates the same mapping already in `list_content_records`/`update_content_record` (`service.py:17-25,28-39`). Fix: extract a `to_content_record(record) -> ContentRecord` helper in `service.py` (mirroring the existing `to_content_version`/`to_category_relation` pattern) and use it in all three places. Small cleanup. Source: [[Interview Prep - Content, Campaigns, Audience]] → Content Q4. **Done 2026-07-12.**
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 527, section "Done", position 13 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
