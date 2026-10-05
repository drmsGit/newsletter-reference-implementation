---
type: adr
status: accepted
topic:
  - architecture
  - content
  - data-model
  - channels
created: 2026-09-27
source:
  - "[[Variant Editor - design interview]] Cluster 2, questions 2.4, 2.8 and 2.10, resolved 2026-09-26"
depends_on:
  - "[[ADR-013 — Content Reference Instead of Content Copy]]"
  - "[[ADR-160 — Channel Model and Composition]]"
  - "[[ADR-161 — Channel Execution Shapes]]"
  - "[[ADR-162 — Channel Rendering and Artifacts]]"
  - "[[ADR-174 — Channel Readiness Is Asserted, Not Computed]]"
---

## Status
Accepted

## Context

The content catalogue's field set is hardcoded and the code already says it is in the wrong place. `CONTENT_FIELD_GROUPS` (`backend/app/content/service.py:101`) holds the per-channel field list, and its own docstring records the defect: the list is *"declared here rather than derived from the channel manifests, which is where it belongs"*, adding that *"when that list exists, this table should read from it rather than repeat it"*. The email half is duplicated a second time in `backend/scripts/import_content_csv.py:33-41`. Two copies of one fact that can disagree, with a written admission that neither is the home.

**Deriving the set from the manifests is the obvious repair and it exposes a sharper problem underneath.** Manifest discovery already walks every file at startup, so a union across manifests is computable where the registry already reads. But `headline_medium` is declared in three manifests at once today, and a union by exact name merges them silently: if two manifests disagree about what that field *is*, whichever discovery reached last wins, with nothing raised anywhere. The union makes an existing exact-name collision load-bearing instead of incidental. What the interview found is that the manifests are the wrong home not because derivation is expensive but because **a field's definition is not a property of any one module that uses it**.

**The split falls along a line question 2.8 discovered rather than designed.** `required` cannot be a property of a field: `body_medium` is required by one module and absent from another, so the catalogue has no single truth to show. Asking which parts of a variable declaration have that shape separates them cleanly — `type`, `size`, `note` and `envelope` describe the field wherever it appears; `required` describes a use of it. One belongs in a central definition, the other stays with the module.

**A bolder restructure was proposed by the user and narrowed rather than rejected.** The proposal was one manifest of all fields plus a separate module→field mapping file, replacing the per-module `name.json` + `name.html` pair. The definitions half is right and is adopted here. The mapping half collides with [[ADR-160 — Channel Model and Composition]] point 6, which names modules as its own precedent for drop-in registration — *"a third pattern that needs registering in several places is the one that eventually gets registered in two"* — under the criterion **time-to-first-output beats completeness**. A central mapping turns "drop two files in a directory" into "drop one file and edit a shared registry", which is precisely the registration step that record refused, and a merge-conflict hotspot the first week two people add a module.

**Deriving the field name from `concept` + `size` was considered at length and rejected, and the reason generalises.** It removes real duplication and puts one naming convention in one place instead of repeating it in every manifest. It was rejected because a concept rename would then silently change every storage key. `ContentRecordDB.content` is `Column(JSON, nullable=False, default=dict)` (`backend/app/content/db_models.py:17`) — unvalidated JSON — so stored content would be orphaned in place with nothing anywhere noticing. **A derived identifier is tidy until something it derives from moves.** With an explicit name, renaming a concept is a display change rather than a data event.

**That same JSON column is why this decision carries no migration, ever.** Values live in one column, not in per-field columns, so a module introducing new variable names is a manifest change and nothing else. This is the storage side of [[ADR-013 — Content Reference Instead of Content Copy]]: compositions reference a record and resolve it at render time, so adding a key changes what resolves, not what is stored elsewhere.

**The obvious objection to a central catalogue — that the field list grows without bound — was tested against the user's own count and does not hold.** Modules cluster into a few content densities rather than proliferating: *"roughly 20 fields for all email fields. push / social / whatsapp / sms may be another 4 per channel"*. The union converges instead of growing with the library, so the long authoring form is a grouping problem, not a scale problem — which is what `concept` is for.

## Decision

**1. Field definitions are centralised in one file, `storage/fields.json`.**
One home per field, carrying what a field *is*. This is the flat list `CONTENT_FIELD_GROUPS`' docstring says should exist and does not.

```jsonc
// storage/fields.json — one home per field definition
{ "headline_medium": { "concept": "headline", "size": "medium",
                       "type": "text", "note": "Works in a 50:50 split" },
  "subject":         { "concept": "subject", "type": "text",
                       "envelope": true } }
```

**2. A module manifest still declares which fields it uses and whether each is required there, and stays a drop-in pair.**
`name.json` + `name.html`, dropped in a directory, with no registry to edit — [[ADR-160 — Channel Model and Composition]] point 6 holds unchanged and the weekend path survives. What a manifest stops doing is re-declaring what a field *is*.

```jsonc
// storage/modules/email/img_left.json — still a dropped-in pair
{ "label": "Image left", "cms": true,
  "fields": [ { "name": "headline_medium", "required": true },
              { "name": "image_url",       "required": true } ] }
```

**3. The field descriptor.**

| Attribute | Purpose |
|---|---|
| `name` | **the JSON key.** Explicit, stable, never computed or derived |
| `concept` | semantic grouping for the authoring form — `headline`, `button_label`, `image` |
| `size` | optional. Only meaningful for sized types, and its vocabulary depends on the type |
| `type` | `text` · `url` · `asset` · `richtext` |
| `note` | guidance for a person **or an AI** on how the field should be used. Replaces `label` |
| `envelope` | whether the field belongs on the delivery envelope rather than in the rendered body. A property of the field, which is why point 8's remaining derivation is about *which module uses it* rather than about the field itself |

`note` replacing `label` is a strict improvement rather than a rename. The form label can be built from `concept` and `size`, which frees the attribute to carry the thing that has no home today — advice readable by a person and by an AI author. `label` was dropped by `ModuleVariableOut` anyway, so nothing regresses.

**4. `required` is a property of *(module, field)*, never of the field.**
The catalogue cannot show one truth for a field one module demands and another never mentions, so **nothing is required at the catalogue level** and the composer warns at bind time instead. This puts the check where the information exists — only the composer knows which module was chosen — and it is the same shape as [[ADR-174 — Channel Readiness Is Asserted, Not Computed]] point 2: warn where the fact bites, do not compute a truth that has no single value.

**5. `size` applies only to text-typed fields, and its vocabulary depends on the type.**
Lengths for text, aspect ratios for images. This is what resolves the objection that *"concept button, size url doesn't make sense"*: a button's label is sized and its URL is not, so they are **two concepts rather than one concept with two parts**. `type` is the attribute that was missing, and adding it makes the size rule statable.

**6. Lengths belong to *(concept, size)*, are defined centrally, and are advisory rather than enforced.**
"One spot to define long = 120, short = 60" is nearly right and not quite: a long headline and a long body are not the same limit. Defining the table centrally rather than per manifest means two modules cannot disagree about what "long headline" means — point 4's collision problem in another form. Advisory, not enforced, per the report-not-block line this repository already runs on.

**7. The catalogue's field set becomes a file read rather than a derivation.**
`GET /content/fields` reads `fields.json` instead of computing a union across manifests. `CONTENT_FIELD_GROUPS` (`backend/app/content/service.py:101`) and its duplicate (`backend/scripts/import_content_csv.py:33-41`) both collapse into it. The raw-versus-derived tension evaporates for that route because there is no longer a derivation to expose.

**8. The client is given derived answers, not manifests to derive from.**
One derivation collapses and one remains, and the remaining one gets a route. The field union becomes a read (point 7). **The envelope lookup stays derived**: even with `envelope: true` on the field definition, *which module carries a channel's envelope* depends on which module **uses** that field, so `envelope_module_type(channel)` (`backend/app/modules/registry.py`) keeps its job as a scan across manifests — the mechanism [[ADR-162 — Channel Rendering and Artifacts]] point 1 put in place when it moved subject and preheader into a module. It is internal today and needs exposing.

A client that scanned manifests for `envelope: true` itself would be a third copy of one derivation, in another language. `docs/react-migration-inventory.md` names exactly this: *"the React client must not be asked to reimplement backend business logic — if it can, so can any other client, and the rule was never enforced."*

## Consequences

### Positive

- **The silent collision is removed structurally rather than by convention.** Three manifests declaring `headline_medium` can no longer disagree about its type, because only one of them says what its type is.
- **Two hardcoded lists become one file, and the code that admits the defect stops admitting it.** `CONTENT_FIELD_GROUPS` and the import script's copy have exactly one successor.
- **A new module needs no migration and no schema work — only a manifest and a template.** The JSON column means new variable names cost nothing at the storage layer, which is what keeps [[ADR-160 — Channel Model and Composition]] point 6's two-file promise true for fields as well as channels.
- **`note` gives per-field guidance a home for the first time, and it is readable by an AI author as well as a person.** That matters more than it sounds: content authoring is explicitly outsourceable, and an agency or agent filling a field currently has nothing to read.
- **`type` fixes a defect it was not aimed at.** `_RICH_TEXT_FIELD` is a single hardcoded name (`backend/app/rendering/service.py`), so `body_long` would silently get no formatting. Declared once as `type: "richtext"`, the constant goes away.
- **Renaming a concept becomes a display change.** Stored content is untouched because the key was never derived from the thing that moved.

### Negative

- **Removing a field definition while stored content still carries the key leaves inert data.** This is a consequence, not a decision: the authoring form stops offering the field and the renderer never asks for it, so the value sits in the JSON blob unreachable and unnoticed. Nothing cleans it up and nothing reports it. A module still *referencing* a removed name is different — that is a discovery-time error, the same fail-closed class as `MisfiledManifestError` (`backend/app/modules/registry.py:31`), and it fails loudly at startup rather than quietly at render.
- **`fields.json` is a file the backend must reload or restart to pick up.** The same property module discovery already has, and the same operational surprise for anyone who edits it on a running system.
- **Two files must now agree for a module to work.** A manifest naming a field that `fields.json` does not define is a new failure mode that did not exist when the manifest was self-contained. It is caught at discovery rather than at render, which is the right place, but it is one more thing to get right when dropping in a module.
- **The redundancy between `name` and `concept` + `size` is real and is accepted deliberately.** `headline_medium` with `concept: headline, size: medium` repeats itself in every field definition, and someone will propose deriving it again. The reason it was rejected is in Context and is a property of the storage model, not a matter of taste.
- **One route remains a manifest scan, so the derived/raw question is answered twice rather than once.** The envelope lookup is a scan and must stay one; anyone reading this record for a general rule will find the general rule has an exception in it.
- **`required` only ever means something in the composer**, so the catalogue authoring form can neither show nor enforce completeness. A manager authoring a record cannot tell from the form which fields will matter until a module is bound.

## Notes

- **This narrows [[ADR-161 — Channel Execution Shapes]] point 7 and the narrowing should be recorded there.** That record's settled split is *"provider `.py` = capabilities · module manifest = fields and limits · channel = an attribute on the variant plus which manifests it accepts"*. The manifest keeps declaring **which** fields a module uses and whether each is required; what moves out is the definition of the field and the length table. Point 7's substance — that the authoring contract exists before a provider is chosen and does not live in the adapter — is untouched and is in fact strengthened, since the contract is now in one file rather than repeated across manifests. **A dated addendum is owed on ADR-161 rather than a supersession**; the addendum text is reported with this record rather than applied here, per the rule that a new record does not edit an accepted one. This repository has had exactly one supersession ever, and this is deliberately not a second.
- **`concept` is not a facet, and the two must not be conflated.** [[ADR-175 — Facets Are the Manager's Own Taxonomy, Not the Engine's]] governs how a manager classifies *content records*. `concept` groups *fields* in the authoring form and is defined by whoever writes modules, not by a manager. They answer different questions about different objects and neither should grow into the other.
- **`richtext` as a type comes from question 2.5, decided in the same cluster.** The descriptor question 2.10 settled listed `text` · `url` · `asset`; the rich-text decision then required a fourth, because a hardcoded field name cannot express which fields take formatting. Recorded here because the type vocabulary belongs to the field model, not to the renderer. The corollary is question 2.5's, not this record's: once `richtext` is declarable on any channel, the renderer must **strip** rather than emit `<strong>` and `<br>` where the channel has no markup.
- **Beta scope for the size vocabulary is two, not three.** *"For our beta example we stick to two length (modules that cover full width, modules that split in 50:50)."* The vocabulary is set by the layouts that exist, not chosen in the abstract, which is why it is two.
- **Deliberately not settled here: which file holds the *(concept, size)* length table.** The decision is that it is central and advisory. Whether it lives inside `fields.json` beside the definitions or in a table of its own is a build question, and getting it wrong is cheap in a way the storage key is not.
- **Also not settled here: assets.** `type: "asset"` is declarable, and the subsystem behind it does not exist — there is no asset table, no upload handling and no picker anywhere in the backend, and `image_url` is a plain string typed into a form. Storing an ID rather than a URL is the right shape and requires a media subsystem that is entirely absent. Logged as a gap, not designed here.
- **Scope, stated because the interview grouped these differently.** Questions 1.8 and 2.9 from the same cluster — catalogue binding by topical signal, and the record-level machine-ready assertion — are decisions about *content records*, not about the field model, and belong in a separate record. They are not folded in here.
- **`docs/playbook-strategy.md` carries no decision-log entry for this interview.** The log ends 2026-09-24 and the interview closed 2026-09-27, so the reasoning behind this record lives in [[Variant Editor - design interview]] rather than in the playbook. The absence is a sequencing gap, not a sign the decision was unargued.

## Addendum 2026-09-28 — a field declares its channel, and a size is not a length

Two things the final-design pass for this record's implementation found
missing. Neither changes the Decision; both complete it.

**1. `fields.json` declares `channel` per field. Point 7 said
`CONTENT_FIELD_GROUPS` collapses into the file and did not say how.** That
table is `{channel: fields}` and this file is flat, so the mapping had nowhere
to go — and it is load-bearing rather than cosmetic: it is the PATCH merge
authority, *"a caller may only clear what it was offering"*, and losing it
means editing a record with push switched off erases the push copy.

Deriving the channel from which modules use a field was refused, because
modules are filed per channel and that is reading the module manifests for
channel — the thing the user ruled out on 2026-09-22. **Declaring is not
deriving**: an explicit `channel` on the field definition is precisely the
*"channel info in the backend"* that ruling asked for, in one file rather than
inferred from a directory layout. `PRESENCE_SIGNIFICANT_GROUPS`
(`backend/app/content/service.py:122`) is channel-keyed for the same reason and
gets the same home.

So the descriptor in point 3 gains a seventh attribute:

| Attribute | Purpose |
|---|---|
| `channel` | which channel reads this field. Declared, never derived from where a module sits |

**2. A size is not a point on a length scale, and the vocabulary must not imply
one.** Point 5 says a size's vocabulary depends on the type — lengths for text,
aspect ratios for images. That is right and it is not enough, because within
text the names still read as an ordering, and the ordering is wrong.

`hero` is the case that proves it. A hero headline is the largest type in an
email and usually sits over a background image, so it must be **short** —
shorter than `headline_medium`, which sits in a 50:50 block. A vocabulary of
`short / medium / long` invites a reader to assume `hero` belongs somewhere on
that line. It does not. **A size names a rendering context, and the amount of
text it wants is a property of that context rather than of the name's position
in a sequence.**

This is why sizes are separate fields rather than limits on one field
(question 2.7): the same content record carries a short hero headline and a
longer medium one, and neither is a truncation of the other.

**Consequences for the implementation, recorded so they are not rediscovered.**
`hero` adopts `headline_hero` and `button_label_hero` and **drops its `text`
field**; the editorial becomes a module of its own rather than a field on the
hero, so that editorial copy stays hand-typed and does not fill the catalogue
with single-use records — the same argument
[[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]]
point 1 makes about a call to action. **That keeps `hero` a plain `cms: true`
module**, so ADR-179's flip does not depend on the unresolved "`cms` is a
boolean and cannot express a mixture" gap. The button's URL stays the unsized
`button_url`, following point 5: a button's label is sized text and its URL is
not, so they are two concepts.

## Addendum 2026-10-04 — A field's label is written once in its definition, not built from concept and size

Prompted by task-271 and decided by the user on 2026-10-04, one question at a
time. The problem was found live the same day while checking task-269's bind
picker: the hero module's fit note read *"Lacks headline_hero for this
module"*, and the variant editor labelled that module's fields
`headline_hero`, `button_label_hero` and `button_url`. A manager saw storage
keys where the form should name the field.

**What point 3 promised and nothing built.** Point 3's descriptor table says
`note` *"Replaces `label`"*, and the paragraph under it says *"The form label
can be built from `concept` and `size`"*. Nothing ever built it. `GET /modules`
returned `label: null` for every email field its manifest did not label
inline, `headline_hero` among them, so the React variant editor and the bind
picker's fit note fell back to the storage key. The paragraph's other premise
has lapsed as well: `ModuleVariableOut` (`backend/app/modules/router.py`) now
carries `label`, so a missing label reaches the client as a gap rather than
being dropped.

**Concept and size cannot name every field apart.** `image_url` and
`image_alt` share the concept `image` and have no size; only `type` (`url`
against `text`) separates them. The concepts `label`, `text` and `url`, used
by the `cta` and `editorial` modules, are generic. The definitions are in
`storage/fields.json`.

**Labels already had a second source.** Some field labels lived inline in
module manifests: `subject` and `preheader` in
`storage/modules/email/header.json`, the `section_heading` entries in
`img_left`, `img_right` and `single_stack`, and the fields of
`storage/modules/push/notification.json`. That is a second source per field,
the condition this record exists to end. The docstring on `_variable` in
`backend/app/modules/registry.py` already claimed *"the definition wins"*, but
the code read only the manifest's label.

**The decision.**

1. **Each field definition in `storage/fields.json` carries one `label`,
   written once.** Point 3's line that the label is built from `concept` and
   `size` is amended accordingly. `note` keeps its role as guidance for a
   person or an AI. The descriptor gains `label` beside `note`; `note` does
   not replace it.
2. **A label names the size only where the size tells two fields of the same
   concept apart**: "Hero headline" against "Headline", "Hero button text"
   against "Button text". The content screen shows fields from several modules
   side by side. Labels that existed inline are kept word for word: "Subject
   line", "Preheader (inbox preview)", "Heading above this module",
   "Notification title", "Notification text", "Image URL", "Opens this link".
3. **A module manifest no longer declares a field label.** The registry reads
   the label from the definition only and refuses a manifest whose field entry
   still declares one, so there is one source. A module's own `label`, its
   name in the module list, is not a field label and is unaffected.
4. **The label reaches every client surface from that one source.**
   `GET /modules` carries it to the variant editor and the picker's fit note.
   `GET /content/fields` carries it to the content screen; its `ContentField`
   model (`backend/app/content/models.py`) gains the attribute.

So point 3's descriptor gains an attribute, and `note`'s row is read without
*"Replaces `label`"*:

| Attribute | Purpose |
|---|---|
| `label` | what a form shows for the field. Written once in the definition, never built from `concept` and `size`, never declared in a manifest |
| `note` | guidance for a person **or an AI** on how the field should be used. Sits beside `label` rather than replacing it |

The exact labels live in `storage/fields.json` and are not repeated here.

## Addendum 2026-10-05 — Required per module, when shown

Prompted by task-218 and decided by the user on 2026-10-05, one question at a
time; recorded in full in
[[ADR-187 — A Manager Hides Fields Per Module, and Required Means Required When Shown]].

**Point 4 is narrowed, not reversed.** `required` stays a property of
*(module, field)*, never of the field. It now also has a condition: a manager
may hide a field in one module in a variant, and in that module a hidden field
is not required. "Required per module" reads **"required per module, when
shown"**. Shown, nothing changes.

**The manifest gains a second per-(module, field) attribute beside
`required`.** `"hideable": true` (default false) declares that a manager may
hide the field in this module. It belongs in the manifest for the same reason
point 4 put `required` there: whether a field may be left out is a property of
the module that uses it, not of the field. It does not enter `fields.json`.
A field may be both required and hideable, which is what makes "no headline"
possible.

Nothing above changes this record's Decision section.

## Related ADRs

### Depends On
- [[ADR-013 — Content Reference Instead of Content Copy]]
- [[ADR-160 — Channel Model and Composition]]
- [[ADR-161 — Channel Execution Shapes]]
- [[ADR-162 — Channel Rendering and Artifacts]]
- [[ADR-174 — Channel Readiness Is Asserted, Not Computed]]
