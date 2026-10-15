---
type: adr
status: accepted
topic:
  - architecture
  - content
  - modules
  - rendering
  - frontend
created: 2026-10-05
modified: 2026-10-15
source:
  - "Design interview with the user, 2026-10-05, one question at a time (task-218)"
  - "[[Manager Workflow - design interview]] Cluster 3, question 3b: the user's brief for the editor"
  - "[[Element Hiding - final design pass]]"
depends_on:
  - "[[ADR-177 — A Field Is Defined Once, Required Per Module]]"
  - "[[ADR-174 — Channel Readiness Is Asserted, Not Computed]]"
  - "[[ADR-131 — Email Module Templates Use MJML as Source Format]]"
  - "[[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]]"
  - "[[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]]"
  - "[[ADR-162 — Channel Rendering and Artifacts]]"
  - "[[ADR-041 — Override Precedence]]"
  - "[[ADR-186 — In the Composer an Override Is the Default and a Catalogue Edit Is Explicit]]"
---

## Status
Accepted

## Context

**The user's brief for the editor asked for this, and nobody designed it.** The brief is quoted in [[Manager Workflow - design interview]] (Cluster 3, question 3b):

> *"options to override the content or to hide elemtns (like no button, no headline)"*

That interview put "hiding elements" in the editor's scope. It flagged one open question for the editor interview: whether "no button" can be expressed by clearing a field *"depends on each template, which makes it a template convention rather than a guarantee"*. The [[Variant Editor - design interview]] never took the question up. It covers only automatic hiding: a decision slot with nothing to show is hidden by [[ADR-086 — Decision Slots Fail Gracefully]], and a slot whose pick is already in the email is hidden too. Both are things the system does. Neither is a choice a manager makes. When task-218 was first filed it was worded as "`ModuleInstanceDB` has no visibility flag", which reads as hiding a whole module. That was a misreading of the brief, and the user corrected it on 2026-10-05.

**The goal is one module type that gives many layouts.** Image Left with image, headline and button but no body is a layout. Without hiding, every such combination is a module type of its own, and a library of tens or hundreds of near-identical module types is what this decision prevents.

**What exists today works partly by accident.** The email templates in `storage/modules/email/*.html` guard their optional parts with `{% if %}`. In `img_left.html` the image, the body and the button render only when filled, and `img_right`, `single_stack` and `hero` do the same, so leaving the body empty already gives "image, headline, button". Three things are wrong with relying on that:

- **It is a habit, not a rule.** Each template does it by choice. Nothing checks it, and a module type added later need not follow it.
- **The headline cannot be left out.** It is printed without a guard (`<h2 class="module-headline">{{ headline_medium }}</h2>`) and is `required` in the manifest, so "no headline" cannot be expressed.
- **"Empty" is not "hidden".** For a catalogue-bound module, emptying a field means an override with an empty value ([[ADR-186 — In the Composer an Override Is the Default and a Catalogue Edit Is Explicit]]). That looks like missing copy, not like a decision. It also loses the value, and the required-field checks treat it as a fault.

**"Required" has to change meaning for "no headline" to be possible.** [[ADR-177 — A Field Is Defined Once, Required Per Module]] point 4 made `required` a property of a (module, field) pair. Three checks read it today: the send-time check ([[ADR-174 — Channel Readiness Is Asserted, Not Computed]] point 3), slot candidacy (ADR-174's addendum of 2026-10-05, "A slot passes over a record that cannot fill its module"), and the bind picker's "Lacks X for this module" note. If a field is both required and hideable, each of those checks must know when the field is hidden. Otherwise hiding a headline blocks the send that the manager just chose to make. This record narrows ADR-177 without contradicting it. The narrowing is carried as a dated addendum on ADR-177, not as a supersession (see Notes).

**The decision log carries it.** `docs/playbook-strategy.md` §5 has the entry "2026-10-05 — A manager hides fields within a module". It summarises the same five points, and this record does not depart from it. The full reasoning is in the 2026-10-05 interview and in task-218.

## Decision

**1. Each field is an element.**
There are no element groups. A group such as "button = label + link" adds a layer that both the editor and the template author would have to manage. It would also tie a field to one visual part, when a field can serve more than one: a link might belong to the button or to the image. What the manager hides is a field.

**2. The module manifest declares which fields may be hidden.**
Each variable gets an attribute `"hideable": true`, which defaults to false. It sits beside `required`, ADR-177's per-module requirement, and for the same reason: whether a field may be hidden is a property of the module that uses it, not of the field. The name says "may be hidden", not "is hidden".

```jsonc
// storage/modules/email/img_left.json: one variable
{ "name": "headline_medium", "required": true, "hideable": true }
```

**3. The manager's choice lives on the module in the variant.**
It is stored as a list of hidden field names, `hidden_fields`, on the module instance. In the editor each hideable field has a toggle. The choice applies wherever the value comes from: a catalogue record, text typed into the module, or a decision slot's pick.

- **It is a layout choice, not content.** It is kept when the module is re-bound to another record, and it is copied when the variant is duplicated.
- **It does not touch the catalogue record or the override.** Hiding a field does not write to either, and [[ADR-041 — Override Precedence]] and ADR-186 are unchanged.

**4. Only a person hides a field, for now.**
A person may hide fields in any module, including modules filled by a slot. That is their choice. No machine principal (an integration) and no decision engine hides an element.

**5. A hidden field reaches the template as empty. It is removed when the values are filled in, before the MJML compile.**
The order matters. [[ADR-131 — Email Module Templates Use MJML as Source Format]] compiles MJML after the values are filled in. A hidden field is blanked at the filling step, so the compiler never sees any trace of the element.

**Template authors follow one rule:** every use of a hideable field sits inside an `{% if %}` whose test has that field as a **conjunct**. The test is either the field itself, or an `and` chain that contains the field at its top level. This is the same guard that already handles an empty field.

- **`{% if button_label and button_url %}` passes.** The button keeps this guard unchanged.
  - `button_label` is the visible field and is hideable, so hiding the label hides the button.
  - `button_url` is not hideable and stays free for other uses, such as a link on the image.
  - A label without a link still shows no broken button.
- **`{% if button_label or image_url %}` is refused.** Under that test, a hidden label would still print the button whenever an image is present.

**The application checks the rule when it loads the modules.** It refuses a manifest that marks a field hideable while its template prints that field outside such a guard, in the same way a broken manifest is refused today. That makes "hideable" a guarantee rather than a convention.

Plain HTML, the content cell of Image Left:

```jinja
{% if headline_medium %}<h2 class="module-headline">{{ headline_medium }}</h2>{% endif %}
{% if body_medium %}<p class="module-body">{{ body_medium }}</p>{% endif %}
{% if button_label and button_url %}<a href="{{ button_url }}" class="module-button">{{ button_label }}</a>{% endif %}
```

With `body_medium` hidden, it renders as:

```html
<h2 class="module-headline">Winter boots are back</h2>
<a href="https://example.com/boots" class="module-button">Shop now</a>
```

The same module in MJML:

```jinja
<mj-column>
  {% if headline_medium %}<mj-text css-class="module-headline">{{ headline_medium }}</mj-text>{% endif %}
  {% if body_medium %}<mj-text>{{ body_medium }}</mj-text>{% endif %}
  {% if button_label and button_url %}<mj-button href="{{ button_url }}">{{ button_label }}</mj-button>{% endif %}
</mj-column>
```

With `body_medium` hidden, the filled MJML that goes to the compiler is:

```xml
<mj-column>
  <mj-text css-class="module-headline">Winter boots are back</mj-text>
  <mj-button href="https://example.com/boots">Shop now</mj-button>
</mj-column>
```

**6. "Required" means "required when shown".**
A required field may also be hideable, and that combination is what makes "no headline" possible. In a module where a required field is hidden, the three checks that read "required" skip it:

- **The send-time required-field check.** This is ADR-174 point 3, implemented as `missing_required_in_frame` (`backend/app/rendering/frame.py`) and `missing_required_fields` (`backend/app/rendering/service.py`).
- **Slot candidacy.** This is ADR-174's addendum of 2026-10-05, "A slot passes over a record that cannot fill its module", in `candidate_query` (`backend/app/decision/strategies/base.py`). A record does not need to fill a field that the slot's module hides.
- **The bind picker's note**, "Lacks X for this module" (`frontend/src/screens/CatalogueModule.tsx`).

When the field is shown, nothing changes: an empty required field still blocks the send, still excludes the record from the slot, and still shows in the picker's note.

**7. Hiding a field keeps its value.**
The value stays in the record, the override or the module's own text. Showing the field again brings the value back.

- **The editor** folds a hidden field down to its label with "Hidden in this module", and shows no input.
- **The preview** shows the module without the field, exactly as it will be sent.
- **The frozen send copy** (the frame of [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]]) records which fields were hidden. The as-sent view therefore stays true if the toggle changes later.

**8. Which fields are hideable in the standard package.**

| Module | Hideable | Not hideable |
|---|---|---|
| Image Left, Image Right, Single Stack | `image_url`, `headline_medium`, `body_medium`, `button_label` | `image_alt`, `button_url`, `section_heading` |
| Hero Banner | `headline_hero`, `button_label_hero` | `button_url` |
| Call to Action, Editorial | none | all |
| Header (envelope) | none | all |
| Push Notification | none, for now | all |

- **Image modules.** The alt text follows the image. The link is not hideable for the reason given in point 5. `section_heading` is typed into the module itself ([[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]], addendum 2026-10-04) and already renders only when filled.
- **Call to Action and Editorial.** Each is one element, so hiding that element would mean removing the module.
- **The Header.** It carries the envelope ([[ADR-162 — Channel Rendering and Artifacts]] point 1), which is not part of the rendered body.
- **Push.** Email comes first, as the brief said. Push can mark fields hideable later without any new design.

## Consequences

### Positive

- **Fewer module types.** One Image Left covers "image, headline, button", "headline and body only", "no headline", and the other combinations, instead of one module type for each.
- **Layout choices survive re-binding and duplication.** A manager who sets up a layout once keeps it when they swap the record, and gets it again in every copy of the variant.
- **One rule for template authors.** It is the guard the templates already use for empty fields, so most of today's templates already follow it.
- **The load-time check makes "hideable" a guarantee.** A template that would print a hidden field is refused when the modules are loaded. The manager never finds out from a sent email.
- **Slot-filled modules get the same layout control.** A personalised module can drop its body or button just as a bound one can.
- **Hiding is not a fault.** The value is kept, the checks know about it, and the state is visible in the editor, the preview and the as-sent view.

### Negative

- **Existing templates must be adjusted.** Every hideable field needs a guard. The image, body and button guards already exist. The headlines in `img_left`, `img_right`, `single_stack` and `hero` are printed without a guard today, and each gains an `{% if %}`.
- **A module can go out without a required field such as its headline, by design.** Once a manager hides the field, the checks no longer protect it in that module. That is the purpose of this decision, and it also means one toggle switches off three checks.
- **Guards are restricted to `and` chains.** The rule refuses a guard such as `{% if button_label or image_url %}`, so a template author who wants an `or` condition around a hideable field must restructure the template.
- **The frame grows.** The snapshot frame records a hidden list per module, which changes the shape [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] point 1 described. The module instance gains `hidden_fields`, so the change needs a migration.
- **Three checks must agree on "skip what is hidden".** They live in Python on the frame, in Python on the live variant and in the candidate query, and the picker's note is computed in the React client. If any one of them forgets the hidden list, a hidden headline either blocks the send or excludes a record for no reason. The mitigation is one shared helper that answers "which required fields count in this module" and is used by every check.
- **No machine can hide a field.** An automated workflow cannot produce a layout without a person. Allowing that later needs its own decision.

## Notes

- **ADR-177 needs a dated addendum, not a supersession.** ADR-177 point 4 says `required` belongs to a (module, field) pair. This record keeps that rule and adds a condition: required per module, when shown. Point 4's Decision stays true as written, so a supersession would discard a record that is still in force. The addendum text is in the report that came with this record. It is not applied here, because a new record does not edit an accepted one.
- **ADR-174 should get a short dated addendum as well.** Point 3's send check and the 2026-10-05 slot-candidacy addendum both say "required field", and a reader of ADR-174 alone would not know that a hidden field is skipped. This narrows how those checks read "required". It does not change ADR-174's Decision.
- **The choice is set through its own route.** It is `PUT /campaigns/modules/{id}/hidden-fields`. Only people may call it (point 4). It takes the `If-Match` version token, as the override and content writes do ([[ADR-180 — A Lock Is Advisory for a Person and Binding for a Machine]] point 2). It answers 422 for a field that is not hideable in that module. The general module `PUT` neither carries nor clears `hidden_fields`, so an edit to a module's content cannot reset its layout by accident.
- **Decided 2026-10-06, by the user: a machine may not show a hidden field again either. People only, in both directions.** No integration and no decision engine hides or shows a field. The one route, `PUT /campaigns/modules/{id}/hidden-fields`, refuses an integration whichever way the call would change the list, whether it adds a field to `hidden_fields` or removes one. Point 4 is worded as hiding only ("no decision engine hides an element"); this answer reads point 4 as covering both directions.
- **The readiness warning is not one of the three checks and does not change.** ADR-174's 2026-10-05 addendum point 4 warns when a record cannot fill any of a channel's modules. It looks at a record with no module instance, so there is no `hidden_fields` list for it to read.
- **MJML is the decided source format but is not built.** The standard templates are plain HTML with Jinja (`storage/modules/email/*.html`), and the email renderer assembles already-compiled HTML (`backend/app/rendering/renderers/email.py`). Point 5's rule and its order (fill in values, then compile) apply to both formats, which is why the Decision shows both examples.
- **Settled by the final design pass** ([[Element Hiding - final design pass]]):
  - **A guard violation costs only that module, not all module loading.** It is handled like a field that `fields.json` does not define (`UndefinedFieldError` in `backend/app/modules/registry.py`), not like a misfiled manifest, which stops everything (`MisfiledManifestError`).
  - **The guard is found with Jinja's parser.** The check reads the template's structure, not its text.
  - **The frame keeps no value for a hidden field.** It records the hidden list, and the only values it freezes are those of shown fields. A hidden value stays in its source (point 7).
- **Not ADR-086.** [[ADR-086 — Decision Slots Fail Gracefully]] hides a whole slot automatically when it resolves to nothing. This record hides one field because a person chose to. The two do not interact. A slot module with hidden fields that resolves to nothing is still hidden as a whole by ADR-086.
- **Preview parity.** Point 7's "the preview shows it exactly as it will be sent" is the obligation [[ADR-063 — Rendering Parity Over Rendering Implementation]] already places on preview and final rendering. Blanking at the filling step, on both the live path and the frame path, is what keeps them the same.

## Addendum 2026-10-15 — blocks compile first, and the new blocks' hideable fields

Prompted by the first MJML blocks ([[ADR-198 — The Email Block Set Is Seven Blocks, Square Images and Text Links]], queue task-371) and by [[ADR-131 — Email Module Templates Use MJML as Source Format]]'s addendum of 2026-10-15. Nothing above changes this record's Decision section.

**1. Point 5's order is reversed.** Point 5 says a hidden field is removed "before the MJML compile", and its MJML example sends filled MJML to the compiler. Blocks are now compiled when they are written (ADR-131's addendum of 2026-10-15), so the compile comes first and the values are filled in later.

- **A hidden field is still blanked when the values are filled in,** and its `{% if %}` guard still removes it.
- **The guard must survive the compile.** The load-time guard check reads the compiled template the backend loads, so a guard the compiler dropped or moved is refused there.
- **For a module that pairs, the check reads its `_<name>_pair.html` too** (ADR-198's addendum of 2026-10-15, point 4).
- **Only loaded names are checked.** A name bound by `{% with %}` is an assignment, not a print.
- **The rule for template authors is unchanged.** Point 5's MJML example still shows the guard; it no longer shows when the compile happens. The Note "MJML is the decided source format but is not built" no longer holds.

**2. Point 8's table, for ADR-198's blocks.**

| Module | Hideable | Not hideable |
|---|---|---|
| Hero | `headline_hero`, `image_url`, `button_label_hero` | `image_alt`, `button_url` |
| Image left, Image right, Column | `image_url`, `headline_medium`, `body_medium`, `button_label` | `image_alt`, `button_url` |
| Single text | `headline_medium`, `body_long`, `button_label` | `button_url` |
| CTA, Headline, Editorial | none | all |
| Envelope | none | all |
| Single Stack (retired) | as in point 8 | as in point 8 |

- **`image_alt` follows the image and is not hideable,** as point 8 says.
- **The Hero gains `image_url`,** because ADR-198 gives it a square image.
- **`section_heading` leaves the image blocks** (ADR-198 point 5). Only the retired Single Stack keeps it.
- **Hidden fields apply to each Column of a pair separately.**

## Related ADRs

### Depends On
- [[ADR-177 — A Field Is Defined Once, Required Per Module]]
- [[ADR-174 — Channel Readiness Is Asserted, Not Computed]]
- [[ADR-131 — Email Module Templates Use MJML as Source Format]]
- [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]]
- [[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]]
- [[ADR-162 — Channel Rendering and Artifacts]]
- [[ADR-041 — Override Precedence]]
- [[ADR-186 — In the Composer an Override Is the Default and a Catalogue Edit Is Explicit]]

### Referenced By
- [[ADR-086 — Decision Slots Fail Gracefully]]
- [[ADR-063 — Rendering Parity Over Rendering Implementation]]
- [[ADR-180 — A Lock Is Advisory for a Person and Binding for a Machine]]
