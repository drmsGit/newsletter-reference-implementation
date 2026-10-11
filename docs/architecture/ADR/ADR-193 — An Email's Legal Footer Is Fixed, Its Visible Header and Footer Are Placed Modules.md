---
type: adr
status: superseded by ADR-194
topic:
  - architecture
  - rendering
  - compliance
  - brand
  - modules
created: 2026-10-10
modified: 2026-10-11
source:
  - "task-301 design session, decided by the user 2026-10-10, one question at a time"
depends_on:
  - "[[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]]"
  - "[[ADR-086 — Decision Slots Fail Gracefully]]"
  - "[[ADR-150 — Tenancy and Access Model]]"
  - "[[ADR-160 — Channel Model and Composition]]"
  - "[[ADR-131 — Email Module Templates Use MJML as Source Format]]"
  - "[[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]]"
  - "[[ADR-163 — Per-Channel Consent and Addressability]]"
---

## Status
Superseded by ADR-194

## Context

**What the recipient sees at the top and bottom of an email does not exist yet.** The user raised it on 2026-10-08, after task-228. There is no visible header (a logo, perhaps a navigation bar) and no designed footer (company details, links, special texts). Queue task-301 collected the questions. This record answers them.

**Two different things are both called "header".**

- **The envelope module.** In code it is named `header` (`storage/modules/email/header.json` and `.html`). It holds the subject and the preheader. Both fields are marked `"envelope": true` in `storage/fields.json` (`:94` and `:133`). It renders only a hidden preheader span. It is what the 2026-10-08 addendum of [[ADR-086 — Decision Slots Fail Gracefully]] calls the envelope.
- **The visible header.** This is what the recipient sees. It does not exist.

**What exists today (verified 2026-10-10).**

- **A fixed footer line on every marketing email, since task-56.** [[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]] point 5 added it. The frame renderer appends it and sets the `List-Unsubscribe` envelope entry (`backend/app/rendering/frame.py:285-292`). The line itself is `footer_html` (`backend/app/subscriptions/texts.py:12-18`): the brand name and an unsubscribe link. Its input comes from `footer_for` (`backend/app/subscriptions/service.py:54-66`). That function returns `None` for a message that is not email or not marketing (`:61-62`). So transactional mail carries no line, as [[ADR-163 — Per-Channel Consent and Addressability]] requires for purpose. The line's inputs are copied into the delivery record (`backend/app/delivery/service.py:1322-1323`), so a reconstruction renders the same footer.
- **A brand holds a key and a name, nothing else.** `BrandDB` has `id`, `key`, `name` and `created_at` (`backend/app/auth/db_models.py:35-38`). There is no logo, no company details and no legal links per brand. Yet an installation has several brands ([[ADR-150 — Tenancy and Access Model]]).
- **One stylesheet for the whole installation.** `storage/modules/email/brand.css` is loaded once (`backend/app/rendering/service.py:35-47`) and inlined by `css_inline` (`:33`). Open queue task-94 (brand theming, not an ADR) decided on 2026-07-26 that email keeps this one full-CSS file.
- **The floor of task-228 knows only the envelope.** `what_rendered` (`backend/app/rendering/frame.py:190-213`) counts any module except the envelope module as meaningful. It finds the envelope through the manifests (`envelope_module_type`, `backend/app/modules/registry.py:440-454`), not by the name `header`. The send loop skips a recipient for whom nothing meaningful rendered (`backend/app/delivery/service.py:1240-1246`). ADR-086's addendum, point 2, deferred a "decorative" marker until a footer or divider module existed. Its Consequences warn that the floor is wrong until such a module gets one.
- **There is no asset management.** Queue task-112 records this: no table, no upload route, no picker. A logo cannot be an asset id today.

**ADR-191 point 5 expected the designed footer to replace the line.** It said: "The designed visible footer of task-301 replaces that line, and it must keep the link." The design session went another way. The line is not replaced. It stays, and it grows (point 1 below). The part of point 5 that matters is the guarantee: every marketing email has a visible way out. That guarantee holds, and it is now independent of what a manager builds. So this record does not supersede ADR-191, and ADR-191's Decision is not edited (Notes).

**How the questions were weighed.** The user decided seven points on 2026-10-10, one question at a time. Two earlier inputs shaped the first one. On 2026-10-08 the user had said that even one brand may need several footers: with an unsubscribe link, without one, or with special texts. And he leaned toward "brands have to use the same basic structure".

- **One fixed frame per brand, with switches**, was not taken. Every footer variation would become a new switch in the frame. Variety is what modules already provide.
- **Placed modules only, with one required footer module**, was not taken. A required module still has to be built correctly. A badly built footer could miss the legal details, and nothing in the frame would notice.
- **For the legal details, a designated "legal" content record** was not taken. The frame would depend on a record that a manager can edit or archive like any other.
- **A configuration file for the legal details** was not taken. Changing an address would need a deploy.

## Decision

**1. Two layers: a fixed legal footer, and placed visible modules.**

- **The frame keeps appending what must always be there.** That is the unsubscribe line of ADR-191 point 5, extended with the brand's legal details (point 2). Every marketing email therefore has a legal footer that no manager can remove.
- **The designed visible header and footer are ordinary modules.** The header holds a logo. The footer holds links and special texts. A manager places them like any other module, and may leave them out.
- **Several footer variants per brand are several footer modules.** Nothing new is needed for variety.
- **"Every email has a footer" is guaranteed by the legal part,** not by forcing a module into the composition.

**2. Legal details live in a brand profile, and may differ within a brand.**

- **The brand profile holds several named legal-detail sets.** Each set holds the legal company name, the address, an imprint link and a privacy link. One set per brand is marked default.
- **A campaign or variant may pick another set.** Otherwise the brand's default applies.
- **The frame reads the chosen set at render.**
- **A snapshot freezes the chosen set,** as it freezes other content ([[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]]). A reconstruction then shows what was sent, even after the profile has changed.
- **A send is refused while the applicable set lacks a legally required field.** German law requires an imprint.
- **The designed header and footer modules take their content like any module:** from content records, which already belong to one brand.

**3. The same structure for every brand, with a per-brand look.**

- **Brands use the same modules.** There are no per-brand templates.
- **The brand profile also carries a few theme values: colour and font.** They are applied on top of the shared `brand.css` at render.
- **`brand.css` stays the shared full-CSS stylesheet for structure.** Task-94's email decision stands for structure. The per-brand values are new.
- **How the values are applied is not decided here.** Email clients handle CSS custom properties poorly, so the values must be resolved at render or during inlining. That is left open for the final-design pass.

**4. Decoration is a flag on the module type.**

- **A module manifest may declare `"decorative": true`.** The visible header and the footer are decorative. Later, so is a section heading (queue task-108).
- **The "nothing to show" check of task-228 ignores decorative modules.** An email that holds only decorative modules plus the envelope still counts as nothing to show, and that recipient is skipped.
- **This is the marker that ADR-086's 2026-10-08 addendum deferred.** Its point 2 said a decorative module would get a manifest marker "decided at that time". This is that time. The addendum's own Decision is unchanged.

**5. The logo is an https URL for now, and an asset later.**

- **Until asset management exists (task-112),** the header's logo is an https image address in the header's content. It uses an existing field type.
- **When assets land,** the field becomes an asset id. The header logo is task-112's first user.

**6. The envelope module is renamed from `header` to `envelope`.**
That frees the name `header` for the visible logo header.

**How the rename is carried out is not decided here.** Stored data names `header`:

- module rows (`ModuleInstanceDB.module_type`, `backend/app/campaigns/db_models.py:86`);
- frames frozen in snapshots, which copy each module's type (`backend/app/rendering/frame.py:103`);
- delivery records, which must stay readable as sent (ADR-183).

The open choice is between two ways: migrate those rows, or let the readers also accept the old name. Rewriting a frozen record changes "what was sent". The final-design pass must choose with that in mind.

**7. A preference center is out of this record.**
A preference center is a page where a recipient chooses which newsletters or channels they get, not only "stop everything". It is filed as its own parked task, task-348. The visible footer has nothing to link to until it exists. The unsubscribe link covers the legal minimum.

## Consequences

### Positive

- **The legal minimum cannot be dropped by a manager.** The unsubscribe link and the legal details sit in the frame, not in a module.
- **Footer variety costs nothing new.** A variant is one more module.
- **Brand-specific content and look without per-brand templates.** Content comes from brand-owned content records. Legal details and theme values come from the brand profile.
- **A decorative module cannot make an empty email count as content.** The floor of task-228 stays true once header and footer modules exist.
- **What was sent stays provable.** The legal set is frozen with the snapshot, so a reconstruction shows the details that went out.

### Negative

- **The brand profile is new surface.** Named legal sets and theme values need schema, a migration and a Settings screen. A campaign or variant also needs a way to pick a set.
- **The envelope rename touches stored data.** Module rows, frozen frames and delivery records all name `header`. Either choice in point 6 carries a cost: a migration that rewrites records of what was sent, or readers that must accept two names for as long as old records exist.
- **Until task-112, a logo is a URL.** Anyone with edit rights on the content can point it at another image, and nothing checks what it points to.
- **Per-brand theme application is not designed yet.** Point 3 decides that the values exist, not how they reach an inlined email.
- **A send can now be refused for missing legal details.** A brand whose default set is incomplete cannot send marketing until someone fills it in.

## Notes

- **Not a supersession of ADR-191.** ADR-191 point 5 called the footer line "a minimal footer line now, until the designed footer replaces it", and its Negative list called the line "a stopgap". Point 1 above keeps the line, extends it and makes it permanent. The designed footer becomes a separate placed module. The part of point 5 that is a guarantee holds and is strengthened: the visible link is always there, and no designed footer can lose it. The expectation about how task-301 would deliver it is not carried out. This follows the precedent of ADR-191's own Notes, which treated a wording difference with ADR-169 the same way. Whether ADR-191 gets a dated addendum pointing here is left to whoever records it. The docstring of `footer_html` (`backend/app/subscriptions/texts.py:13-14`) also says the line lasts "until task-301's designed footer replaces it". That will be wrong once this record is built.
- **The relation to task-94.** Task-94 is an open queue task, not an ADR. Its 2026-07-26 direction gave email one full-CSS `brand.css` per installation, with no token set. Point 3 keeps that file for structure and adds per-brand colour and font values beside it. So task-94's email side widens from one file to one file plus per-brand values. Its own description already argued that email values must be baked in as concrete values, because email clients do not support CSS variables reliably. The renderer already inlines CSS with `css_inline` (`backend/app/rendering/service.py:33`). That is a starting point for the pass, not a decision.
- **For the final-design pass, beyond the open points above:**
  - **The rename (point 6).** The renderer looks up each frame entry's manifest and template by `module_type` (`backend/app/rendering/frame.py:269-278`). After the rename, a frozen entry named `header` would resolve to the new logo header, not to the envelope. And `what_rendered` finds the envelope by manifest attribute (`backend/app/modules/registry.py:440-454`), so a frozen `header` entry would no longer be recognised as the envelope. It would count as meaningful. Both effects follow from either choice and must be handled.
  - **Theme values and ADR-183.** ADR-183 point 1 freezes "a fingerprint of the templates and brand CSS used". Whether per-brand theme values join that fingerprint, or are frozen like the legal set, belongs to the same open question as point 3.
  - **Which fields are legally required.** Point 2 names the imprint as required under German law. Which of the four fields the send check requires, and whether that varies by jurisdiction, is not enumerated here.
  - **Where the pick of a legal set is stored.** Point 2 allows a campaign or a variant to pick one. Which level wins when both pick one is not stated.
  - **Transactional mail and test sends.** `footer_for` gives transactional mail no line, and a test send has no token (ADR-191, Negative). Whether either carries the legal details is not decided here. Transactional sends are queue task-134.
  - **The URL field.** The `url` field type exists (`storage/fields.json`, for example `image_url` at `:77-81`). The only check found is the editor's `<input type="url">` (`frontend/src/components/EditorFields.tsx:66`), which accepts any scheme. No server-side https check was found. Point 5 says "https", so the pass decides where that is enforced.
- **Module files.** A header and a footer module are each a `.json` manifest plus an `.html` template, as the 2026-10-09 addendum of [[ADR-160 — Channel Model and Composition]] describes for email modules. Their MJML source follows [[ADR-131 — Email Module Templates Use MJML as Source Format]].
- **No decision-log entry.** `docs/playbook-strategy.md` has no entry for this decision. Its §5 mentions the floor ("No 'decorative' marker until a footer or divider module exists") and ADR-191's interim footer line, and both are consistent with this record. The reasoning here comes from task-301's notes and the 2026-10-10 session.

## Addendum 2026-10-10 — the rename leaves frozen frames as they were sent

**Point 6 left open how the rename is carried out. Queue task-349's final-design pass settled it, decided by the user (commit `0d2ef14`).** Point 6 and the rest of the Decision above are unchanged.

**A finding came first.** `module_html` (`backend/app/rendering/service.py:343-379`) writes each module's type into the HTML as `data-module-type`. So rewriting frozen frames from `header` to `envelope` would change the bytes of every email already sent. Every past delivery would then fail its "matches what was sent" check, the artifact hash of [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]]. The user had first chosen to migrate everything, with a proof that the output stayed byte-identical. This finding showed that proof could not hold. The user then chose as follows.

1. **Frozen snapshot frames are never rewritten.** Live module rows were renamed (migration `backend/scripts/migrate_0043_envelope_module_rows.sql`). The manifest and template files are now `storage/modules/email/envelope.json` and `.html`.
2. **The frame version marks which name an entry uses.** `FRAME_VERSION` is 2 (`backend/app/rendering/frame.py`), and `is_frame` accepts versions 1 and 2.
3. **In a version-1 email frame, a `header` entry is the envelope.** Readers translate it in two places: for manifest and template lookups (`lookup_type`), and for the nothing-to-show floor (`what_rendered`). The HTML still names it `header`, so old emails render byte-identically.
4. **The translation is keyed on the frame version.** It can therefore never be confused with the visible `header` module of a version-2 frame (queue task-351).

**Proof on development data.** Nine sent deliveries were frozen with a `header` envelope. The one that reconstructed byte-for-byte before still does (`hash_matches`). The other eight are unchanged. `templates_match` flipped for that one delivery, because the template files changed: their names, and the manifest's label. That best-effort flag flips on any template edit. ADR-183 point 4 makes content exact and layout best-effort, so this is expected.

**Consequence.** A small, permanent translation for version-1 frames lives in the frame reader. It stays for as long as version-1 frames exist, which is for as long as their deliveries are kept. This is the second cost named in the Negative list above ("readers that must accept two names"), taken in a narrower form: the reader accepts the old name only in version-1 frames, not everywhere.

## Related ADRs

### Depends On
- [[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]] — the frame's unsubscribe line, which point 1 extends.
- [[ADR-086 — Decision Slots Fail Gracefully]] — the floor and its 2026-10-08 addendum, whose deferred decorative marker point 4 supplies.
- [[ADR-150 — Tenancy and Access Model]] — brands, which the brand profile extends.
- [[ADR-160 — Channel Model and Composition]] — two files per email module.
- [[ADR-131 — Email Module Templates Use MJML as Source Format]] — the source format of the new modules.
- [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] — the frozen frame and the delivery record, which the legal set and the rename must respect.
- [[ADR-163 — Per-Channel Consent and Addressability]] — purpose; transactional mail carries no unsubscribe line.

### Superseded By
- [[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]]
