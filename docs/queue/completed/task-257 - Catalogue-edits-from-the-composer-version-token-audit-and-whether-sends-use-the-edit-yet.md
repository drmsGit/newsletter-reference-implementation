---
id: TASK-257
title: >-
  Catalogue edits from the composer: version token, audit, and whether sends use
  the edit yet
status: Done
assignee:
  - '@claude'
created_date: '2026-10-03 18:27'
updated_date: '2026-10-03 18:36'
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
- [x] #1 content_records gains updated_at (migration), and PATCH /content/{id} takes If-Match and answers 409 when stale
- [x] #2 Content edits and publishing a version are audited
- [x] #3 The record detail read says the latest published version number and whether the live content differs from it
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Migration 0029: content_records.updated_at (timestamptz, NOT NULL, default now()); applied before any model edit (ADR-181).
2. ContentRecordDB.updated_at with onupdate; ContentRecord carries it.
3. update_content_record takes expected_updated_at (refuse_stale); PUT and PATCH /content/{id} take If-Match, 409 when stale.
4. Audit content.updated (JSON PUT/PATCH and the Jinja edit form) and content.published (JSON and Jinja publish).
5. POST /content/versions takes the author from the principal, never the body (the task-243 rule; found 2026-10-03).
6. GET /content/{id} answers a ContentRecordDetail: latest_version_number and unpublished_changes (live content differs from the latest version, or no version yet).
7. Tests, mutation-checked; client types regenerated.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-03. Migration 0029 written and applied to the dev database before the model changed (schema check: up to date). Built: ContentRecordDB.updated_at; refuse_stale in update_content_record; If-Match on PUT and PATCH /content/{id}; audit content.updated (JSON PUT/PATCH, Jinja edit) and content.published (JSON and Jinja publish); GET /content/{id} now answers ContentRecordDetail with latest_version_number and unpublished_changes (publish_state in content/service.py). Also fixed: POST /content/versions and the Jinja publish form took the version's author from the request (body field / a 'Created by' input); both now use the signed-in principal, and the input is gone from content_detail.html. Tests backend/tests/test_content_edits.py (5); mutants: no version check, never unpublished, PATCH unaudited, author unset, Jinja publish unaudited: each caught. Full suite 1179 passed, rc 0; client types regenerated, 88 client tests. Found on the way: the test database is rebuilt from the models only after test modules import main, and main queries content_records at import (create_demo_content_if_empty), so a new column on that table breaks the next test run once; applied 0029 to the test database by hand and flagged the gap separately.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Content records now have a version token (migration 0029) checked on PUT/PATCH with If-Match; catalogue edits and publishing are audited on both planes; the record detail says the latest published version and whether the live content differs from it; and a version's author is the caller, never the request. Verified by 5 tests and five mutants, full suite 1179 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
