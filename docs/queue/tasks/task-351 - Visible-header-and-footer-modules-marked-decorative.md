---
id: TASK-351
title: >-
  Visible header and footer modules render from the brand profile, marked
  decorative
status: To Do
assignee: []
created_date: '2026-10-10 21:17'
updated_date: '2026-10-11 08:39'
labels:
  - backend
  - frontend
dependencies:
  - TASK-350
type: feature
ordinal: 200980
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Slice 3 of 5 of the brand-profile design (ADR-194, 2026-10-11; it supersedes ADR-193, which first described these modules with content from content records).

The visible header (logo, menu links) and footer (links, service hotline, footer texts) are modules a manager places in an email, or leaves out. They render from the variant's brand profile, so switching the profile switches them. The footer module adds one optional per-email free text for a special note. The fixed legal line is appended by the frame regardless (slice 1, task-350).

Their manifests declare "decorative": true, and the nothing-to-show check (task-228; ADR-086's 2026-10-08 addendum) ignores decorative modules: an email holding only decorative modules plus the envelope still counts as nothing to show. The header's logo is a profile image field, an https URL until asset management exists (task-112).

The name `header` is free since task-349. Version-1 frames still read their `header` as the envelope, keyed on the frame version, so the new visible `header` lives only in version-2 frames. Codex's test_envelope_frame_boundaries.py already pins that boundary with a stand-in module.

Depends on task-350 (the profile).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A header module (logo, menu) and a footer module render from the variant's brand profile
- [ ] #2 The footer module carries one optional per-email free text
- [ ] #3 Their manifests declare decorative: true, and an email holding only decorative modules and the envelope is skipped as nothing to show
- [ ] #4 An old version-1 frame still renders and reconstructs as sent
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10, from writing ADR-193: the url field type has no server-side https check. The only check is the editor's <input type=url> (frontend/src/components/EditorFields.tsx around :66), which accepts any scheme. 'The logo is an https URL' therefore needs enforcing here (or in the field model) for the header's logo field.

2026-10-11: rescoped by the brand-profile design session (ADR-194 supersedes ADR-193). The original description, kept verbatim:

**[Feature]** Nothing a recipient sees at the top or bottom of an email exists as a module: the email modules are cta, editorial, header (the envelope), hero, img_left, img_right and single_stack.

Decided by the user 2026-10-10 (task-301, ADR-193 points 1, 4 and 5):
- The designed visible header (a logo) and footer (links, special texts) are ordinary modules a manager places. Several footer variants per brand are several footer modules.
- Their content comes from content records, which already belong to one brand.
- Their manifests declare "decorative": true, and task-228's nothing-to-show check ignores decorative modules: an email holding only those plus the envelope still counts as nothing to show (ADR-086, 2026-10-08 addendum).
- The header's logo is an https URL in its content for now, and an asset id once task-112 exists.

Depends on the envelope rename (the name header must be free). Third of three build tasks from task-301. task-108's section heading will use the same flag.
<!-- SECTION:NOTES:END -->
