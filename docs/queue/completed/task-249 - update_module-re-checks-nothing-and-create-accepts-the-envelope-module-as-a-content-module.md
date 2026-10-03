---
id: TASK-249
title: >-
  update_module re-checks nothing, and create accepts the envelope module as a
  content module
status: Done
assignee:
  - '@claude'
created_date: '2026-10-03 17:08'
updated_date: '2026-10-03 17:25'
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
- [x] #1 A module update to a type its variant's channel does not accept is refused
- [x] #2 Creating or updating a module to the channel's envelope type through the module routes is refused; the envelope is written only through the variant
- [x] #3 The module limit is counted the same way on create and in the composition read
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. _refuse_module_type(channel, type) in backend/app/campaigns/service.py: the channel must declare the type, and it must not be the channel's envelope type; called by create (replacing its inline check) and, newly, by update.
2. The module limit on create counts non-envelope modules, as campaign_composition does.
3. Two test fixtures (test_frame.py, test_read_models.py) built their header through create_module_for_variant; they now use set_envelope_fields.
4. Tests in backend/tests/test_module_types.py, mutation-checked; dev database checked for rows the rule would refuse.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-03. Reproduced first: 5 of 7 new tests failed on the old code (envelope accepted on create; update took notification, an unknown type and header; with a limit of 1 the envelope used up the only place), 2 controls passed. Mutants: update unchecked (3 fail), envelope allowed (2), limit counting the envelope (1). Dev database (read-only check): no module of a type its channel lacks, no stray or doubled envelope module. Fixtures in test_frame.py and test_read_models.py moved to set_envelope_fields, so their header now sits at position 0 as in real data; no assertion depended on position 1. Full suite 1117 passed, rc 0.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A module's type is now checked against its channel on update as well as create, and the channel's envelope (email's header) can no longer be added or switched to as an ordinary module; subject and preheader go through the variant. The module limit counts the same modules on create as the composition read. Verified by 7 tests (5 reproduced as failures first), three mutants each caught, a dev-database check, and the full suite (1117 passed).
<!-- SECTION:FINAL_SUMMARY:END -->
