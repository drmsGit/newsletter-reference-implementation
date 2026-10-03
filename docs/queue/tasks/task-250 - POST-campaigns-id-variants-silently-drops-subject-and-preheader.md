---
id: TASK-250
title: 'POST /campaigns/{id}/variants silently drops subject and preheader'
status: To Do
assignee: []
created_date: '2026-10-03 17:08'
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
- [ ] #1 A variant created over JSON with subject and preheader reads them back from the composition
- [ ] #2 Whitespace-only subject or preheader is treated as empty on create and update, on both planes
<!-- AC:END -->
