---
status: decided
date: 2026-10-05
---
# Element Hiding — final design pass

**Status: decided, 2026-10-05 (task-218), with the user, one question at a
time. Nothing here is built yet. The architecture is recorded in
[[ADR-187 — A Manager Hides Fields Per Module, and Required Means Required When Shown]];
the work is filed as three build tasks (see the end).**

## Where it comes from

The user's brief for the editor, quoted in [[Manager Workflow - design interview]]
(Cluster 3): *"options to override the content or to hide elements (like no
button, no headline)"*. It was named in the editor's scope and never designed.
When the gap was filed (task-218, 2026-09-27) it was worded as "`ModuleInstanceDB`
has no visibility flag", which reads as hiding a whole module; corrected with
the user on 2026-10-05. **The point is layouts:** one module type — Image Left —
gives image + headline + button, headline + body, image + button…, instead of
tens or hundreds of near-identical module types.

## Decisions

1. **Each field is an element.** No groups: a group is another layer to manage
   in the editor and the templates, and would tie a field to one visual part (a
   link may serve the button or the image).
2. **The manifest says which fields may be hidden:** `"hideable": true` on a
   variable, beside `required`. "May be hidden", not "is hidden".
3. **The choice lives on the module in the variant** (`hidden_fields`, a list of
   field names), shown in the editor as a toggle on each hideable field. It
   applies whatever fills the module — record, typed text, or a slot's pick. It
   survives re-binding to another record and copies when the variant is
   duplicated. It never touches the record or the override.
4. **Human only, for now.** A person may hide fields in any module, slot-filled
   ones included. No integration and no decision engine hides an element.
5. **A hidden field reaches the template as empty, removed when the values are
   filled in — before the MJML compile** (ADR-131). Template rule: every
   hideable field sits inside an `{% if %}` whose test mentions that field. What
   is hidden is the visible field — the button's `button_label` — so the guard
   may still read `button_label and button_url`: hiding the label hides the
   button, `button_url` is not hideable and stays free for other uses (a link
   on the image), and a label without a link still shows no broken button.
   **Checked when the modules load;** a manifest that breaks it is refused.
6. **"Required" means "required when shown".** A required field may be
   hideable. Where it is hidden, the send-time required-field check, slot
   candidacy and the picker's "Lacks X" note skip it.
7. **Hiding keeps the value.** The editor folds a hidden field to its label with
   "Hidden in this module"; the preview shows the module as it will be sent; the
   frozen send copy records which fields were hidden.
8. **Starting set:** Image Left / Image Right / Single Stack — `image_url`,
   `headline_medium`, `body_medium`, `button_label`. Hero Banner —
   `headline_hero`, `button_label_hero`. Call to Action, Editorial, Header,
   Push Notification — none (for now).

### Examples (decision 5), Image Left with the body hidden

Plain HTML template:

```html
{% if headline_medium %}<h2 class="module-headline">{{ headline_medium }}</h2>{% endif %}
{% if body_medium %}<p class="module-body">{{ body_medium }}</p>{% endif %}
{% if button_label and button_url %}<a href="{{ button_url }}" class="module-button">{{ button_label }}</a>{% endif %}
```

renders as headline + button: the body's `<p>` is never written.

MJML template (the standard package, ADR-131):

```xml
{% if headline_medium %}<mj-text css-class="module-headline"><h2>{{ headline_medium }}</h2></mj-text>{% endif %}
{% if body_medium %}<mj-text css-class="module-body">{{ body_medium }}</mj-text>{% endif %}
{% if button_label and button_url %}<mj-button href="{{ button_url }}">{{ button_label }}</mj-button>{% endif %}
```

is filled first — hidden fields left out — so the MJML handed to the compiler
holds only the headline and the button.

## Decided in this pass (follow from the answers; not asked)

- **A route of its own:** `PUT /campaigns/modules/{id}/hidden-fields` with
  `{"hidden_fields": [...]}`, the module's version in `If-Match` (ADR-180 point
  2), refused for an integration (403, decision 4) and for a field the module's
  manifest does not mark hideable (422, naming it). Audited (a new
  `module.fields_hidden` action with the before and after lists). The general
  `PUT /campaigns/modules/{id}` neither carries nor clears it — so the Jinja
  module form, which uses the same service, cannot wipe it.
- **A module-type change keeps only what the new type still marks hideable.**
  Re-binding the record keeps the list (decision 3).
- **The load-time check reads the template's structure** (Jinja's parser), not
  its text: every use of a hideable field must sit inside an `{% if %}` whose
  test has that field as a **conjunct** — the field itself, or an `and` chain
  containing it at the top. `button_label and button_url` passes;
  `button_label or image_url` is refused, because it would still print the
  button with only the label hidden (found while writing ADR-187).
- **A guard violation costs only that module**, as an undefined field does
  (`UndefinedFieldError`), not all module loading; the error names the module,
  the field and the template line.
- **The frame keeps no value for a hidden field**: it records the list, and the
  values it freezes are only the shown ones. The value lives on in its source
  (decision 7). A text search would pass `{{ body_medium }}` printed once
  inside the guard and once outside it.
- **One helper says what a module requires when shown** — the required fields
  minus its hidden ones — and every check reads it: `missing_required_fields`
  and `module_states` (live), `missing_required_in_frame` (send),
  `candidate_query` (slots; a field counts if it is required and not hidden in
  a module the slot fills), and the client's picker note. Three checks
  drifting apart is the risk ADR-187 names; one helper is the mitigation.
- **The frame records `hidden_fields` per module entry** and drops those fields
  from its frozen variables; a slot entry carries the list so the pick made at
  send drops them too. A frame frozen before this has no key and means "none
  hidden" — old snapshots render as they did.
- **No Jinja toggle.** The Jinja pages render through the same code, so they
  show the layout correctly; choosing it is done in the React editor.

## Where each part lands

| Part | Server | Client | Task |
|---|---|---|---|
| Manifests and templates | `ModuleVariable.hideable` (`app/modules/registry.py`); the load-time guard check in `_load_manifest`/`assert_manifests_load`; the standard manifests and templates (`storage/modules/email/`): a guard for each headline (the image, body and button are guarded already) | — | build 1 |
| The choice and its effects | `module_instances.hidden_fields` (migration 0033, JSON list, default empty); the route; type-change pruning; duplication (`app/campaigns/duplication.py`); the renderer leaves hidden fields out (`render_cms_module`, `render_static_module`, `build_frame`, `_pick_for_slot`); the shared required-when-shown helper in the three checks; `hidden_fields` in the composition | — | build 2 |
| The editor | — | a Hide toggle on each hideable field (`CatalogueModule.tsx`, `ModuleFields`), a folded "Hidden in this module" field, the picker's "Lacks" note skipping hidden fields; the preview needs nothing new | build 3 |

**Deliberately not touched:** the catalogue record and the override (decision
7); the readiness warning, which asks whether the record can fill *any* module
of the channel and knows no variant; push manifests (decision 8); machine
principals' other module writes; the MJML compile step itself, which is not
built (the templates are plain HTML today — decision 5 holds for both).

## What could break

- **Templates gain guards:** each headline gets an `{% if %}`. Nothing else in
  the standard templates changes; a headline that is required and shown still
  always has a value, so output is unchanged until someone hides one.
- **A required field hidden** is, by design, a module that goes out without it.
  The checks no longer protect that module; that is the decision, not a
  defect.
- **Every check must use the helper.** A check that reads `required` directly
  will refuse a send or empty a slot for a field nobody sees.
- **Frame shape:** old frames have no `hidden_fields`; readers must treat the
  absence as empty.
- **The migration** runs before any Python edit while the preview backend
  reloads (ADR-181).

## Build tasks

1. **Manifests declare hideable fields, and templates guarantee them** — the
   attribute, the load-time check, the standard set (backend).
2. **A module's hidden fields: stored, set by a person, honoured everywhere** —
   column, route, duplication, rendering, frame, the three checks (backend;
   depends on 1).
3. **The editor hides and shows a module's fields** (frontend; depends on 2).
