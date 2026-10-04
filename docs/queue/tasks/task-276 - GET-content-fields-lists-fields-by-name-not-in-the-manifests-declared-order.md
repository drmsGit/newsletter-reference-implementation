---
id: TASK-276
title: 'GET /content/fields lists fields by name, not in the manifests'' declared order'
status: To Do
assignee: []
created_date: '2026-10-04 18:24'
labels:
  - backend
dependencies: []
type: bug
ordinal: 104700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found 2026-10-04 by the task-274 design session, verified that day; filed as a bug ahead of the content write-surface build, at the user's choice.

The Manager Workflow interview decided that a record's fields appear "in the manifest's declared order", with required fields not sorted to the top ([[Manager Workflow - design interview]] Q2 rider, lines 492-499; the same section decided labelled sections down the page, not tabs, lines 478-491). `GET /content/fields` returns them **sorted by name** instead: `catalogue_fields` in `backend/app/content/service.py`, `for name in sorted(in_catalogue)` at line 223. The new content screen groups that list by `channel`, so every section would show fields alphabetically: body before headline, button before image.

The open point the fix must settle: a field can appear in several manifests (hero, img_left, img_right and single_stack each declare their own order), so "the manifest's declared order" needs a rule for the union. One candidate is first appearance, walking the manifests in a fixed order. Put it to the user if it is not obvious.

Related: `content_field_groups()` (`service.py:106-145`) requires `var.channel` while `catalogue_fields` does not. So a content field with no declared channel would be listed by `/content/fields` but be in no group, and PATCH would never write it. Today every field declares one; a test asserting that both agree would keep it so.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 GET /content/fields returns fields in the manifests' declared order, by a rule stated in the code
- [ ] #2 A test pins the order and that every listed field is in a channel group
<!-- AC:END -->
