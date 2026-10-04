---
id: TASK-269
title: The bind picker browses by topic and is driven from the keyboard
status: Done
assignee:
  - '@claude'
created_date: '2026-10-04 10:21'
updated_date: '2026-10-04 10:47'
labels:
  - frontend
dependencies:
  - TASK-268
type: feature
ordinal: 200040
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-263 design session (2026-10-04, user, one question at a time). It is recorded in the "Choosing a record for a module" section of [[Campaign Write Surface - final design pass]] and in the ADR-175 addendum of 2026-10-04. It depends on task-268, the server half.

**Why.** After trying slice 6 (task-258), the user said on 2026-10-03: "when selecting content there should at least be some options to select (if a manager only has a general topic in mind, they might not have a specific title)". BindRecord (`frontend/src/screens/CatalogueModule.tsx:254-286`) shows nothing until you type. It then fetches up to 50 records on every keystroke (`useContentList(0, q, 'active')`, `frontend/src/api/resources.ts:84-94`), keeps 10, and shows each as a separate `Use "title"` button reached by Tab. The variant editor is keyboard-first (Variant Editor design interview: "queue work is keyboard work"), and this is the one list in it you cannot arrow through.

**What was decided for the picker:**
1. **The picker is where a topic-only manager chooses** (decision 1). A decision slot filtered to one category already covers "let the engine pick from this topic", and the "Personalise with a decision slot" path on an unbound module stays as it is. No picker-to-slot shortcut.
2. **It opens already listing records**, newest first, so there are always options (decision 7).
3. **A text field sits beside a category dropdown.** The field searches title and description (decision 3). The dropdown allows one category at a time and shows the hierarchy with children indented (decision 4). Text and category combine. Choosing "Nature" shows only records directly in Nature, not Hiking; the indent makes the children one step away. The category graph is multi-parent (a child can appear under more than one parent) and the demo seed holds a Beach↔Family cycle (`backend/scripts/seed_demo_data.py:93-94`). Building the indented list from `GET /content/categories` and `GET /content/category-relations` must therefore terminate and show each category sensibly.
4. **The picker reads categories only** (decision 2). It never offers to create or assign one; findability labels are facets' job (ADR-175 point 6). When task-207 lands, facets join as a second filter.
5. **Results update live after a short typing pause** (debounce), not on Enter. A picker is a quick in-place choice; the list screens' search-on-Enter (`SearchBox`, `frontend/src/components/RecipientSearch.tsx`) stays as it is.
6. **Keyboard:** arrow keys move through results, Enter binds the highlighted record, and Esc closes the picker. Nothing in the client uses React Aria `ListBox`/`GridList`/`ComboBox` yet; choosing one is this task's design work. Keys handled locally are listed in the shortcut overview through `useShortcut(keys, description, null, 'This screen')` (`frontend/src/shortcuts/Shortcuts.tsx`), as Alt+↑/↓ already are in `VariantEditor.tsx`.
7. **Each row shows the title, a one-line description, and notices** (decision 6). The category score and the record's full category list are not shown. Notices inform and never block (VE 1.4, 1.6):
   - **Fit:** the record lacks a field this module requires. VE 2.8 decided "the composer warns at bind time"; it was never built. ADR-177 says whether a field is required belongs to the module.
   - **Already in this variant:** another module in this variant is bound to the same record. VE 1.6 decided "allowed, note in the composer"; it was never built.
   - **Not published yet:** a send uses the latest published version and refuses a record with none. The data comes from task-268.

**Also check.** After a successful bind from "Use another record", `rebinding` is not reset (`CatalogueModule.tsx:95`, `:104-108`), so the picker stays open. Confirm whether that is unintended before changing it.

**Tests.** The only bind test today types "Lis" and clicks `Use "Lisbon in spring"` in `frontend/src/screens/CatalogueModule.test.tsx`. Seed titles are "{Category} feature #N" (task-71), so demo topic browsing will look thin.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Opening the picker lists records before anything is typed or chosen
- [x] #2 A one-category dropdown, showing the hierarchy indented, narrows the list to records directly in that category, combined with the typed text
- [x] #3 Arrow keys move through results, Enter binds the highlighted record, Esc closes; the keys appear in the shortcut overview
- [x] #4 Each row shows title, a one-line description, and the fit, already-in-this-variant and not-published notices where they apply, none of which blocks binding
- [x] #5 The picker never offers to create or assign a category
- [x] #6 Tests cover browsing without text, the category filter, keyboard binding, and each notice
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. resources.ts: usePickerRecords(q, categoryId): GET /content/ with status active, limit 20 and category_id, keeping the previous data while typing. useCategoryRelations().
2. components/CategoryChoice.tsx: categoryTree(categories, relations) gives each category once, at a depth. A category with several parents sits under its first parent by name. Cycles are cut by a visited set, and categories reachable from no root are appended as roots. It renders Choice with an "Any category" option. Choice.tsx gains an optional indent per option.
3. In CatalogueModule.tsx, BindRecord becomes an RAC Autocomplete (TextField plus ListBox, virtual focus): a 250 ms debounce, the list on open, Enter binds via onAction, Esc calls onClose where the picker is closable.
   - Each row shows the title, a one-line description, and the notices: fit (required content fields of the manifest that are empty on the record), in this variant (sibling module ids), and not published (latest_version_number null).
   - Shortcut overview entries use handler null.
   - onBound closes the rebinding picker.
4. VariantEditor.tsx passes the other modules' content_record_ids down through ModuleFields and CatalogueModule.
5. Tests: browsing without text, the category filter passed to the server, keyboard bind, each notice, the picker closing after a rebind, and categoryTree with multi-parent and cycle cases. Mutation-check each.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-04.
- Chose a plain RAC ListBox with real focus over Autocomplete. Autocomplete's context would also reach the nested category Select, and the shipped bundle gave no way to verify that the Select shields itself. ArrowDown from the search focuses the list; arrows move, Enter uses the record (onAction), Esc closes an opened picker. Esc is gated on DOM containment, so Esc in the portalled category popover closes only the popover.
- Lists 20 active records on open (PICKER_SIZE), with "Showing N of M" when more exist. The search is trimmed and debounced 250 ms.
- Notices are computed client-side: fit = required, non-envelope, non-module manifest variables that are empty or whitespace on record.content (ADR-177); in this variant = other modules' content_record_ids, passed from VariantEditor; not published = latest_version_number null (task-268).
- The rebinding picker closes on a successful bind (onClose). It stayed open before because ModuleFields is keyed by module id and survives a rebind.
- components/CategoryChoice.tsx (reusable for task-270): categoryTree lists each category once, under its first parent by name, with a visited set and leftover roots, so the Beach<->Family cycle neither loops nor disappears. Choice.tsx gained an optional indent.
- AC 5 is verified by inspection: CategoryChoice imports only useCategories and useCategoryRelations, with no mutation or write call.
- Tests: 8 picker tests in CatalogueModule.test.tsx, 4 categoryTree tests, and SlotSettings.test.tsx updated for the new picker. Mutation-checked against 19 mutants, each caught. Client: tsc -b clean, vitest 136 passed.
- Not verified live: the dev backend runs outside this session, so no sign-in code was readable.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The bind picker browses by topic: it lists records on open, has a search (title or description, debounced) beside a one-category dropdown with the hierarchy indented, and is keyboard-driven (ArrowDown into the list, Enter uses, Esc closes; listed in the shortcut overview). Rows show the title, one line of description, and non-blocking notices for fit, already in this variant, and never published. Verified by 12 new tests mutation-checked against 19 mutants, plus the full client suite (136) and typecheck. Not yet looked at live.
<!-- SECTION:FINAL_SUMMARY:END -->
