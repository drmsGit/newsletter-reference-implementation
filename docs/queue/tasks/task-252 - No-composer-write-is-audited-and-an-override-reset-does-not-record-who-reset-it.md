---
id: TASK-252
title: >-
  No composer write is audited, and an override reset does not record who reset
  it
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
ordinal: 100500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Defect 5 of the campaign write surface final-design pass, 2026-10-03. [[ADR-153 — Audit and Accountability]] point 4 makes writes the floor. Only the two duplicates are audited today (`backend/app/campaigns/router.py:659`, `:721`). Campaign and variant create, variant edit, module create/update/delete/move, slot create/update and override create/reset write nothing, on either plane. `reset_content_override` (`backend/app/overrides/service.py:158`) sets `active=False` and `reverted_at` and keeps no actor. The pass decided (D2, user 2026-10-03) to keep the hard delete of a module's overrides (`campaigns/service.py:596-600`) and to make the history survive in the audit log instead: override create and reset are audited with the fields and values involved, and a module delete names every override it removed with its `field_overrides`. The override-history screen (Variant Editor interview 3.5) reads the audit log. The pass also chose autosave on blur (D1), so these entries will be frequent; that cost was accepted.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each composer write named above records an audit event with the actor and the target, on both planes
- [ ] #2 Override create and reset record the fields and values; reset records who reset it
- [ ] #3 Deleting a module records every override it removed, with its field_overrides
<!-- AC:END -->
