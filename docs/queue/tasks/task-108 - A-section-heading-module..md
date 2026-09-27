---
id: TASK-108
title: A section-heading module.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
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
<!-- SECTION:NOTES:END -->
