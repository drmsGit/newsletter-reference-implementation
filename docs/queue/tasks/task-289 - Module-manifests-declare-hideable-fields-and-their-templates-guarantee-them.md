---
id: TASK-289
title: 'Module manifests declare hideable fields, and their templates guarantee them'
status: To Do
assignee: []
created_date: '2026-10-05 21:27'
updated_date: '2026-10-05 21:29'
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
- [ ] #1 Manifests carry hideable; GET /modules reports it
- [ ] #2 A manifest marking a field hideable whose template prints it outside a guard mentioning it is refused at load
- [ ] #3 The standard email modules mark the agreed fields hideable and load
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-05, from writing ADR-187: the load-time rule is tightened — the hideable field must be a conjunct of its guard's test (the field itself, or an 'and' chain containing it at the top); 'button_label and button_url' passes, 'button_label or image_url' is refused. A violation costs only that module, as UndefinedFieldError does, naming module, field and template line. Tests: add a refused 'or' guard.
<!-- SECTION:NOTES:END -->
