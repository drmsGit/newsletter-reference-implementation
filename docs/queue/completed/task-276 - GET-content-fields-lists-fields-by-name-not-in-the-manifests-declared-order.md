---
id: TASK-276
title: 'GET /content/fields lists fields by name, not in the manifests'' declared order'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-04 18:24'
updated_date: '2026-10-05 07:19'
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
- [x] #1 GET /content/fields returns fields in the manifests' declared order, by a rule stated in the code
- [x] #2 A test pins the order and that every listed field is in a channel group
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-05.
The union rule, decided with the user that day: merged so every module's own order holds, modules walked by channel then module name. Each new field goes right after its predecessor in its own module; failing that, before the next placed field of its module; failing both, at the end. Where modules disagree, the first one wins.
- content.service.merge_declared_orders, used by catalogue_fields. Email now reads: Hero headline, Hero button text, Image (URL), Image description (alt text), Headline, Body text, Button text, Button link; then push.
- The React record page (ContentDetail.tsx) lists a record's fields in that order, undefined keys last. Done now so the change is visible before task-279.
- Tests: the route's order pinned; every listed field is in a channel group; the merge rule on its own (shared last field stays last, after predecessor, disagreement first wins, no duplicates); a client test for the order. Mutation-checked against 6 mutants, each caught.
- Results: backend 1269 passed; client tsc clean, vitest 145 passed, check:contract clean.
- Checked live in the React client: record 65 lists Hero headline, Image (URL), Headline, Body text, Button text, Button link. The variant editor (campaign 4, variant 4A) still loads its catalogue act, which is also the React check for task-275's PATCH change.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
GET /content/fields returns fields in the modules' declared order, merged so every module's order holds (the user's rule, 2026-10-05), and the React record page lists them so. Verified by route, rule and client tests mutation-checked against 6 mutants, both suites, the contract check and a live look at record 65.
<!-- SECTION:FINAL_SUMMARY:END -->
