---
id: TASK-249
title: >-
  update_module re-checks nothing, and create accepts the envelope module as a
  content module
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
ordinal: 100200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Defect 2 of the campaign write surface final-design pass, 2026-10-03. `create_module_for_variant` checks the type against the variant's channel (`backend/app/campaigns/service.py:505`), but `update_module` (`:552-583`) overwrites `module_type` with no check at all: a PUT can turn a module into another channel's type, an unknown type, or the envelope type. Create, meanwhile, accepts the channel's envelope type (`envelope_module_type`, `backend/app/modules/registry.py:281`) as an ordinary content module, appended at the end, where `set_envelope_fields` (`service.py:408`) never looks. The composition read hides envelope types from `accepted_module_types` (`service.py:1063-1066`) and the Jinja picker filters them (`frontend/router.py:972-980`), but a dropdown is not a control: the same argument the channel check's own comment makes. Related: the channel module limit is counted over all modules on create (`service.py:517-521`) but over non-envelope modules in the composition read (`:1061`); harmless today because no channel has both a limit and an envelope.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A module update to a type its variant's channel does not accept is refused
- [ ] #2 Creating or updating a module to the channel's envelope type through the module routes is refused; the envelope is written only through the variant
- [ ] #3 The module limit is counted the same way on create and in the composition read
<!-- AC:END -->
