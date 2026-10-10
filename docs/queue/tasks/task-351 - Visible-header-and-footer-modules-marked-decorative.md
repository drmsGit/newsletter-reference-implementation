---
id: TASK-351
title: 'Visible header and footer modules, marked decorative'
status: To Do
assignee: []
created_date: '2026-10-10 21:17'
updated_date: '2026-10-10 21:19'
labels:
  - backend
  - frontend
dependencies:
  - TASK-349
type: feature
ordinal: 200980
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Nothing a recipient sees at the top or bottom of an email exists as a module: the email modules are cta, editorial, header (the envelope), hero, img_left, img_right and single_stack.

Decided by the user 2026-10-10 (task-301, ADR-193 points 1, 4 and 5):
- The designed visible header (a logo) and footer (links, special texts) are ordinary modules a manager places. Several footer variants per brand are several footer modules.
- Their content comes from content records, which already belong to one brand.
- Their manifests declare "decorative": true, and task-228's nothing-to-show check ignores decorative modules: an email holding only those plus the envelope still counts as nothing to show (ADR-086, 2026-10-08 addendum).
- The header's logo is an https URL in its content for now, and an asset id once task-112 exists.

Depends on the envelope rename (the name header must be free). Third of three build tasks from task-301. task-108's section heading will use the same flag.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A header module (logo) and a footer module can be placed in an email variant
- [ ] #2 Their manifests declare decorative: true
- [ ] #3 An email holding only decorative modules and the envelope is skipped as nothing to show
- [ ] #4 The header's logo field accepts an https URL
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10, from writing ADR-193: the url field type has no server-side https check. The only check is the editor's <input type=url> (frontend/src/components/EditorFields.tsx around :66), which accepts any scheme. 'The logo is an https URL' therefore needs enforcing here (or in the field model) for the header's logo field.
<!-- SECTION:NOTES:END -->
