---
type: adr
status: accepted
topic:
  - architecture
  - rendering
  - modules
  - content
  - design
created: 2026-10-15
modified: 2026-10-15
source:
  - "task-371 design, decided by the user 2026-10-15, one question at a time"
depends_on:
  - "[[ADR-131 — Email Module Templates Use MJML as Source Format]]"
  - "[[ADR-177 — A Field Is Defined Once, Required Per Module]]"
  - "[[ADR-162 — Channel Rendering and Artifacts]]"
  - "[[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]]"
  - "[[ADR-193 — An Email's Legal Footer Is Fixed, Its Visible Header and Footer Are Placed Modules]]"
  - "[[ADR-197 — Images Are Brand Assets, Served Publicly From an Unguessable Path]]"
  - "[[ADR-086 — Decision Slots Fail Gracefully]]"
  - "[[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]]"
  - "[[ADR-187 — A Manager Hides Fields Per Module, and Required Means Required When Shown]]"
  - "[[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]]"
---

## Status
Accepted

## Context

**The November demo needs example emails that look good** (queue task-371, raised by the user on 2026-10-11). Task-371 asked which blocks the initial set has: hero, image and text both ways, stack, CTA, header, footer, section heading. This record answers that question. How the blocks are compiled is the 2026-10-15 addendum of [[ADR-131 — Email Module Templates Use MJML as Source Format]].

**What exists today (verified 2026-10-15).**

- **The email modules are hand-written Jinja HTML.** `storage/modules/email/` holds `hero`, `single_stack`, `img_left`, `img_right`, `cta`, `editorial`, `header`, `footer` and `envelope`, each a `.json` manifest and an `.html` template. [[ADR-131 — Email Module Templates Use MJML as Source Format]] names MJML as the source format, and nothing compiles MJML yet.
- **The image blocks print the headline as an H2 and end with a button.** `img_left.html` gives the image cell 40% of the width, then `headline_medium` in an `<h2>`, `body_medium` and a `module-button` link. `img_right` and `single_stack` follow the same pattern.
- **The Hero has no image.** `hero.html` holds the H1 (`headline_hero`) and an optional button. Its manifest says it carries no body copy, because editorial copy belongs to the Editorial module ([[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]]).
- **A field is defined once, in `storage/fields.json`** ([[ADR-177 — A Field Is Defined Once, Required Per Module]]). The content record's body text is `body_medium`. There is no long body field. ADR-177's Notes mention `body_long` only as an example.
- **`section_heading` is a small heading typed into the module.** It sits on `img_left`, `img_right` and `single_stack` with `"source": "module"`. It was the first use of [[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]]'s addendum of 2026-10-04.
- **The visible header and footer are placed, decorative modules.** [[ADR-193 — An Email's Legal Footer Is Fixed, Its Visible Header and Footer Are Placed Modules]] introduced them. [[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]] superseded it and carries them forward.

**The set was decided with the user on 2026-10-15, one question at a time.** The user's words are quoted where they decided a point.

**Options not taken.**

- *More than one image format.* The user: *"As I don't want to blow up fields in the content record we stick to one image format (square)."* Each extra format would be another image field on every content record.
- *One Column module holding two content bindings,* or *a slot that picks two records* ([[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]). The user chose two paired modules instead (point 4). With pairing, every rule that works per module still works per column. Neither alternative gets that for free.

## Decision

### 1. The offered email blocks

| Block | Content record | Layout |
|---|---|---|
| **Hero** | one | Big headline on the left, square image on the right. A real button goes with the headline. |
| **Headline** | none | An H2, typed into the module. |
| **Image left** | one | Square image on the left. The right half holds an H3 headline, short body text and a text link. |
| **Image right** | one | The mirror of Image left. On mobile the image is still the first element. |
| **Column** | one | Square image, H3 headline, short body text and a text link, top to bottom. *"Each col selects 1 content record."* |
| **Single text** | one | H3 headline, long body text and a text link. |
| **CTA** | none | One real button. Two buttons side by side when a second label and link are given: *"if possible dynamically 1 or 2 CTA"*. |

- **Editorial stays as it is.** It is hand-typed body copy for one send (ADR-179).
- **The visible header and footer stay as they are** ([[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]]).

### 2. One image format, and one new content field

The user: *"As I don't want to blow up fields in the content record we stick to one image format (square); only one new field: body text short/long separation."*

- **`image_url` is square.** Every block that shows an image shows the same square image of the record.
- **`body_medium` is the short body text.** Image left, Image right and Column use it.
- **`body_long` is the long body text, and the one new content field.** Single text uses it. It is defined once in `storage/fields.json` ([[ADR-177 — A Field Is Defined Once, Required Per Module]]).
- **The CTA's second label and link belong to the module, not to the content.** The CTA has no content record, so all its values are typed into it. Like every field, they are defined in `storage/fields.json`.

### 3. Design rules

The user: *"Only the Hero CTA and the CTA module are actual buttons, else use Text Buttons (text underline with arrow -> or similar), everything is left aligned and 50:50 split."*

- **Two places have real buttons:** the Hero's call to action and the CTA block.
- **Every other link is a text link.** It is underlined text with an arrow (`->` or similar).
- **Everything is left-aligned.**
- **Every split is 50:50.** That covers the Hero, Image left, Image right and a pair of Columns.
- **On mobile every split stacks, image first.** This includes Image right, whose image sits on the right on a wide screen.

### 4. Two columns are two half-width Column modules, paired

The user chose this over one module with two bindings and over a slot with two picks.

- **A Column module is an ordinary module.** It has one content record or one slot.
- **Two adjacent Column modules render as one 50:50 row.**
- **A lone Column fills the left half.**
- **Every per-module rule applies unchanged:** binding, overrides, hidden fields ([[ADR-187 — A Manager Hides Fields Per Module, and Required Means Required When Shown]]), slots ([[ADR-086 — Decision Slots Fail Gracefully]]), required fields and click attribution.
- **The editor offers "Two columns".** It places two Column modules.

### 5. Retired blocks

- **Single Stack is retired.**
  - Existing variants and frozen snapshots keep rendering it.
  - It is no longer offered to add. Its manifest carries a `retired` mark, and an attempt to add it is refused.
- **The small `section_heading` leaves the image blocks.** The Headline block takes its role. Existing values stop showing.
- **Retired blocks are deleted at the next full system reset.** The user decided this. It is a chore task.

## Consequences

### Positive

- **Fewer blocks, and they agree with each other.** Every block follows the same rules: left-aligned, 50:50, square images, image first on mobile.
- **Text links reduce visual noise.** Only two places in an email carry a real button, so the button keeps its weight.
- **The content record grows by one field only.** Square images and a short/long body split cover every block.
- **Two columns need no new mechanism.** Each column is a module, so binding, overrides, hidden fields, slots, required fields and click attribution apply to each column as they already do.
- **Nothing already sent or already composed breaks.** Single Stack keeps rendering for variants and snapshots that hold it.

### Negative

- **Square-only images limit layouts.** No block can use a wide banner or a portrait image, and a record has no way to carry one.
- **Pairing is decided by module order.** Reordering can split a pair: one Column moved away from its neighbour becomes a lone half-width Column. Nothing holds two Columns together.
- **Single Stack lingers until a reset.** Its template and manifest stay in the repository, and the registry carries a `retired` case, until the chore task deletes them.
- **Existing section headings disappear.** A variant that used `section_heading` on an image block loses that heading without any warning. The manager must add a Headline block instead.
- **A Headline is not tied to the block below it.** ADR-179's addendum of 2026-10-04 put the heading inside the module for one reason. A separate heading module *"would float above nothing for exactly the recipients [[ADR-086 — Decision Slots Fail Gracefully]] protects"*. The Headline block is a separate module. When a slot finds nothing, ADR-086 hides the slot's module, and a Headline placed above it still shows.
- **Reconstructions of earlier emails will differ in layout.** The new blocks change the templates of Hero, Image left, Image right and CTA. Removing `section_heading` changes them again. [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] point 4 re-renders a reconstruction with today's templates. For deliveries sent before this change, the templates fingerprint no longer matches and the hash check fails. That is reported, not hidden, and it is the expected result of any template change.

## Notes

- **ADR-179 and ADR-187 are narrowed, not superseded.** Neither Decision is edited.
  - **ADR-179's addendum of 2026-10-04 is unchanged as a mechanism.** `source: "module"` stays: the Headline block and the CTA use it. Only its "first use", `section_heading` on the image blocks, is withdrawn.
  - **ADR-187 point 8 lists Single Stack and `section_heading`.** Its table of hideable fields was written for the old set. Which fields the new blocks mark hideable is not decided here. Point 5's rule (every use of a hideable field sits inside a guard on that field) applies to them unchanged.
  - A short dated addendum on each, pointing here, would let a reader of either record alone find the change.
- **ADR-194 is not changed.** The header and footer stay as its Decision describes.
- **Left open for the final-design pass.** None of these was put to the user:
  - **Whether the Headline block is decorative.** [[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]] point 15 expected a section heading to be decorative (queue task-108). If it is, an email that holds only Headlines does not pass the nothing-to-show floor. If it is not, it does.
  - **Which field the Headline block's H2 uses.** It could be `section_heading` reused as the block's own field, or a new module field.
  - **Which field each H3 uses.** `headline_medium` is the evident one, since it is the image blocks' headline today and no new content field is allowed beyond `body_long`.
  - **How pairing reads past two.** Point 4 decides two adjacent Columns and a lone one. It does not decide three or more in a row, or a pair where ADR-086 hides one Column for a recipient.
  - **Whether the retired Single Stack keeps printing its `section_heading`.** Point 5 says existing Single Stack content keeps rendering, and also that `section_heading` leaves the image blocks.
  - **The labels.** `button_label` is labelled "Button text" in `storage/fields.json`. In most blocks it now drives a text link.
- **The chore task for the reset has not been filed yet.** No queue task mentioning a full reset or retired blocks was found on 2026-10-15.
- **No decision-log entry.** `docs/playbook-strategy.md` §5 has no entry for this decision. Its entry "MJML remains the right call for email module templates, confirmed deliberately" concerns the source format and is consistent with this record. The reasoning here comes from task-371 and the 2026-10-15 session.

## Addendum 2026-10-15 — the final-design pass

Prompted by building task-371. The Notes list six points "left open for the final-design pass"; points 1–6 below answer them, and points 7–10 record what the build settled. **The implementer decided these in the final-design pass on 2026-10-15, not the user.** The user said to proceed without further questions, and has not reviewed the points one by one. Nothing above changes this record's Decision section.

**1. The Headline block is decorative.**

- **Its manifest, `storage/modules/email/headline.json`, carries `"decorative": true`.**
- **A heading alone is nothing to show.** An email that holds only Headlines does not pass the nothing-to-show floor of [[ADR-086 — Decision Slots Fail Gracefully]].
- **This is what [[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]] point 15 expected** of a section heading.

**2. The Headline's H2 uses a new module field, `heading`.**

- **It is labelled "Heading" and defined in `storage/fields.json`** ([[ADR-177 — A Field Is Defined Once, Required Per Module]]).
- **It does not reuse `section_heading`.** That field's label ("Heading above this module") and its note describe the old in-module heading.

**3. Every H3 uses `headline_medium`.**

**4. Pairing is declared, not named.**

- **A manifest key `pairs: true` declares it.** Two copies of such a module in a row render together through `_<name>_pair.html`, which is given `left` and `right`. Only `column.json` carries the key, so the one pair template is `_column_pair.html`.
- **The renderer pairs greedily, in order.** The first pairs with the second, the third with the fourth, and an odd one stands alone in the left half. This is `lay_out` in `backend/app/rendering/service.py`. `email_document` uses it, so the live preview and the frame render pair identically ([[ADR-063 — Rendering Parity Over Rendering Implementation]]).
- **A module that renders nothing does not break a row.** An empty slot or an unbound module leaves only an HTML comment, so its neighbours pair. This answers the Notes' question of a pair where ADR-086 hides one Column.
- **A slot on a Column showing two picks yields two copies, and they pair** ([[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]], addendum 2026-10-11).
- **Each side's links are tagged with its own content id** ([[ADR-182 — A Click Credits Content Only When the Link Names It]]). The rendered pair is split at a marker comment to do this.
- **The pair is wrapped in both modules' `data-module-id`/`data-content-id` divs, nested.**
- **Hidden fields apply per side** ([[ADR-187 — A Manager Hides Fields Per Module, and Required Means Required When Shown]]).

**5. The retired Single Stack renders unchanged, its `section_heading` included.**

- **Its manifest carries `retired: true`.**
- **It is not offered.** `list_manifests(channel, offered=True)` (`backend/app/modules/registry.py`) leaves it out of the add-module offer and out of the content readiness warning.
- **Adding it, or switching a module to it, is refused.** That is `_refuse_module_type` in `backend/app/campaigns/service.py`. A module already of that type may still be edited.
- **Seeded and duplicated rows are not refused.** Duplication copies existing modules.
- **The API's module manifest now carries `pairs` and `retired`.**

**6. Labels, in `storage/fields.json`.**

- **`button_label` is now "Link text", and `button_url` is "Link".**
- **`body_medium` is "Body text (short)", and the new `body_long` is "Body text (long)".**
- **The CTA's second button uses the fields `label_2` and `url_2`.**

**7. How Jinja passes through the compiler.** [[ADR-131 — Email Module Templates Use MJML as Source Format]]'s addendum of 2026-10-15 left this to the build.

- **`frontend/scripts/build-modules.mjs` pastes `mj-include` partials in itself before compiling.** MJML 5.4.1 drops a body fragment included inside a column, and it does not apply `mj-attributes` that arrive through an include.
- **Jinja values sit in attributes,** compiled at validation level soft. **Jinja conditionals sit in `mj-raw`.**
- **Of the head styles, only `@media` and `.moz-text-html` rules are collected,** into `_mjml_head.html`, marked `data-css-inline="keep"`. The rest are left out because a kept style is also inlined. MJML's element resets would land on every module's elements, and the Outlook-only `.mj-outlook-group-fix { width:100% !important }` would pin every column to full width.
- **MJML's viewport meta goes into `_mjml_head.html` with them.** Found in the live check of 2026-10-15: without it a phone lays the email out 980px wide, and the media queries never stack the columns.
- **`email_document` adds that head only when the body contains MJML markup,** meaning a `class` starting `mj-`. A document of only hand-written modules is byte for byte what it was ([[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]]).

**8. Square images are a content convention.** Nothing crops an image or checks its ratio. This is a known limit: an image that is not square is not caught.

**9. Existing `section_heading` values on image blocks are kept but not shown.** They stay in `module_data`, as point 5 says. Nothing migrates them.

**10. The reset that deletes retired blocks is filed as the chore task.** The Note "has not been filed yet" no longer holds.

**Done alongside, recorded in other records.**

- **[[ADR-131 — Email Module Templates Use MJML as Source Format]]'s addendum of 2026-10-15:** blocks are compiled when they are written.
- **[[ADR-197 — Images Are Brand Assets, Served Publicly From an Unguessable Path]]'s addendum "a library image always uses its own alt text".** As built:
  - forms hide each image's paired alt field;
  - the API's field descriptors for modules, content fields and profile fields now carry `alt`, which names that pair;
  - the Web address tab asks for the alt text and saves it with the address in one write.

**A correction to the first Note.** It says `source: "module"` stays because "the Headline block and the CTA use it". Neither does. Both are `cms: false`, so all their fields come from `module_data` without it, and neither manifest declares it. Today the retired Single Stack is the only manifest that declares `source: "module"` ([[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]], addendum 2026-10-15).

## Related ADRs

### Depends On
- [[ADR-131 — Email Module Templates Use MJML as Source Format]] — the blocks' source format, and its 2026-10-15 addendum on when they are compiled.
- [[ADR-177 — A Field Is Defined Once, Required Per Module]] — `body_long` and the CTA's second label and link are defined in `storage/fields.json`.
- [[ADR-162 — Channel Rendering and Artifacts]] — the email renderer that assembles the blocks.
- [[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]] — the visible header and footer, and the decorative marker.
- [[ADR-193 — An Email's Legal Footer Is Fixed, Its Visible Header and Footer Are Placed Modules]] — where the visible header and footer were first decided (superseded by ADR-194).
- [[ADR-197 — Images Are Brand Assets, Served Publicly From an Unguessable Path]] — the square `image_url` is a library image or an https address.
- [[ADR-086 — Decision Slots Fail Gracefully]] — a Column bound to a slot that finds nothing is hidden like any other slot module.
- [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] — frozen snapshots keep rendering Single Stack, and reconstructions report the template change.
- [[ADR-187 — A Manager Hides Fields Per Module, and Required Means Required When Shown]] — hidden fields apply to each Column as a module of its own.
- [[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]] — module-sourced fields; `section_heading`'s first use is withdrawn.
