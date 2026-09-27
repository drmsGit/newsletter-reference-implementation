---
id: TASK-111
title: >-
  `hero` becomes `cms: true` and whatever sits in existing `module_data` for
  hero instances stops being read.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: chore
ordinal: 206400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Chore] — a flag flip that orphans data. Found 2026-09-25 while closing [[Variant Editor - design interview]] question 1.8.** **`hero` becomes `cms: true` and whatever sits in existing `module_data` for hero instances stops being read.** Rendering branches on `manifest.cms` (`backend/app/rendering/service.py:162`) to decide whether variables come from `module_data` or from a content record, so flipping the flag in `storage/modules/email/hero.json` silently changes where every existing hero module looks — the old values stay in the column and render nowhere. **It is a manifest change *and* a data migration**, and the migration direction is unusual: existing `module_data` must become content records, which means inventing a title and a brand for each. **Why it is being done:** question 1.8 settled that catalogue binding follows topical signal, and `hero` is a headline plus body copy about a subject — so its invisibility to the recipient affinity profile is a real defect rather than a tidiness complaint. `header` and `cta` stay `cms: false` deliberately and need no migration.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 372, section "Features", position 64 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
