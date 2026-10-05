---
id: TASK-277
title: >-
  GET /content/{id}/versions answers an empty list instead of 404 for another
  brand's record
status: Done
assignee:
  - '@claude'
created_date: '2026-10-04 18:24'
updated_date: '2026-10-05 07:23'
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
- [x] #1 A record outside the working brand, or none at all, answers 404; a record with no versions answers an empty list
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-05.
- GET /content/{id}/versions checks the record against the working brand first and answers 404 like every other content route (ADR-172 point 6); a record of one's own with no versions still answers [].
- Test in test_brand_boundary.py: another brand's record gives 404, a missing one 404, one's own with none gives 200 []. It failed before the fix (200 == 404); an always-404 mutant fails it too.
- Results: backend 1270 passed; check:contract clean (status code only).
- Live through the React dev proxy: record 65 answers 200 with versions [2, 1]; record 999999999 answers 404.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The version list answers 404 for a record outside the brand or not there, like every other content route, and [] only for one's own record with no versions. Reproduced by a failing test first, an always-404 mutant caught, full suite green, checked live.
<!-- SECTION:FINAL_SUMMARY:END -->
