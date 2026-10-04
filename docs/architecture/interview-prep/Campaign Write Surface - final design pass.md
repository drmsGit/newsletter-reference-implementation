---
status: decided
date: 2026-10-03
---
# Campaign Write Surface — final design pass

**Status: decided, 2026-10-03. D1–D4 were taken with the user; nothing here is
built yet. The defects are filed as task-248 to task-253.**

The React client reads the whole campaign loop and writes almost none of it:
the one write on campaign detail is Duplicate. This pass covers the rest:
editing a variant's modules, fields, overrides and decision slots, creating a
campaign, and creating a blank variant. CLAUDE.md requires a final-design pass
before building on accepted ADRs: where each part lands, what it reuses, what
it leaves alone, and what could break.

Sources: [[Variant Editor - design interview]] (VE, closed 2026-09-27),
[[Manager Workflow - design interview]] (MW) Cluster 3, and the code as it
stood on 2026-10-03.

## Governing records

- [[ADR-178 — Scope of the Correction, Not Location of the Manager]]:
  - an edit lands in the content record by default;
  - the record-or-override choice is the field's state, not an editor mode;
  - an overridden field shows the value it covers;
  - a slot-bound module is never overridden;
  - reset per field and per module;
  - a passive count of unsent campaigns that use a record (point 8);
  - reason presets;
  - no `outcome_delta` in the composer.
- [[ADR-180 — A Lock Is Advisory for a Person and Binding for a Machine]]:
  optimistic concurrency underneath (a 409 on a stale save), and an advisory
  lock on top that anyone may clear.
- [[ADR-177 — A Field Is Defined Once, Required Per Module]]: whether a field
  is required belongs to the module, lengths are advisory, and the client gets
  derived answers.
- [[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]]:
  `manifest.cms` decides whether a module reads a record or `module_data`.
- [[ADR-160 — Channel Model and Composition]] points 4–6: the channel is fixed
  at creation, and modules are drop-ins.
- [[ADR-162 — Channel Rendering and Artifacts]] point 1: the envelope is the
  header module's fields.
- [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] point 2: edits after a snapshot need a new snapshot. **There is no edit lock after approval, and this pass adds none.**
- [[ADR-153 — Audit and Accountability]] point 4: writes are the floor.
- [[ADR-150 — Tenancy and Access Model]] point 8: content stays inside its brand.
- [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] and
  [[ADR-173 — The Manager Client's Runtime Dependencies]]: generated client,
  react-aria-components, TanStack Query.

Already decided in the interviews, so not reopened here:
- Variants are edited on their own screen (MW Q3).
- The layout is a list stack, a field editor beside it, and a collapsed preview
  bar with an overlay (VE 2.1).
- Modules move with arrows and the keyboard; drag-and-drop is rejected (VE 1.5).
- The envelope is a fixed area at the top (VE 2.3).
- A slot is configured on its module, in place (VE 1.3).
- Completeness is shown only inside the editor (VE 2.2).
- Rich text is raw markdown with the syntax explained (VE 2.5).
- Duplicate is the primary way to create a variant, blank the secondary one
  (VE 5.1).
- Picking a channel opens an empty editor (MW Q4).

## What the code does today (verified 2026-10-03)

**The JSON write routes exist**, and both planes share the same services:
- campaign create, which also creates the first variant;
- variant create and update;
- module create, update, delete and move;
- slot create, PUT and PATCH;
- override create and reset;
- both duplicates.

**The module manifests reach the client** through `GET /modules?channel=`
(`ModuleManifestOut`, whose field types come from `fields.json`). The campaign
composition already carries:
- `overrideable`, `active_override`, `can_add_module` and
  `accepted_module_types`;
- the envelope modules, kept apart from the rest.

### Defects found on the write path (prerequisites, not design)

Each item below was confirmed against the code. Each is a defect against an
accepted record, not an open question.

1. **A module can be bound to another brand's content.**
   - `create_module_for_variant` and `update_module`
     (`backend/app/campaigns/service.py:478-583`) check neither that
     `content_record_id` belongs to the brand nor that `decision_slot_id`
     belongs to the same variant.
   - Rendering loads a bound record by id with no brand filter
     (`resolve_renderable_content`, `backend/app/rendering/service.py:567-595`).
   - So brand A's manager could render or send brand B's content. This breaks
     ADR-150 point 8.
2. **`update_module` re-checks nothing.**
   - A PUT can change a module to another channel's type, an unknown type, or
     the envelope type.
   - Create checks the type but still accepts the envelope type as a content
     module, which gives a duplicate header that `set_envelope_fields` ignores.
3. **`POST /campaigns/{id}/variants` drops `subject` and `preheader`**
   (`backend/app/campaigns/router.py:159-166`). The request model accepts them
   and they are silently lost.
4. **`PUT /campaigns/decision-slots/{id}` answers 500 for a config the
   strategy rejects** (`router.py:471`, no `ValueError` mapping). PATCH maps it
   correctly.
5. **None of these writes is audited**, on either plane. Only the two
   duplicates are. Override reset does not record who reset it. This breaks
   ADR-153 point 4.
6. **Deleting a module hard-deletes its overrides, history included**
   (`service.py:596-600`). VE 3.5 gives override history its own screen, and
   this erases what that screen would show.
7. **`module_data` is never checked against the manifest.** Undeclared keys
   are stored. Per ADR-177, `required` is advisory while editing, but unknown
   keys and wrong types should be refused, as overrides already refuse unknown
   keys.

### Mechanism the accepted records owe and the API lacks

- **Optimistic concurrency** (ADR-180 point 2, task-110). Nothing checks
  `updated_at`, so the last write wins, and two module moves at once can
  surface as a 500.
- **The unsent-campaign count** (ADR-178 point 8, task-224). It is binding as
  soon as the composer edits a catalogue value.
- **Partial module edits.** Module PUT replaces the whole module, and the
  variant PUT clears subject and preheader if they are left out. "Override this
  one field" and "edit this one field" need either a PATCH or a client that
  always sends the full object. The client already reads the full object, so
  the latter is possible, but it widens what a stale save overwrites.
- **Client side:**
  - a 422 with a list of field errors loses its detail in `read()`
    (`frontend/src/api/resources.ts:65-74`), so per-field server errors never
    reach a form;
  - no hook reads `GET /modules`.

## Where each part lands

| Part | Server | Client |
|---|---|---|
| Variant editor screen | composition read as is; `GET /modules?channel=` | new `screens/VariantEditor.tsx` at `/campaigns/:id/variants/:variantId`; campaign detail links to it |
| Envelope area | `PUT /campaigns/variants/{id}` (always sends name, subject and preheader) | fixed area at the top of the editor |
| Module stack: add, remove, move | existing create, delete and move routes | arrows plus keyboard; add offers only `accepted_module_types` |
| Static module fields (`cms: false`) | module PUT, after defect 7 is fixed | form generated from `ModuleVariableOut` (type, size, note, required) |
| Record-bound fields (`cms: true`) | content record update, which edits the catalogue by default (ADR-178 point 1) | field shows "edits the catalogue: used by N unsent campaigns" (task-224) |
| Override a field | `POST /overrides/`, reset | per-field "override here"; the covered value stays visible; reset per field and per module |
| Decision slot on a module | slot create plus module bind; PATCH for strategy, categories and config | strategy select, category picker (`GET /content/categories`), config generated from the strategy's declared fields (`GET /decision/strategies`) |
| New campaign | `POST /campaigns/` (name, channel) | dialog on the campaigns list; lands in the new campaign's first variant |
| Blank variant | `POST /campaigns/{id}/variants` (after defect 3 is fixed) | secondary action next to Duplicate |

**Deliberately not touched:**
- the Jinja composer (it keeps working on the same services);
- snapshots, approval and send;
- preview (the overlay is its own slice: render route as is, per-module state
  in task-227);
- the advisory lock UI;
- visibility (task-218);
- override reason codes (task-225; presets are client-side until then);
- assets and the image picker (task-112).

## Proposed slices, in order

**Progress, 2026-10-03: slices 1–4 are built** (task-248 to task-253 and
task-110, each reproduced by a failing test first and mutation-checked).
Slice 4 was narrowed with the user: optimistic concurrency only, with an
optional `If-Match` token that the React editor always sends. ADR-180's
advisory lock and "last updated by" moved to task-254, to be built with the
editor screen that shows them. **Slice 5 is built too** (task-255): the
variant editor with envelope, module stack and static fields, saving on blur,
plus creating a campaign and a blank variant. **Slice 6 is built too**
(task-256, task-257, task-224, task-258): catalogue fields, overrides, reach
and publish state. **Its default was then reversed by the user** after trying it:
[[ADR-186 — In the Composer an Override Is the Default and a Catalogue Edit Is Explicit]]
supersedes ADR-178, so typing overrides and the catalogue changes through an
explicit per-field act (task-260). **Slice 7 is built** (task-264, 2026-10-04): a
slot is set up on its module, in place. The write surface is complete, and the preview
overlay is built (task-227, task-265, 2026-10-04). What remains is the advisory
lock (task-254), a keyboard shortcuts overlay (VE 1.5) and a slot heading
(task-223).

1. **Close defects 1–4** (task-248, task-249, task-250, task-251). These are backend fixes with tests. Defect 1 first:
   it is the only one that crosses a brand.
2. **Audit the composer's writes and record who resets an override**
   (defects 5 and 6, task-252, as D2 settles it).
3. **Validate `module_data` against the manifest** (defect 7, task-253). Teach the
   client's `read()` to carry 422 field errors.
4. **Optimistic concurrency** (task-110, moved to the front of the features): an `updated_at` precondition on
   variant, module and slot writes, answering 409.
5. **Variant editor, structure:** screen, envelope, add, remove and move,
   static fields. Then create campaign and blank variant.
6. **Record-bound fields and overrides,** with task-224's count.
7. **Slots on modules.**

Each of slices 1–4 is small and makes the screens in 5–7 safe to build.
Building 5–7 first would put a UI on writes that leak across brands and cannot
detect a conflict.

## Open decisions

- ✅ **D1. Save model: autosave on blur (user, 2026-10-03).** Each field
  saves when it loses focus, so the preview overlay always renders what the
  manager sees, and no render button is needed (VE 2.1). **This makes slice 4
  (optimistic concurrency) a precondition of slice 5, not a follow-up.** With
  autosave, a stale save is a normal event, so the editor must show a 409 in
  place, on the field, and offer to reload that module. The cost is accepted:
  many small writes, each audited once slice 2 lands.
- ✅ **D2. Deleting a module with overrides: keep the erase, and audit it
  (user, 2026-10-03).** Slice 2 audits these:
  - override create and reset, each with the fields and values involved;
  - module delete, naming every override it removed and that override's
    `field_overrides`.

  The history then survives in the audit log, which outlives what it refers
  to (ADR-153 point 5), so the override rows need no schema change. The VE 3.5
  history screen reads the audit log, not `content_overrides`.
- ✅ **D3. Defects 1–7 are filed as queue tasks before they are fixed (user,
  2026-10-03).** One bug task per defect, each citing this pass. Defect 1
  crosses a brand and is filed P1.
- ✅ **D4. The write surface is the next line of work (user, 2026-10-03),**
  ahead of category detail and facets: slices 1–4, then the editor screens.
  The bug tasks are ordered at the front of the queue, task-248 first.
- ✅ **D5. A catalogue edit from the composer is shown as unpublished, with a
  one-click Publish (user, 2026-10-03).** A send uses the record's latest
  published version, so a fix reaches the next send only once published. The
  editor says "changed since version N was published — sends still use
  version N" beside the fields. It does not publish on every save: with
  autosave that would turn versions into edit history rather than releases.
- ✅ **D6. Override reasons are four presets plus Other (user, 2026-10-03):**
  "Shorter for this send", "Different tone for this audience", "Out of date
  for this campaign", "Legal or compliance". They are stored as text in the
  existing reason column; task-225 may turn them into codes.

## Choosing a record for a module

**Decided with the user, 2026-10-04 (task-263), one question at a time. Not
built: task-268 (server), task-269 (picker), task-270 (Content list).**

After trying slice 6, the user said a manager with "only a general topic in
mind" has nothing to pick from. BindRecord (`frontend/src/screens/CatalogueModule.tsx`)
matches part of a title and shows nothing until something is typed. The API
and category rules are recorded in the ADR-175 addendum of 2026-10-04
([[ADR-175 — Facets Are the Manager's Own Taxonomy, Not the Engine's]]). This
section holds the decisions about the screen.

1. **A manager with a topic browses in the picker, not through a slot.** A slot
   filtered to one category already means "let the engine pick from this
   topic", and stays as it is.
2. **Topic is category for now, read-only.** The picker never offers to create
   or assign a category. Facets join as a second filter when task-207 is built.
3. **Text matches title and description**, in the picker and on the Content
   list alike.
4. **"In Nature" means directly assigned to Nature,** as for a slot. The
   dropdown shows children indented beneath their parents.
5. **Order:** with a category, score highest first, then newest. With text
   only, newest first.
6. **Each row shows** the title, a one-line description and notices. The
   notices inform and never block:
   - the record lacks a field this module requires (VE 2.8);
   - it is already in this variant (VE 1.6);
   - it is not published yet.

   The score and the record's other categories are not shown.
7. **Interaction:**
   - The picker opens already listing records, newest first.
   - A text field sits beside a one-category dropdown, and the two combine.
   - Results update live after a short typing pause.
   - Arrow keys move through results, Enter binds and Esc closes. These keys
     appear in the shortcut overview.
8. **The Content list gets the same category filter**, built alongside
   task-267's content-screen work (task-270).

**Deferred, not rejected:**
- body-text and full-text search;
- including child categories, which would be decided for slots and picker
  together;
- a shortcut from the picker to a slot.

**Where it lands:**
- **Server, task-268:** `GET /content/` gains a category filter, the wider `q`
  and the score order. It reuses the brand-scoped `page_content_records`
  (`backend/app/content/service.py`). Its row has to carry what "not published
  yet" needs without a query per row.
- **Client, task-269:** BindRecord is rewritten as a keyboard-navigable list.
  The hierarchy is built from `GET /content/categories` and
  `/content/category-relations`, and must survive the multi-parent graph and
  the seeded Beach↔Family cycle.

**Not touched:**
- decision slots;
- `candidate_query`;
- category assignment;
- the list screens' search-on-Enter.

**What could break:**
- Widening `q` changes the Content list's search results as well, which is
  intended.
- A category filter that joins assignments without the brand filter would leak
  another brand's records, the same class of fault as defect 1.

> Note, 2026-10-04: the "Record-bound fields" row in *Where each part lands*
> describes ADR-178's catalogue-first default. Since ADR-186 superseded it,
> typing overrides and the catalogue changes only through an explicit act.
> The row is left as it was decided; read ADR-186 for current behaviour.

## What could break

- **Fixing defect 1 can refuse existing rows.** A seeded or hand-made module
  that already binds across brands would refuse its next edit. Check the
  development database for such rows first.
- **Validating `module_data` (defect 7) can refuse saved modules** whose stored
  data has keys the manifest no longer declares. This needs the same check
  first.
- **An `updated_at` precondition breaks every caller that does not send one**
  (Jinja forms and machine integrations), unless it is optional for those
  callers. ADR-180 point 3 makes it binding for a machine, which needs care.
- **Autosave (if chosen) multiplies writes.** Once slice 2 lands, audit
  volume grows with every field change.
