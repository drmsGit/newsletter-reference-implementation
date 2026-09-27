---
id: TASK-117
title: >-
  Nothing in the catalogue is ever hard-deleted, and this should probably be
  written down once rather than rediscovered per table.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - needs-adr
  - backend
dependencies: []
ordinal: 300100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
📋 **Nothing in the catalogue is ever hard-deleted, and this should probably be written down once rather than rediscovered per table.** Stated as a principle by the user 2026-09-27 while settling asset deletion: *"delete = hide from picker; similar as no deletion on content records or categories for example as those are woven into the affinity profiles (deleting would mean we can't interpret it)"*. **Three separate reasons converge on one rule.** An **asset** cannot be removed because emails sent months ago are in inboxes and fetch it on open — hard deletion retroactively breaks history that has already shipped. A **content record** and a **category** cannot be removed because recipient affinity profiles are built from engagement with them; delete the referent and the profile becomes uninterpretable numbers. **It is already implemented for content and named nowhere**: `CONTENT_STATUSES = ("active", "inactive")` (`backend/app/content/service.py:85`), whose comment says *"deactivation exists to stop a record being newly selected without breaking anything that already references it"* — which is exactly this rule, written as a local note about one table. **What "delete" means everywhere is therefore: stop it being newly selected, keep it resolvable.** Worth stating once because the alternative is each new table deciding independently, and one of them eventually deciding wrong — the failure is silent and only visible long afterwards, in an affinity profile nobody can explain or an email whose images stopped loading. **Sequence with the general data-lifecycle ADR**, which already owes a retention answer and is the natural home: retention and "never delete" are the same question from opposite ends, since storage that only grows needs an archival story rather than a deletion one.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 410, section "Needs ADR", position 1 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
