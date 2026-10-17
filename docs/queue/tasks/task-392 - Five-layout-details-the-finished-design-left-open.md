---
id: TASK-392
title: Small details the finished design left open
status: To Do
assignee: []
created_date: '2026-10-17 13:31'
updated_date: '2026-10-17 16:00'
labels:
  - frontend
dependencies: []
type: feature
ordinal: 210600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Raised 2026-10-17 at the close of TASK-372 (the finished design applied to the React screens): five small places where a screen does not yet match its render, recorded in TASK-372's notes as left for later and moved here so TASK-372 could close. None changes behaviour; each is layout or styling against docs/design/renders and docs/design/canvas-v2/ui.css.

1. The category graph keeps the old colours: green and red circles for rising and falling, grey otherwise (frontend/src/index.css:1318-1320, .graph-node circle and .graph-node--up/--down; the classes are set at frontend/src/screens/CategoryGraph.tsx:135). The graph was never drawn (HANDOFF section 9, decision 20; it opens full width since step 6). The trend is also said in words in the table beside it, so the colour is decoration, but it is the only place the v2 palette is not used. Needs a small design choice first: which tokens carry rising and falling, if any.
2. Slot settings in the editor show the categories as plain checkboxes, where render 23 draws them as option rows (the tinted row with the accent border, like the .react-aria-Radio rows added in step 3). The group is the CheckboxGroup at frontend/src/screens/SlotSettings.tsx:145. A shared option-row style for checkboxes would also serve the AI draft's channel ticks (render 27 draws them that way).
3. In a catalogue-bound module's fields, "Change X in catalogue" (frontend/src/screens/CatalogueModule.tsx:516) and the hide switch stay stacked under the field; render 21 puts the switch on the left and the link on the right of one line under the field.
4. The record page's Performance section keeps the old label/value grid (dl.facts at frontend/src/components/ContentFigures.tsx:46) inside its card, where render 27 draws fact rows (the shared Fact component, frontend/src/components/Fact.tsx).
5. On the record page the Duplicate button sits slightly above its brand pulldown (the row is .record-duplicate, frontend/src/screens/ContentDetail.tsx:236, styled at frontend/src/index.css:842); render 27 draws them on one baseline.
6. The rich-text hint under every multi-line field promises more than the email renders. It reads "**bold**, *italic*, [link](https://…), and a line starting with - for a bullet" (frontend/src/components/EditorFields.tsx:108), but render_rich_text formats only **bold**, [label](https://…) links and new lines (backend/app/rendering/service.py:56-57 and the function after them); *italic* and "- " lines reach the email as typed. Found 2026-10-17 when the editorial became rich text. Either the hint says only what renders, or the formatter learns italic and bullet lines (escaped first, as it does now, and a push still strips them, strip_rich_text). Nothing else promises them: the AI prompts and the content prompt do not mention italics or bullets.

Check items 1 to 5 against their renders at 1,440 px in the browser pane, light and dark.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The category graph uses v2 tokens for its circles, after a choice of which tokens carry rising and falling
- [ ] #2 Slot settings categories are option rows as in render 23
- [ ] #3 A catalogue field's hide switch and Change in catalogue share one line as in render 21
- [ ] #4 Performance on the record page uses fact rows
- [ ] #5 The Duplicate button and its pulldown share a baseline
- [ ] #6 The rich-text hint promises only what the email renders, or the renderer formats italic and bullet lines as the hint says
<!-- AC:END -->
