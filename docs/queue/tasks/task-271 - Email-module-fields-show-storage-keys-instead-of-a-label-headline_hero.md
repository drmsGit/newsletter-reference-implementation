---
id: TASK-271
title: Email module fields show storage keys instead of a label (headline_hero)
status: To Do
assignee: []
created_date: '2026-10-04 11:06'
labels:
  - frontend
  - backend
dependencies: []
type: feature
ordinal: 200080
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found by the user and Claude on 2026-10-04, while checking task-269's bind picker live on the dev server. On campaign 4, variant 4B, the hero module's fit note read "Lacks headline_hero for this module". The editor's own field labels for that module say `headline_hero`, `button_label_hero` and `button_url` too. A manager sees storage keys where the form should name the field.

**Why.** `GET /modules` returns `label: null` for every field of the email modules: `hero`, `img_left`, `img_right`, `cta`, `editorial`, `header` and `single_stack` under `storage/modules/email/`. Only the push notification's manifest declares field labels inline. `_variable` (`backend/app/modules/registry.py:141-171`) reads `label` from the manifest entry alone (`declared.get("label")`). `storage/fields.json` has no `label` attribute, by design. The client then falls back to the key in three places:
- `field.label ?? field.name` in `frontend/src/components/EditorFields.tsx:33`;
- the same fallback in `frontend/src/screens/CatalogueModule.tsx:446`;
- the picker's fit note in `CatalogueModule.tsx:412`.

**What ADR-177 already decided, and nothing implements.** Point 3 of [[ADR-177 — A Field Is Defined Once, Required Per Module]] gives the field descriptor `concept`, `size`, `type` and `note`. It says `note` replaces `label`, because "the form label can be built from `concept` and `size`". Every email field has those in `storage/fields.json`. For example:
- `headline_hero` is concept `headline`, size `hero`;
- `button_label_hero` is `button_label`, size `hero`;
- `button_url` is `button_url`, with no size.

Nothing builds the label, so this is a gap against an accepted record, not an open design question. The registry docstring also claims "the definition wins" for labels, which the code does not do.

**Left to this task's final-design pass:**
- **Where the label is derived.** On the server it would go into `ModuleVariableOut.label`, which the design pass says the client receives as a derived answer (ADR-177 there: "the client gets derived answers"). On the client it would be a formatter.
- **The wording.** Does "Headline (hero)" read better than "Headline"? Within one module the size is usually redundant, but the picker's fit note and the content screens may show fields from several modules side by side.
- **Push's inline labels** ("Notification title" and the others): do they stay as an override, or move to `storage/fields.json`?

Keep the Jinja composer in view. It has its own hand-written email labels (task-63), so it is not affected, but it should not end up disagreeing with the React editor.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every email module field reaches the variant editor with a readable label, built from its concept and size as ADR-177 point 3 says, never the storage key
- [ ] #2 The bind picker's fit note and the editor's field labels use the same wording
- [ ] #3 A test fails if a module field declared in storage/fields.json reaches GET /modules without a label
<!-- AC:END -->
