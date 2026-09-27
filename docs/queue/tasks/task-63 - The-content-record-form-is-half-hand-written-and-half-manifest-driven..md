---
id: TASK-63
title: The content-record form is half hand-written and half manifest-driven.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 201600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — a generalisation deferred on purpose, not an oversight.** **The content-record form is half hand-written and half manifest-driven.** Email's six fields are hardcoded in `content.html`, `content_detail.html` and both routes, with labels and placeholders written by hand. Every *other* channel's fields are generated from its module manifest (`_channel_authoring_sections`), using the `label` a manifest variable may now declare. Adding push on 2026-09-17 took the generated path because writing a second hand-written block would have been the third place channel fields live.

  **Why email was not converted with it.** A manifest variable carries `name`, `required` and now `label` — it does not carry a placeholder, a field type (textarea vs input), an ordering, or the "Supports **bold** and [links](…)" help text that `body_medium` has today. Generating email's form from the manifest as it stands would visibly degrade the authoring surface people actually use. The generalisation therefore needs the manifest format extended first, and that is a change to a file format five modules already use.

  **Also unresolved, and the reason this is worth doing eventually:** FastAPI needs form parameters spelled out, so `PUSH_CONTENT_FIELDS` in `frontend/router.py` is a hand-written list beside the manifest. A test asserts the two agree, which turns drift into a failure rather than a silent dropped field — but the test exists *because* the duplication does. A form driven end-to-end by manifests would not need either. Source: 2026-09-17, while adding push authoring at the user's prompt.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 186, section "Features", position 16 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
