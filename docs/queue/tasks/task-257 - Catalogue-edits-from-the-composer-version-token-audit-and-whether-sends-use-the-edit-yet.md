---
id: TASK-257
title: >-
  Catalogue edits from the composer: version token, audit, and whether sends use
  the edit yet
status: To Do
assignee: []
created_date: '2026-10-03 18:27'
labels:
  - backend
dependencies: []
documentation:
  - >-
    docs/architecture/interview-prep/Campaign Write Surface - final design
    pass.md
type: feature
ordinal: 200057
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Slice 6 of [[Campaign Write Surface - final design pass]] (2026-10-03). ADR-178 point 1: an edit made while composing lands in the content record. The editor saves on blur (D1), but `content_records` has no `updated_at`, so two managers editing one record silently overwrite each other; `PATCH /content/{id}` (`backend/app/content/router.py:165`) is not audited (ADR-153 point 4); and a send uses the record's latest published version (`resolve_renderable_content`, `backend/app/rendering/service.py:567-618`), so an edit reaches the next send only once republished. User decision 2026-10-03 (design pass D5): the editor shows "changed since last published — sends still use version N" with a one-click Publish, rather than publishing automatically. That needs the record to say whether its live content differs from its latest version.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 content_records gains updated_at (migration), and PATCH /content/{id} takes If-Match and answers 409 when stale
- [ ] #2 Content edits and publishing a version are audited
- [ ] #3 The record detail read says the latest published version number and whether the live content differs from it
<!-- AC:END -->
