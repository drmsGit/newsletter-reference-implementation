---
id: TASK-392
title: Small details the finished design left open
status: To Do
assignee: []
created_date: '2026-10-17 13:31'
updated_date: '2026-10-17 18:25'
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

**From the UX audit of 2026-10-17** (docs/design/ux-audit-2026-10-17/FINDINGS.md; screenshots beside it). Triaged with the user the same day: the small, verified fixes are items 7 to 21 here; the findings that need a decision first became tasks of their own (TASK-393 to TASK-401); UX-23 is dropped, because Audiences puts New and Suggest under the title as render 37 draws it. Every cause below was checked against the code, not taken from the report.

Regressions from TASK-372 itself, so worth doing first:

7. (UX-01, audit P1) The image picker's cards are crushed: each card is a button, and step 1 of TASK-372 (aded12e) gave every button a fixed height (frontend/src/index.css:154, the button rule), so a 96 px thumbnail sits in a 28 px button and overlaps the rows and the filters. The card needs height: auto and its own padding (.image-grid__card, frontend/src/index.css:1242; markup frontend/src/components/ImageField.tsx:233).
8. (UX-02, audit P1) New record and New audience still use the old inline form inside their dialogs (className create-form at frontend/src/screens/ContentCreate.tsx:51 and frontend/src/screens/AudienceCreate.tsx:54): the heading and the first field share a row, the fields are about 164 px wide, and Create comes before Cancel. Use the dialog-form and DialogActions pattern every other create dialog uses since step 14 (frontend/src/components/NewDialog.tsx).
9. (UX-06) Multi-line fields have the weak divider as their border (about 1.38:1 on white, against WCAG 1.4.11): the older rule .field textarea (frontend/src/index.css:765) overrides the strong field border step 1 set for textarea. Remove or align that rule so textareas use the field border token, as inputs do.
10. (UX-07) The Personalise menu runs the label into the token ("Salutation formal{{salutation_formal}}"): the item is a flex row, so the space between the label and the token's span collapses (frontend/src/components/EditorFields.tsx:177). Give the token its own element with a gap, in monospace.
11. (UX-11) In Settings, General, the read-only facts (Sending's channels; AI's default model, key, tokens, warning, spent) start at the card's left edge while the inputs beside them are inset 16 px: the rule .card-rows .fact-list { padding: 0; } (frontend/src/index.css:1703) also hits the plain dt/dd lists (dl.fact-list.facts-compat, frontend/src/screens/Settings.tsx:97, 133, 205 and the AI facts in Sections). Render them with the shared Fact rows, or give the compat lists the 16 px inset.
12. (UX-12, UX-25) Buttons beside a field line up with the field's label instead of its control: Add under "Put it under" and "Add a subcategory" (categories), Duplicate (record), Give (user access), Issue a key (integration), and Rename and Delete in Settings, Brands, where the name field also stays about 164 px wide. The cause is the global button rule's align-self: flex-start (frontend/src/index.css:172), added in step 1 so buttons in a column keep their width; it overrides the row's align-items. In a row (.inline-form, .create-form, .field-pair and similar) the button should align to the end, and the Brands name field should grow (frontend/src/screens/Brands.tsx:56).
13. (UX-22) In the list column the search box and the filters start 12 px left of the title and the rows: the title has 20 px (frontend/src/index.css:1358, .list-head), the search and filters 8 px (index.css:1361 .col-list .filters, index.css:1530 .col-list .search-compact). One indent per column (HANDOFF section 3). The decision history shows the same offset. DROPPED 2026-10-17 by the user's decision: the code matches render 20 and ui.css (.filters and .search, 8 px), where boxes line up with boxes at 8 px (the selected row's highlight) and text with text at 20 px; the audit compared a box edge with text.
14. (UX-13) Dialogs differ in where Close sits and in which order the actions come: the image picker has Close under its heading on the left, the preview a right-aligned header, Paste people stacks Check and Cancel (frontend/src/screens/AudiencePeople.tsx:196, 243). One header pattern (title, Close at the right where there is one) and one footer (Cancel, then the primary action, at the right).

Accessibility and polish:

15. (UX-08) Every "Personalise…" button has the same accessible name (frontend/src/components/EditorFields.tsx:173): name it by its field, for example "Personalise Subject line", keeping the short visible text.
16. (UX-09) The Remove buttons in a user's Access card are all named "Remove" (frontend/src/screens/PersonDetail.tsx:72): name each by what it removes, "Remove Admin on Grathaus Outdoor", as other lists do.
17. (UX-10) The recipient page's tables have no header cells (frontend/src/screens/RecipientDetail.tsx:42, 65, 84, 105, 118 and the groups table at 191): consent, deliveries, decisions, interests and consent history are td-only rows. Add column headers (th with scope) and an accessible name per table.
18. (UX-16) React Aria's own words follow the browser's locale, so in an English interface a German browser hears "ausgewählt" and "Schließen": the app sets no locale (frontend/src/main.tsx renders App without an I18nProvider). Wrap it in I18nProvider with the interface's language; record content keeps its own languages.
19. (UX-17) The keyboard shortcuts have no visible way in: the overview opens only with ?, and only one control in the client carries aria-keyshortcuts. Add a keyboard-reachable "Keyboard shortcuts" action in the shell and aria-keyshortcuts where a single key is valid (Open preview, the navigation). Whether the character shortcuts can be turned off is its own task (TASK-393, from UX-04 and UX-05).
20. (UX-24) "Upload new" in the image sheet shows the browser's native file button ("Datei auswählen") next to the app's own fields (frontend/src/components/ImageField.tsx:334, 370): a styled trigger that opens the same native chooser, with the chosen file's name beside it (React Aria FileTrigger).
21. (UX-28) A long body field opens four rows high, the same as a short one (frontend/src/components/EditorFields.tsx:100, rows={4} for every rich-text field): a field whose definition has size long (storage/fields.json, body_long) should open taller.

Check items 1 to 5 against their renders at 1,440 px in the browser pane, light and dark; items 7 to 21 against the audit's screenshot for each, and with the keyboard where the item is about names or focus.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The category graph uses v2 tokens for its circles, after a choice of which tokens carry rising and falling
- [ ] #2 Slot settings categories are option rows as in render 23
- [ ] #3 A catalogue field's hide switch and Change in catalogue share one line as in render 21
- [ ] #4 Performance on the record page uses fact rows
- [x] #5 The Duplicate button and its pulldown share a baseline
- [ ] #6 The rich-text hint promises only what the email renders, or the renderer formats italic and bullet lines as the hint says
- [x] #7 The image picker's cards show their whole thumbnail and title, without overlapping the rows or the filters
- [x] #8 New record and New audience use the dialog form and DialogActions: heading on its own row, full-width fields, Cancel then Create
- [x] #9 Multi-line fields have the same strong field border as inputs
- [x] #10 Personalise menu items show a gap between the label and the token, the token in monospace
- [x] #11 Settings General read-only facts share the 16 px inset of the inputs beside them
- [x] #12 Buttons beside a field align with its control, not its label, and the Brands name field grows
- [x] #13 In the list column the search box and filters start at the same indent as the title and the rows
- [x] #14 Dialogs share one header pattern and one footer order: Cancel, then the primary action, at the right
- [x] #15 Each Personalise button is named by its field
- [x] #16 Each Remove in a user's Access card is named by the access it removes
- [x] #17 The recipient page's tables have header cells with scope and an accessible name each
- [x] #18 React Aria's own strings follow the interface's language through an I18nProvider
- [x] #19 A keyboard-reachable Keyboard shortcuts action exists in the shell, and single-key shortcuts carry aria-keyshortcuts
- [ ] #20 Upload new uses a styled file trigger with the chosen file's name beside it
- [ ] #21 A long body field opens taller than a short one
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-17: items 7 and 8 (UX-01, UX-02) fixed in the commit after c58eb2f. The image card overrides the button height (index.css, .image-grid__card); live, cards are 158 px with the 96 px thumbnail inside. New record and New audience use dialog-form and DialogActions, heading in the Dialog; tests in Content.test.tsx and AudienceEditor.test.tsx, each mutation-checked.

2026-10-17: item 9 (UX-06) fixed: the old .field textarea rule removed, so textareas use the base field rule (strong border, 6/8 px padding, red when invalid). Checked live: textarea and input borders computed equal, light #857a6c and dark #8f857a. CSS only, no unit test possible in jsdom.

2026-10-17: item 10 (UX-07) fixed: label and token in the MenuItem's label and description slots, token as code, .personalise-entry spaces them (index.css). Test in EditorFields.personalise.test.tsx, mutation-checked on the slot and the code element. Live: at least 16 px between label and token, monospace, aria-describedby set.

2026-10-17: item 11 (UX-11) fixed: the six facts-compat lists in Settings.tsx are Fact rows; the facts-compat CSS removed. Test in Settings.test.tsx (every dt sits in a .fact), mutation-checked. Live: the facts and the field labels start at the same x (273 px) in Sending and AI.

2026-10-17: items 12 (UX-12, UX-25) and 5 fixed together, one cause: in the ten rows that align to the end (.filters, .pager, .add-module, .create-form, .inline-form, .bind__filters, .record-duplicate, .assignment, .assignment-add, .image-library__filters) a direct-child button now has align-self: auto (index.css, after the button rule); the Brands name field grows (.brand-list .inline-form). Live: button bottom equals control bottom (0 px) for Rename, Delete, Duplicate, Remove, Add (record and category), Give, Issue a key, Save; Brands name field 427 px. CSS only, no unit test possible in jsdom.

2026-10-17: item 13 (UX-22) closed as matching the design, not changed. Render 20 draws the search box at x 240 (8 px into the list column), the same as the selected row's highlight, and the title and row text at x 252 (20 px); ui.css gives .filters and .search 8 px padding; HANDOFF's one-indent rule is about text. The user chose to keep it as drawn. AC #13 is ticked as closed by that decision, not as fulfilled.

2026-10-17: item 14 (UX-13) fixed against renders 24, 43 and 45. Sheets: the image picker and the shortcut overview get the sheet-head bar (they used the unstyled preview-head); the preview already matched. Footers in DialogActions or dialog-actions: Paste people (Cancel, then Check or Add N), Delete audience (Cancel, Delete), Suggest from campaign (Cancel), The new key (Copy, I have stored it). The ten create dialogs already matched render 45. Tests in ImageField, Shortcuts, AudienceEditor and IntegrationDetail.secret, mutation-checked four ways. Live: all four opened and cancelled, nothing written.

2026-10-17: item 15 (UX-08) fixed: Personalise takes the field's label and names its button Personalise <label> (EditorFields.tsx); visible text unchanged. Tests in EditorFields.personalise.test.tsx, mutation-checked. Live on record 156: eight buttons, eight distinct names.

2026-10-17: item 16 (UX-09) fixed: PersonDetail names each Remove by the row's access text (Remove <role> on <brand>, or Remove <role> with one brand). Test in Administration.test.tsx (waits for the brands, which load after the grants), mutation-checked. Live on user 96: Remove Viewer on Grathaus Outdoor.

2026-10-17: item 17 (UX-10) fixed: a local Table in RecipientDetail.tsx gives each of the six tables aria-label, an sr-only thead of th scope=col, and the first cell as th scope=row (the design draws no header row, render 38); index.css gives body row headers the cell look. Tests in Recipients.test.tsx (six tables), mutation-checked on the name and the row headers. Live on recipient 1000: tables named, headers in the accessibility tree, thead 1 px, row headers 13 px normal weight.

2026-10-17: item 18 (UX-16) fixed: components/InterfaceLanguage.tsx wraps the app (main.tsx) in I18nProvider locale en-GB (INTERFACE_LOCALE). Test in InterfaceLanguage.test.tsx: under a German browser a popover's hidden close button says Dismiss; red with a pass-through provider (React Aria reads the browser language at load and on languagechange, so the test fires that event after render). Live in the pane, whose browser is de: the Personalise popover's dismiss buttons read Dismiss. Not in this item: our own formatDate uses toLocaleString() and still follows the browser (17.10.2026, 16:58:10 in German), where the renders draw 14 Oct 2026, 08:12.

2026-10-17: item 19 (UX-17) done. Placement decided by the user: the navigation foot, above Sign out (ShortcutsEntry in shortcuts/Shortcuts.tsx, used in shell/Shell.tsx; the foot's button class is now nav-foot-action). Found on the way: React Aria's Button drops aria-keyshortcuts (its filterDOMProps passes only some aria props), so VariantEditor's existing Alt+Arrow attribute had never reached the page; keyShortcuts(keys), a ref, sets it on the element for ?, n (three New buttons), p and Alt+Arrow; SearchBox's Input takes / directly. No attribute for the g-then-letter navigation: aria-keyshortcuts cannot express a sequence. Tests in Shortcuts, Shell, Content, Preview, AudienceEditor and VariantEditor, mutation-checked (no-op helper: 5 fail; entry removed from the shell: 2 fail). Live: foot order avatar, Keyboard shortcuts, Sign out; it opens the overview; icon on the rail; attributes present.
<!-- SECTION:NOTES:END -->
