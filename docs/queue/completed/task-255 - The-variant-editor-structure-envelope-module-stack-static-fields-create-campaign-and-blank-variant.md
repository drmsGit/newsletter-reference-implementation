---
id: TASK-255
title: >-
  The variant editor, structure: envelope, module stack, static fields; create
  campaign and blank variant
status: Done
assignee:
  - '@claude'
created_date: '2026-10-03 18:05'
updated_date: '2026-10-03 18:15'
labels:
  - frontend
dependencies: []
documentation:
  - >-
    docs/architecture/interview-prep/Campaign Write Surface - final design
    pass.md
type: feature
ordinal: 200055
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Slice 5 of [[Campaign Write Surface - final design pass]], started 2026-10-03 at the user's request after slices 1-4 (task-248..253, task-110) made the write path safe. The React client could read the whole campaign loop and write almost none of it. This is the first editor screen: the variant edited on its own screen (Manager Workflow Q3), laid out as a module stack with a field editor beside it (Variant Editor 2.1), the envelope as a fixed area on top (VE 2.3), modules moved with arrows and the keyboard, never dragged (VE 1.5), and saving on blur (design pass D1) with the If-Match token from task-110. Creating a campaign and a blank variant (VE 5.1: duplicate stays primary) completes the structure. Catalogue-bound fields and overrides are slice 6, slots on modules slice 7, the preview overlay and the advisory lock (task-254) later.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A variant has its own editor screen, reached from campaign detail
- [x] #2 Subject and preheader (the channel's envelope fields) save on blur, with If-Match
- [x] #3 Modules can be added (only types the channel accepts, not past its limit), removed after a confirmation, and moved with buttons and Alt+Arrow keys
- [x] #4 A static module's fields form is generated from its manifest and saves on blur; a server refusal is shown on the field it names
- [x] #5 A stale save (409) is shown in place with a way to reload, and two saves to one module never refuse each other
- [x] #6 A campaign can be created from the campaign list and a blank variant from campaign detail
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. resources.ts: useModuleManifests(channel); mutations for variant save, module add/save/delete/move, campaign create, variant create. Saves read the entity token from the cached composition at send time, are serialised per entity with mutation scope, and write the returned updated_at back into the cache.
2. screens/VariantEditor.tsx at /campaigns/:id/variants/:variantId: envelope area, module stack (select, move, remove with inline confirm, add), field editor for the selected module. Catalogue-bound and slot-bound modules show what they are bound to and link there (editing them is slices 6 and 7).
3. Campaigns.tsx: new-campaign form (name, channel from settings.channels where available) that opens the new variant. CampaignDetail.tsx: an Edit link per variant and a secondary blank-variant form.
4. index.css: the two-column editor layout.
5. Tests per acceptance criterion, mutation-checked; browser check against the dev server.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-03. Built as planned, with two corrections found by the tests. (1) The first save hooks merged a field into the module data as it was when the field rendered, so a second quick save wrote the first field's old value back; the stateful stub server caught it. Saves now state only what changed and merge into the entity read from the cache when the save is sent. (2) A write-back of the saved version into the cache turned out redundant (each save's success waits for the composition re-read before the next queued save starts) and was removed after a mutant showed nothing depended on it. The race test first did not race (an await between the blurs); it now fires both blurs back to back, and removing the queue or the wait for the re-read each fails it. Tests: VariantEditor.test.tsx (11, against a stub server that keeps state and enforces If-Match like the real one), CampaignDetail.test.tsx (+2: create campaign, blank variant, editor link). Mutants caught: no queue, no wait for re-read, changes replacing the data, no token, saving unchanged fields, no remove confirmation. 88 client tests, tsc clean, contract clean. Browser (dev server, signed in as the dev account): editor renders Demo Campaign 1 / Variant 1A from live data; an autosave on the CTA label sent PUT with If-Match (200, version moved, url kept); a save after another writer's change got 409, showed 'Somebody changed the module…', and kept their value; the CTA label was restored to 'Explore' afterwards (the test writes left module.updated audit entries on module 4). Fixed from the screenshot: a field note equal to its label is no longer repeated; the stack column is wider. Pane was hidden, so interaction was driven through DOM events rather than clicks. Not built here, by slice: catalogue-bound fields and overrides (6), slots on modules (7), preview overlay, advisory lock (task-254), a shortcuts overlay (VE 1.5 asked for one; deferred).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The variant now has its own editor: envelope fields and a static module's manifest-generated fields save on blur with If-Match, modules are added (channel-accepted types, within the limit), removed after an inline confirmation and moved with buttons or Alt+Arrow; a stale save shows in place with 'Load their version', a refused field shows on that field, and quick successive saves never refuse each other. Campaigns and blank variants can be created and open in the editor. Verified by 13 new client tests against a stateful If-Match stub, six mutants caught, and a live check against the dev backend (autosave and a real 409).
<!-- SECTION:FINAL_SUMMARY:END -->
