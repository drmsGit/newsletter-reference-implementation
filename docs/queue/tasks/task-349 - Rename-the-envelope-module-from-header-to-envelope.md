---
id: TASK-349
title: Rename the envelope module from header to envelope
status: To Do
assignee: []
created_date: '2026-10-10 21:17'
updated_date: '2026-10-10 21:19'
labels:
  - backend
  - frontend
dependencies:
  - TASK-301
type: feature
ordinal: 200960
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** The email module that holds the subject and the preheader is code-named header: storage/modules/email/header.json and .html, with its fields marked "envelope": true in storage/fields.json. It renders only a hidden preheader span. The visible logo header decided in task-301 needs that name.

Decided by the user 2026-10-10 (task-301, ADR-193 point 6): rename the envelope module to envelope, so the visible module can be called header.

The final-design pass must settle what ADR-193 left open. Stored data names 'header':
- module rows in campaigns' variants;
- frames frozen in snapshots;
- delivery records that must stay readable as sent (ADR-183).

Either migrate them, or let every reader accept the old name too. Rewriting a frozen record changes what it says was sent, so choose with that in mind.

Also in scope: wherever code, the manager client or the docs say header for the envelope. Grep for module_type 'header' and the envelope module, and see the 2026-10-08 ADR-086 addendum's wording.

First of three build tasks from task-301: this, then the brand profile, then the visible header and footer modules.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The envelope module is called envelope in its manifest, its template and every code path
- [ ] #2 Snapshots and delivery records made before the rename still read and reconstruct as sent
- [ ] #3 The name header is free for the visible header module
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10, from writing ADR-193 (point 6 hazard, for the final-design pass): the renderer looks up each frozen frame entry's template by module_type (backend/app/rendering/frame.py around :269-278). So after the rename, an OLD frozen 'header' entry would resolve to the NEW visible logo header. Also, what_rendered (frame.py around :190-213) finds the envelope by its manifest attribute, not by name, so an old 'header' entry would then count as meaningful content and defeat the nothing-to-show floor. Either migrate the frozen entries, or map 'header' to the envelope when reading frames made before the rename.
<!-- SECTION:NOTES:END -->
