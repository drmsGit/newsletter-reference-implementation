---
id: TASK-250
title: 'POST /campaigns/{id}/variants silently drops subject and preheader'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-03 17:08'
updated_date: '2026-10-03 17:39'
labels:
  - backend
dependencies: []
documentation:
  - >-
    docs/architecture/interview-prep/Campaign Write Surface - final design
    pass.md
type: bug
ordinal: 100300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Defect 3 of the campaign write surface final-design pass, 2026-10-03. `VariantCreate` accepts `subject` and `preheader` (`backend/app/campaigns/models.py:24`), but the JSON route (`backend/app/campaigns/router.py:159-166`) never passes them to `create_variant_for_campaign`, so they are lost without an error. The Jinja route passes them, stripped (`frontend/router.py:1341-1370`). The JSON variant routes also do not strip whitespace, and `set_envelope_fields` drops only falsy values, so `" "` would be stored as a subject. The React client's "blank variant" action (slice 5 of the pass) uses this route.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A variant created over JSON with subject and preheader reads them back from the composition
- [x] #2 Whitespace-only subject or preheader is treated as empty on create and update, on both planes
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. The JSON variant-create route passes subject and preheader to create_variant_for_campaign.
2. set_envelope_fields trims string values and drops what is then empty; every path (JSON create/update, Jinja forms, AI apply-subject) writes the envelope through it.
3. Tests in backend/tests/test_variant_envelope.py, mutation-checked.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-03. Reproduced first: 3 of 4 new tests failed (fields dropped on create; whitespace kept on create and on update). Mutants: route not passing the fields (2 fail), no trimming (2). Full suite 1121 passed, rc 0. The Jinja routes' own .strip() stays (harmless). Not touched: the stale docstring of create_variant_for_campaign ('stay on the row for now'), which is task-43's.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A variant created over JSON keeps its subject and preheader, and a whitespace-only value is empty on every path, because trimming moved into set_envelope_fields. Verified by 4 tests (3 reproduced as failures first), two mutants caught, full suite 1121 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
