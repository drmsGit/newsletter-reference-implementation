---
id: TASK-277
title: >-
  GET /content/{id}/versions answers an empty list instead of 404 for another
  brand's record
status: To Do
assignee: []
created_date: '2026-10-04 18:24'
labels:
  - backend
dependencies: []
type: bug
ordinal: 104800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found 2026-10-04 by the task-274 design session, verified that day; a small inconsistency filed at the user's choice ahead of the content write-surface build, which reads this route for its version list.

`GET /content/{content_id}/versions` (`get_content_versions`, `backend/app/content/router.py:396-405`) is brand-scoped through a join, so it leaks nothing. But for a record outside the working brand, or one that does not exist, it answers `200 []` where every other content route answers 404 (for example `GET /content/{id}` at `router.py:148-152`). A client cannot tell "no versions yet" from "not yours / not there", and the new screen's version list would quietly show "No versions" for a mistyped id. Answer 404 the way `get_content_record` does, with a test for both cases.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A record outside the working brand, or none at all, answers 404; a record with no versions answers an empty list
<!-- AC:END -->
