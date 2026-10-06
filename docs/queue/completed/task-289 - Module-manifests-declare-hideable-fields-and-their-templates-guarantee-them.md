---
id: TASK-289
title: 'Module manifests declare hideable fields, and their templates guarantee them'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-05 21:27'
updated_date: '2026-10-06 10:50'
labels:
  - backend
dependencies: []
type: feature
ordinal: 200376
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-218 design interview (2026-10-05, with the user); recorded in [[ADR-187 — A Manager Hides Fields Per Module, and Required Means Required When Shown]] and [[Element Hiding - final design pass]], decisions 2, 5 and 8. First of three build tasks.

**Today** a manifest variable (`ModuleVariable`, `backend/app/modules/registry.py:59`) has `required`, `envelope`, `source` and the like, but nothing says a field may be hidden. The email templates (`storage/modules/email/*.html`) happen to guard image, body and button with `{% if %}`; the headlines are printed unconditionally.

**Build:**
- `hideable: bool = False` on `ModuleVariable`, read by `_load_manifest` (`registry.py:209`).
- **The load-time rule**, in `_load_manifest`/`assert_manifests_load` (`registry.py:325`): every use of a hideable field in the module's template sits inside an `{% if %}` whose test mentions that field. Read with Jinja's parser (`Environment.parse`, walking `If` and `Name` nodes), not a text search: a text search passes a field printed once inside its guard and once outside. A manifest that breaks the rule is refused at startup like a broken manifest today, naming the module and the field. A module with `has_template: false` cannot declare a hideable field.
- **The standard set** (decision 8): Image Left, Image Right, Single Stack — `image_url`, `headline_medium`, `body_medium`, `button_label`; Hero Banner — `headline_hero`, `button_label_hero`. The headline guards are added; the button guard stays `button_label and button_url` (what is hidden is the label; the link is not hideable). Call to Action, Editorial, Header, Push Notification: none.
- The manifest endpoint (`GET /modules`) reports `hideable`, so the editor can offer the toggle (build 3).

**Changes no output:** nothing hides anything yet (build 2). A required, shown headline always has a value, so the new guards change no rendered email.

Tests: the attribute is read; the rule refuses an unguarded, a half-guarded (printed outside its guard too) and a guard-on-another-field template, and accepts `button_label and button_url`; the standard set loads with the agreed fields; `GET /modules` carries it. Mutation-checked.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Manifests carry hideable; GET /modules reports it
- [x] #2 A manifest marking a field hideable whose template prints it outside a guard mentioning it is refused at load
- [x] #3 The standard email modules mark the agreed fields hideable and load
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first (tests/test_hideable_fields.py): the attribute and its type; the template rule refusing an unguarded use, a use inside and outside its guard, a guard on another field, an or, an else and an elif of its own guard, a filtered use, and a no-template module; accepting a plain guard, an and chain, nested guards, an elif on the field, and the button's label-and-link guard; a violation costing only that module; the standard set; GET /modules.
2. registry.py: ModuleVariable.hideable, 'hideable' in FIELD_ENTRY_KEYS, a strict boolean, UnguardedHideableFieldError, _conjuncts and _check_hideable_guards (Jinja parser) run from _load_manifest.
3. router.py: ModuleVariableOut.hideable.
4. storage/modules/email: the agreed fields marked; headline guards in img_left, img_right, single_stack and hero.
5. Mutation-check, suites, contract, a fresh load of every module.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-05, from writing ADR-187: the load-time rule is tightened — the hideable field must be a conjunct of its guard's test (the field itself, or an 'and' chain containing it at the top); 'button_label and button_url' passes, 'button_label or image_url' is refused. A violation costs only that module, as UndefinedFieldError does, naming module, field and template line. Tests: add a refused 'or' guard.

Built as designed. Choices within the design: the check runs in _load_manifest, so a violation surfaces through _discover's existing 'Failed to load manifest ... skipping' path and costs only that module; the test of an if may read the field (it is not a print); an elif or else branch of the field's own guard is NOT guarded (it runs when the field is empty); only a top-level and chain counts (or, not, comparisons give no guard). The button guards keep 'button_label and button_url'; nothing else in the templates changed but the four headline guards, so no rendered email changes until build 2 hides something.
Validation: 25 tests, failing first (collection error before the code existed); 11 mutants all caught (the survivor 'elif inherits the outer guard' led to the elif case). Backend 1355, client 182 (types regenerated: hideable on the module variables), tsc, contract. Live: a fresh process loads all eight modules with no warning and exactly the agreed hideable fields; the dev server's one 'skipping img_left' warning came from the mutation run editing the template for a moment, restored.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Module manifests can now mark a field 'hideable' (ADR-187), and the app guarantees it: when the modules load, Jinja's parser checks that every use of a hideable field sits inside an {% if %} that holds the field as an and-conjunct, refusing that module otherwise. The standard set is marked (image, headline, body and button label in the three image modules; headline and button label in the Hero), the four headlines gained their guard, and GET /modules reports hideable. Nothing renders differently yet. Verified by 25 tests, 11 caught mutants, both suites, the contract check and a fresh load of every module.
<!-- SECTION:FINAL_SUMMARY:END -->
