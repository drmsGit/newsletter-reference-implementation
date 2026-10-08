---
id: TASK-108
title: A section-heading module.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-10-08 18:26'
labels:
  - backend
dependencies: []
type: feature
ordinal: 206100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — a module type that does not exist, and the smallest possible test of ADR-160 point 6's two-file claim. Raised by the user 2026-09-25.** **A section-heading module.** Structural punctuation that divides an email into areas — in the family of `divider`, not of `hero`, which is editorial content. `storage/modules/email/` currently holds six manifests (`header`, `hero`, `cta`, `img_left`, `img_right`, `single_stack`) and nothing that says *"a new section starts here"*. Surfaced while answering [[Variant Editor - design interview]] question 1.3, where the user corrected a misreading: *"with headlines i didn't mean hero. Headlines can be necessary to separate different areas within an email. It's a module type that doesn't exist yet in code."* **Cheap by design and that is the point:** [[ADR-160 — Channel Model and Composition]] point 6 chose "a channel manifest plus a provider adapter — two files, no config step", and a heading module is a `.json` plus a `.html` with no code change anywhere. If it turns out to need more than two files, that is a finding about the seam rather than about headings. **Sequence with interview question 1.8** (which modules should be catalogue-bound) — a heading is almost certainly `cms: false`, but that answer falls out of 1.8 rather than being assumed here.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 366, section "Features", position 61 in that section (top = do next). The description is the original entry, verbatim.

2026-10-08, from the task-228 interview (ADR-086 addendum of that date): the floor skips a recipient when nothing but the envelope rendered, and there is no "decorative" marker on modules because no decorative module existed. A section heading is the first one: an email holding only the envelope module and a section heading must still count as "nothing to show", or it ships with nothing in it. So this task decides the manifest marker for structural modules (a key added to MANIFEST_KEYS in backend/app/modules/registry.py, read by what_rendered in backend/app/rendering/frame.py), together with the visible header and footer task filed the same day. On the user's question whether a module is a plain .html drop: no, a module needs its .json manifest beside the .html (an .html alone is skipped with a warning, registry.py _discover); with a minimal manifest (label, channel, cms false, no fields) it appears in the editor with no code change.
<!-- SECTION:NOTES:END -->
