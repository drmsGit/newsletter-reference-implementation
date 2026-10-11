---
type: adr
status: accepted
topic:
  - architecture
  - rendering
  - compliance
  - brand
  - modules
  - consent
created: 2026-10-11
modified: 2026-10-11
source:
  - "task-350 design session on brand profiles, decided by the user 2026-10-11, one question at a time"
depends_on:
  - "[[ADR-193 — An Email's Legal Footer Is Fixed, Its Visible Header and Footer Are Placed Modules]]"
  - "[[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]]"
  - "[[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]]"
  - "[[ADR-163 — Per-Channel Consent and Addressability]]"
  - "[[ADR-150 — Tenancy and Access Model]]"
  - "[[ADR-153 — Audit and Accountability]]"
  - "[[ADR-131 — Email Module Templates Use MJML as Source Format]]"
  - "[[ADR-086 — Decision Slots Fail Gracefully]]"
  - "[[ADR-160 — Channel Model and Composition]]"
---

## Status
Accepted

## Context

**[[ADR-193 — An Email's Legal Footer Is Fixed, Its Visible Header and Footer Are Placed Modules]] decided, on 2026-10-10, what a recipient sees at the top and bottom of an email.** It had seven points. Two of them set up a "brand profile" without designing it: point 2 put named legal-detail sets in it, and point 3 added a few colour and font values. Queue task-350 is the build of those two points. Its final-design pass began on 2026-10-11 with a design session on brand profiles. The user decided every point below in that session, one question at a time.

**The session turned two things into one.** ADR-193 had legal-detail sets on one side and theme values on the other. The user made them one concept: a **brand profile** that carries an email's look, its texts, its links and its legal details. One choice per email then decides all of them. The use cases the user named:

- a flashy marketing look, a calm transactional one, a dark Black Friday one;
- different header menus, hotlines and footer texts per profile.

**The session also moved where the designed header and footer get their content.** ADR-193 point 2 said they take it "like any module: from content records". They now render from the profile.

**What exists today (verified 2026-10-11).**

- **A brand holds a key and a name, nothing else.** `BrandDB` has `id`, `key`, `name` and `created_at` (`backend/app/auth/db_models.py:35-38`).
- **The fixed footer line is marketing-only and English.** The frame renderer appends it and puts the link in the envelope as `list_unsubscribe` (`backend/app/rendering/frame.py:310-317`). The line is `footer_html` (`backend/app/subscriptions/texts.py:12-18`): the brand name and an "Unsubscribe" link, worded in code. Its input comes from `footer_for` (`backend/app/subscriptions/service.py:54-66`), which returns `None` for a message that is not email or not marketing (`:61-62`).
- **One stylesheet for the installation.** `storage/modules/email/brand.css` is read once and cached (`_load_brand_css`, `backend/app/rendering/service.py:43-47`) and inlined by `css_inline` (`:33`). It holds concrete values; nothing in it varies by brand.
- **Module templates are `.html` tables with Jinja,** for example `storage/modules/email/hero.html`. [[ADR-131 — Email Module Templates Use MJML as Source Format]] names MJML as the source format and keeps raw HTML as an escape hatch. `module_html` (`backend/app/rendering/service.py:343`) wraps each module and writes its type as `data-module-type`.
- **Every send is a marketing send.** The consent stage of the send-time exclusion stack asks for a grant for `(channel, purpose)` (`backend/app/delivery/exclusion.py:189-217`). The purpose vocabulary has one entry, `marketing`, and it is never a default (`backend/app/recipients/consent.py:34-40`, task-42). "Every planned send today is a marketing send" (`backend/app/delivery/service.py:640`). Audience assembly runs the same stack with `MARKETING` (`backend/app/audience/service.py:1068`).

**Why this supersedes ADR-193 instead of adding a dated addendum.** The decision rewrites three of ADR-193's seven points:

- point 1's content source for the designed header and footer (now the profile, not content records);
- point 2 (named legal-detail sets become brand profiles);
- point 3 (per-brand colour and font become profile fields).

The rules forbid rewriting an Accepted Decision in place. An addendum that replaced three of seven points would leave a Decision that mostly says what is no longer in force. That is the reasoning [[ADR-186 — In the Composer an Override Is the Default and a Catalogue Edit Is Explicit]] gave when it superseded ADR-178. **This is the third supersession in the repository,** after [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] over ADR-001 (2026-09-12) and ADR-186 over ADR-178. The points of ADR-193 that still hold are restated below, so this record can be read on its own. Each cites ADR-193 as its origin. That includes ADR-193's addendum of 2026-10-10 on the envelope rename.

**Options not taken.** Holding the profile's structure in code was not taken: one company declares two font sizes, another four, and the user wanted IT to change that in a normal deployment, not in a code change. Choosing the profile per campaign was not taken: per variant allows A/B tests of designs and matches the freeze, which is one snapshot per variant. A separate dark-mode logo was not taken: mail programs cannot be told to swap images.

## Decision

### What changes: ADR-193 points 1 (content source), 2 and 3

**1. A brand has brand profiles, as many as it needs.**

- **The first profile is the default.** The default can be changed, by marking another profile default. It cannot be deleted.
- **A profile can be duplicated.**
- **Deleting a profile that unsent variants use makes those variants fall back to the default.** The composer says so.
- **Frozen snapshots keep the deleted profile's values** (point 4).

**2. The profile's structure is declared at setup, not fixed in code.**

- **A deploy-time file, `storage/brand_profile.json`, declares the fields.** Each field has a name, a type, a label, whether it is required, and a group. The types are colour, font family, size, image, text, url and number. The file sits beside the module manifests and is changed the same way.
- **One company declares two font sizes, another four.** IT changes the file in a regular deployment.
- **A fixed core is always present,** because the platform relies on it: legal company name, address, imprint URL, privacy URL and unsubscribe text. The setup file may add any further fields.

**3. The look comes from the profile.**

- **`brand.css` stays one shared file, and its values come from the profile.** It refers to profile fields by name. The renderer fills the values in before inlining, because email clients do not support CSS custom properties.
- **Profile values also reach the module templates as variables,** not only `brand.css`. Many MJML styles are tag attributes, not CSS ([[ADR-131 — Email Module Templates Use MJML as Source Format]]), so a stylesheet alone cannot carry them.

**4. The profile is chosen on the variant.**

- **Each variant picks a profile** from a dropdown of its brand's profiles, within the manager's permissions. The default is preselected.
- **A new variant takes the profile of the variant it is copied from,** otherwise the default.
- **Duplicating a campaign within a brand keeps the profiles.** Copying it into another brand uses that brand's default, which can be changed afterwards.
- **A snapshot freezes the chosen profile's values.** Editing a profile never changes an email already sent ([[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]]).

**5. Managing profiles is its own per-brand permission.**
Admin holds it. A Manager holds it if the company grants it. Every change is audited ([[ADR-153 — Audit and Accountability]]). Roles and permissions are rows, so granting it needs no code ([[ADR-150 — Tenancy and Access Model]] point 5).

**6. One profile per language.**
For example "Default DE" and "Default EN". The profile records its language, so the composer can warn when it does not match the audience's language. This follows the business decision "one variant per language" (P2-F2, `docs/playbook-strategy.md` §5).

**7. The visible header and footer take their content from the profile.**

- **The header and footer modules render from the variant's profile:** logo, menu links, hotline, footer texts.
- **The footer module adds one optional free text per email.**
- **A manager still places them, or leaves them out.** The fixed legal line is appended regardless (point 14).

**8. Legal details are on every email.**
Marketing, transactional and test sends all carry them. **Any send is refused while its profile lacks a required field.**

**9. A profile is marketing or transactional.**

- **The mark decides whether an email may go out without an opt-in consent check.** Every new profile is marketing by default.
- **Creating a transactional profile, or marking one transactional, needs a separate permission** and is audited.
- **Choosing a transactional profile on a variant shows a clear "sent without opt-in check" label** and is audited.
- **Duplicating a transactional profile keeps it transactional only for someone who holds that permission.** For anyone else, the copy is marketing.

**How this meets the consent model.** [[ADR-163 — Per-Channel Consent and Addressability]] keeps consent per `(recipient, channel, purpose)` (point 1) and gates every send per `(channel, purpose)` (points 6 and 7). Today the only purpose is `marketing`, and every planned send is a marketing send (task-42). A transactional profile is the first thing that makes a variant's send go out under another purpose. So this record decides **where** the marketing-or-transactional choice is made, and that a transactional email is not held to a marketing opt-in. It does not decide the transactional purpose itself. Which purposes exist, which other stages of the stack still apply to transactional mail, and how sender reputation is split stay with queue task-134, which also owns the purpose vocabulary (`backend/app/recipients/consent.py:38-39`). **The build must be designed together with the exclusion stack's consent stage,** and with audience assembly, which runs the same stack.

**10. The profile sets the unsubscribe line's text, not its link.**

- **The link stays the platform's per-recipient token link** ([[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]] point 2).
- **Every marketing email keeps the one-click `List-Unsubscribe` header** (ADR-191 point 5).
- **A marketing profile must have unsubscribe text.** That keeps ADR-191 point 5's guarantee: a visible way out that no manager can remove.
- **A transactional profile may leave the text empty, and then no line is shown.** Some companies do show one on transactional mail. There, following it would put the recipient on a block list.
- **Further footer links go in free fields, or in extra core fields declared at setup.** For example a profile page, or other unsubscribe variants.

**11. The profile sets the link tracking parameters.**

- **The profile sets `utm_source` and `utm_medium`,** plus optional extra `key=value` pairs.
- **`utm_campaign` comes from the campaign and `utm_content` from the variant,** automatically.
- **They are added at render to content links.** Never to the unsubscribe, imprint or privacy links.

This is link tagging only. Open tracking is a separate open discussion (queue task-353).

**12. The manager app shows the working brand's logo, from its default profile — only the logo.**

- **The app keeps one palette and its fonts per installation,** IBM Plex Sans and IBM Plex Mono. The design draft `docs/design/DESIGN.md` says so: "the manager app is one palette per install, not per brand".
- **So the draft's colour meanings hold.** Teal marks what the system chose, ochre what a person pinned, and no brand accent or font can clash with them.
- **This replaces queue task-94's separate web palette idea for the app.** It is built in queue task-356.

**13. Not in a profile.**

- **Sender name, from-address and reply-to.** They belong to deliverability and provider setup.
- **A separate dark-mode logo.** Mail programs cannot be told to swap images. Logos are PNGs with a thin white edge.

### What carries over from ADR-193

**14. Two layers: a fixed legal part, and placed visible modules** (ADR-193 point 1).

- **The frame appends what must always be there:** the legal details and, where the profile has unsubscribe text, the unsubscribe line. No manager can remove it.
- **The designed visible header and footer are ordinary placed modules.** A manager may leave them out. Several footer variants are several footer modules, or several profiles.
- **"Every email has a footer" is guaranteed by the legal part,** not by forcing a module into the composition.

What changes against ADR-193 point 1 is only where the modules' content comes from (point 7).

**15. Decoration is a flag on the module type** (ADR-193 point 4).
A module manifest may declare `"decorative": true`. The visible header and footer are decorative; later, so is a section heading (queue task-108). The "nothing to show" floor of task-228 ignores decorative modules: an email holding only decorative modules plus the envelope still counts as nothing to show, and that recipient is skipped. This is the marker the 2026-10-08 addendum of [[ADR-086 — Decision Slots Fail Gracefully]] deferred.

**16. The logo is an https URL for now, and an asset later** (ADR-193 point 5).
Until asset management exists (queue task-112), the logo is an https image address in a profile image field. When assets land, the field holds an asset id.

**17. The envelope module is called `envelope`, and frozen frames still read as sent** (ADR-193 point 6 and its addendum of 2026-10-10). **Done in task-349** (commit `0d2ef14`).

- **Live module rows were renamed** from `header` to `envelope`. The name `header` is free for the visible logo header.
- **Frozen snapshot frames are never rewritten.** `module_html` writes each module's type into the HTML as `data-module-type`, so rewriting frozen frames would change the bytes of every email already sent and break ADR-183's hash check.
- **In a version-1 email frame, a `header` entry is the envelope.** The frame version (`FRAME_VERSION` is 2, `backend/app/rendering/frame.py:36`) keys the translation, so it can never be confused with the visible `header` module of a version-2 frame.

**18. A preference center is out of this record** (ADR-193 point 7).
It is its own parked task, task-348. The unsubscribe link covers the legal minimum.

### Open for the final-design passes

- **The exact core field names,** and which core fields the send check treats as required. Point 10 fixes one rule: unsubscribe text is required on a marketing profile.
- **How `brand.css` refers to profile fields.** For example a `var(--name)` that the renderer resolves, or a template syntax. And how MJML tag attributes take profile values.
- **How the composer's language warning works,** including where the audience's language is read from.
- **How a transactional send meets the exclusion stack** (point 9).

## Consequences

### Positive

- **One choice per email carries look, texts, links and legal details.** A manager picks a profile on the variant, and nothing else has to agree with it.
- **Footer variety without per-email content.** Hotlines, menus and footer texts differ per profile, not per content record.
- **The structure fits each company without code changes.** A company declares its own fields in `storage/brand_profile.json`; IT deploys it.
- **The legal minimum cannot be dropped.** The core is always present, the frame appends the legal part to every email, and a send is refused while a required field is empty.
- **Designs can be A/B tested.** Two variants with two profiles are an ordinary A/B test.
- **What was sent stays provable.** The profile's values are frozen with the snapshot, so editing or deleting a profile changes no email already sent.
- **Recipient-facing footer text can follow the language.** One profile per language carries its own unsubscribe and footer texts.

### Negative

- **A setup file and a profile editor are new surface.** They need schema, a migration, validation of the setup file against the core, a Settings screen and a picker on the variant.
- **The transactional mark is a powerful switch.** A profile marked transactional sends without an opt-in check. Its guard (a separate permission, audit, a visible label, and copies that fall back to marketing) is what stands between it and a marketing email sent without consent.
- **Variants of one campaign can look different by mistake.** The choice is per variant, so two variants may carry different profiles without anyone meaning it. They may even differ in purpose: one marketing, one transactional.
- **A send can be refused for a missing profile field.** That now includes transactional and test sends, so an incomplete profile blocks every kind of send that uses it.
- **This is the third supersession** (ADR-165 over ADR-001, ADR-186 over ADR-178). ADR-193 was accepted one day earlier, and its build had already begun (task-349 is done under it).

## Notes

- **ADR-193's open points this record settles.**
  - *Which level picks the legal set when both a campaign and a variant pick one:* only the variant picks (point 4).
  - *Whether transactional mail and test sends carry the legal details:* they do (point 8).
  - *Whether per-brand theme values join ADR-183's fingerprint or are frozen like the legal set:* they are frozen with the snapshot, as the profile's values (point 4). `brand.css` itself stays a shared file, so ADR-183 point 1's fingerprint of templates and brand CSS still covers it.
- **Not a supersession of ADR-191, and ADR-191's Decision is not edited.** Point 10 keeps the per-recipient token link, the one-click header on every marketing email, and point 5's guarantee of a visible link. Two readings change.
  - ADR-191 point 7 put all recipient-facing wording in one module, in English. The unsubscribe line's text now comes from profile data, one profile per language. The confirm page and its texts stay in `backend/app/subscriptions/texts.py`.
  - ADR-191's addendum of 2026-10-10 says the legal details are "taken from a brand profile (ADR-193 point 2)". The source is now this record.

  ADR-191's dated addendum of 2026-10-11 records both readings and points here.
- **Point 12 was narrowed before this record was committed.** The session first decided that the manager app takes accent colour, logo and font from the default profile (question 6); after reading the design draft `docs/design/DESIGN.md` the same day (2026-10-11), the user narrowed it to the logo only, before this record was committed.
- **Old deliveries must still reconstruct as sent.** No frame frozen so far holds profile values. The footer inputs of those deliveries are recorded in their delivery records (ADR-191, Notes). A reconstruction must therefore never pick up today's profile for an old frame. The frame version is the mechanism point 17 already uses for this kind of change.
- **Templates today are not MJML.** Point 3 asks for profile values to reach templates as variables. Today's `.html` Jinja templates already take variables, so this works for them as for the MJML source ADR-131 names. ADR-131 compiles MJML in the frontend layer, so the variables must exist before that step.
- **Link tagging and the content-id carrier are both link parameters written at render.** Point 11's UTM tags serve the company's web analytics. The carrier of [[ADR-102 — Rendering Prepares Tracking Metadata]] and [[ADR-182 — A Click Credits Content Only When the Link Names It]] point 5 serves attribution. Neither replaces the other. The pass that builds one should place both.
- **Not stated in the session, and so left to the passes.**
  - Where the footer module's per-email free text (point 7) is held.
  - What following an unsubscribe line on a transactional email writes. ADR-191 point 4 says transactional messages are never affected by an opt-out, and `footer_for` mints a token only for marketing (`backend/app/subscriptions/service.py:61-62`). Point 10's "block list" goes beyond both. Suppression is task-134's and task-135's ground.
  - The scope of the transactional permission. By [[ADR-150 — Tenancy and Access Model]]'s addendum of 2026-09-15, a permission is brand-scoped when the rows it guards carry a brand. Profile rows do, so it would be brand-scoped like the permission in point 5. That is an inference, not something the session stated.
- **The consent purpose split.** [[ADR-122 — Minimal Consent Model Required]] makes marketing versus transactional the base consent distinction. Its addendum of 2026-09-12 says ADR-163's `(channel, purpose)` grid is the concrete shape that distinction takes. Point 9 adds no purpose to that grid. It decides where the switch sits; the purpose behind it is task-134's.
- **Still owed from ADR-193.** The docstring of `footer_html` (`backend/app/subscriptions/texts.py:13-14`) says the line lasts "until task-301's designed footer replaces it". Rewording it belongs to task-350.
- **The decision log.** `docs/playbook-strategy.md` §5 has the 2026-10-10 entry behind ADR-193. Its point 2 ("a campaign may pick another") and point 3 ("their own colour and font, on top of the shared stylesheet") are replaced by this record. There is no entry yet for the 2026-10-11 session. The reasoning here comes from task-350's notes of 2026-10-11.

## Addendum 2026-10-11 — slice 1's final-design pass

**Slice 1's final-design pass (queue task-350) settled the first item of "Open for the final-design passes" above, and several build questions the session had not stated.** The user decided them on 2026-10-11. Points marked *agreed default* are technical defaults that the user agreed to in the same pass. Points 1–18 of the Decision are unchanged. Task-350's implementation plan holds the full map of where each part lands.

**1. The core field names and the field types.**

- **The core fields are** `legal_company_name`, `legal_address`, `imprint_url`, `privacy_url` and `unsubscribe_text`.
- **The field types are** `colour`, `font_family`, `size`, `image`, `text`, `url` and `number`: point 2's list, as names.
- **A field name must match `[a-z][a-z0-9_]*`.**
- **`storage/brand_profile.json` may relabel or regroup a core field.** It may never change a core field's type or its required flag.
- **The shipped file declares no fields beyond the core** (agreed default).

**2. Which fields a send requires.**

- **Always:** legal company name, address, imprint URL and privacy URL.
- **On a marketing profile, also the unsubscribe text.** This is point 10's rule.
- **The setup file can add required fields.** It can never make a core field optional.

**3. The footer's link labels are the platform's, not the profile's.**

- **"Imprint" and "Privacy" come from a built-in table per language:** English and German, falling back to English. They are not profile fields.
- **The profile's whole unsubscribe text is the link.**

**4. Every existing brand gets one profile.**

- **It is named "Default",** with language `en`, marked marketing, and unsubscribe text "Unsubscribe".
- **Its legal fields are left empty.** Legal values are never guessed from the brand name.
- **Every brand always has a default profile,** including brands created later.
- **Profiles are deleted with their brand.** They do not block a brand's deletion; its campaigns already do.

**5. Old snapshots and old frames.**

- **An unsent send holding a snapshot made before brand profiles is refused:** "made before brand profiles; take a new snapshot". This is how [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] point 6 treats snapshots made before frames.
- **Email frames that freeze a profile are frame version 3.**
- **Older frames keep today's footer line byte-for-byte,** so deliveries already sent reconstruct exactly.
- **The legacy line must never change.** That is `footer_html` and `FOOTER_STYLE` in `backend/app/subscriptions/texts.py`. `templates_fingerprint` (`backend/app/rendering/frame.py:78-91`) hashes only the files in the channel's module directory, and `texts.py` is not among them. A change to the line would break the hash check of every delivery already sent, while `templates_match` still reported the layout as unchanged. The rewording of the `footer_html` docstring that Notes lists as owed is done in 1b, and it says this.

**6. Where an incomplete profile is refused** (agreed default).

- **At send time, not at snapshot time,** with warnings in the composer beforehand. This is the convention already used for missing required content. An incomplete profile can be saved.
- **Test sends are refused too,** naming the missing fields.
- **A test send carries the legal footer, with the unsubscribe text shown unlinked and no `List-Unsubscribe` header.** A test send has no token ([[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]], Negative).

**7. Transactional profiles wait for their guard** (agreed default).
The kind is stored, but the API refuses `transactional` until queue task-355 builds point 9's guard. So no transactional profile can exist without that guard. The transactional permission is not declared until then either. Until task-355, every profile is marketing.

**8. The audit records which fields changed, never their values** (agreed default).
A value may hold an email address, and the audit writer refuses those ([[ADR-153 — Audit and Accountability]], addendum of 2026-10-08).

**9. Writes are people-only** (agreed default).
This is the same rule as for settings. Point 5's permission is `brand_profiles.manage`, and it is brand-scoped. Admin holds it; a Manager holds it only if the company grants it.

**10. Slice 1 is built in two halves.**

- **1a, "profiles exist"** (queue task-350): the setup file, profiles, their screens and the choice on the variant. No email changes.
- **1b, "every email carries them"** (queue task-357): frame version 3, the legal footer on every email, and the refusals.

That way profiles can be filled in before enforcement starts. When 1b lands, every send of an existing campaign is refused until its brand's default profile has its legal fields filled. Planned sends holding an older snapshot need a new snapshot.

**Still open after this pass.**

- **The composer's language-mismatch warning,** including where the audience's language is read from.
- **How `brand.css` refers to profile fields, and how MJML tag attributes take profile values** (queue task-354).
- **How a transactional send meets the exclusion stack** (queue task-355).
- **What following an unsubscribe link on a transactional email writes.**
- **Where the footer module's per-email free text is stored** (queue task-351).

## Addendum 2026-10-11 (second) — the legal footer is a template file

**Starting slice 1b (queue task-357), the user decided on 2026-10-11 where the legal footer's markup lives.** Points 3 and 5 of the addendum above implied a function in `backend/app/subscriptions/texts.py`. It is a template file instead. Points 1–18 of the Decision are unchanged.

**1. The legal footer is a template file.**

- **Its markup lives in `storage/modules/email/_legal_footer.html`,** in the email template folder.
- **It is rendered with the same Jinja environment as module templates,** so it is autoescaped.
- **The built-in Imprint and Privacy labels live in it too,** per language: English and German, falling back to English. In German they read "Impressum" and "Datenschutz".
- **It is not a function in `texts.py`.**

**2. Why: only the template folder is fingerprinted.**

- **`templates_fingerprint` (`backend/app/rendering/frame.py:78-91`) hashes every file in the channel's module directory.** `texts.py` is not among them.
- **A footer kept in code could never be edited safely.** An edit would break `hash_matches` for every delivery sent with it, while `templates_match` still reported the layout unchanged. That is why the legacy `footer_html` line is frozen forever.
- **In the template folder, a later edit shows honestly as "templates changed".** For example when the designed footer of queue task-351 and task-354 arrives.

**3. The module registry skips template files whose name starts with an underscore.**
So the footer is not taken for a module without a manifest. Today the registry warns about every `.html` file that has no manifest (`backend/app/modules/registry.py:360-362`).

**4. The email fingerprint changes once** (accepted cost).
Adding the file changes the fingerprint, as adding any module does. Deliveries sent before it then report `templates_match` false. Their `hash_matches` is unaffected: frames below version 3 keep rendering the legacy `footer_html` line byte-for-byte.

**What still stands from the addendum above.**

- **Point 3:** the labels are still built in, not profile fields. Only the place they are written changes.
- **Point 5:** `footer_html` and `FOOTER_STYLE` still never change.

## Addendum 2026-10-11 (third) — slice 2's final-design pass: look values and link tags

**Slice 2's final-design pass (queue task-354) settled how profile values reach the look and the links.** The user decided points 1–4 on 2026-10-11, one question at a time. Points 5–8 are technical consequences settled in the same pass. Points 1–18 of the Decision are unchanged. Task-354's implementation plan holds the map of where each part lands.

**1. `brand.css` names a profile value as a standard CSS variable with its fallback.**

- **The form is `var(--field_name, fallback)`,** for example `color: var(--colour_text, #1a1a1a);`.
- **The renderer replaces every `var()` before the CSS is inlined:** with the profile's value, or with the fallback when the profile leaves the field empty.
- **No email ever contains `var()`.** Email clients cannot read CSS variables (Decision point 3).
- **`brand.css` stays valid CSS** that a designer can open in any tool, and every value has a visible default.
- **Only colour, size, font family and number values are filled in.** Any other field named in `brand.css` falls back.

**2. The shipped setup file declares a starter set of look fields.**

- **They are taken from today's `brand.css`,** each with today's value as its fallback, in the group "Look": text colour, body text colour, button colour, button text colour, hero background, font family, headline size, body size and button corner radius.
- **Task-354's plan names them** `colour_text`, `colour_body_text`, `colour_button`, `colour_button_text`, `colour_hero_background`, `font_family`, `size_headline`, `size_body` and `radius_button`.
- **Nothing looks different until a profile fills one.**
- **This replaces slice 1's default** "the shipped file declares no fields beyond the core" (point 1 of the first addendum above), for these look fields.

**3. UTM tags go on every http(s) link a module renders.**

- **That is content links and typed-in static buttons,** and later the menu links of the header and footer modules.
- **Never the legal footer's** imprint, privacy or unsubscribe links.
- **A key the link already carries is kept.**
- **No tags at all unless the profile sets `utm_source`.**
- **The click-attribution parameter `nl_content` is separate and unchanged** ([[ADR-182 — A Click Credits Content Only When the Link Names It]]). Links are tagged after it is written.

This makes Decision point 11's "content links" concrete.

**4. `utm_campaign` and `utm_content` are the campaign's and the variant's names as slugs.**

- **A slug is lowercase; any other character becomes a hyphen.** For example `utm_campaign=spring-sale-2026`.
- **They read plainly in analytics,** without a lookup table.
- **Two campaigns with the same name share a label.** The user accepted this.
- **They are frozen at snapshot time.** Renaming a campaign after the send does not change what was sent.

**5. Theme values are frozen with the profile.**

- **The version-3 frame already holds all of a profile's values** (queue task-357). So a rebuilt email keeps the colours it was sent with.
- **The frozen link parameters sit beside the profile in the frame.**
- **There is no frame-version bump.** Frames without them render as before.

**6. `utm_source`, `utm_medium` and `utm_extra` are core fields.**

- **They are optional,** in the group "Link tracking".
- **`utm_extra` holds further `key=value` pairs,** one per line.
- **They are core because the platform reads them by name.** This adds to the core fields listed in point 1 of the first addendum above.

**7. The email fingerprint changes once** (accepted cost).

- **Editing `brand.css` changes the template fingerprint,** as any template edit does.
- **The inlined output of older frames stays byte-identical.** The CSS inliner drops the style block after inlining, and the fallbacks equal today's values.

**8. Profile values also reach the module templates as `profile.<field>`.**
This is Decision point 3's second half. Today's `.html` templates can use it now. When templates move to MJML ([[ADR-131 — Email Module Templates Use MJML as Source Format]], not built yet), tag attributes can take profile values the same way.

**What this pass settles.**

- **"How `brand.css` refers to profile fields, and how MJML tag attributes take profile values"** from the open list of the first addendum above.
- **The Notes item that the pass building link tagging or the content-id carrier "should place both".** Both are written at render, UTM after `nl_content`, and neither replaces the other.

**Negative consequences of this pass.**

- **Same-named campaigns share a `utm_campaign` label.** Analytics cannot tell them apart by that tag.
- **Which `brand.css` values a profile may change is limited to the declared field types.** Colour, size, font family and number are filled in; nothing else is.
- **A new value in `brand.css` is fillable only once the setup file declares it.** Until then it always shows its fallback.

## Addendum 2026-10-11 (fourth) — slice 3's final-design pass: the header and footer modules

**Slice 3's final-design pass (queue task-351) settled how the visible header and footer modules are built.** The user decided points 1–3 on 2026-10-11, one question at a time. Points 4–8 are technical consequences settled in the same pass. Points 1–18 of the Decision are unchanged. Task-351's implementation plan holds the map of where each part lands.

**1. Link lists are a new field type, `links`.**

- **A `links` field is a text box with one link per line,** written as `Label | https://address`.
- **It holds any number of links,** in the order written.
- **It is checked on save.** Every line needs a label and an https address.
- **This adds an eighth type** to the seven listed in point 1 of the first addendum above.

**2. The shipped setup file declares the header and footer fields.**

- **Group "Header":** logo (image), logo alt text (text), logo links to (url) and menu links (links).
- **Group "Footer":** footer links (links), service hotline (text) and footer text (multi-line text).
- **Task-351's plan names them** `logo`, `logo_alt`, `logo_link`, `menu_links`, `footer_links`, `service_hotline` and `footer_text`.
- **An empty field leaves its part out of the email.**
- **This adds to the look fields** of point 2 of the third addendum above.

**3. https everywhere.**

- **`url`, `image` and `links` fields refuse `http://` addresses.** That includes the core imprint and privacy links.
- **Many mail programs block or flag images loaded over plain http.** Task-351's notes had asked for the logo to be https.
- **A value already saved is refused only on its next save.**
- **Frozen frames are not touched.**

This extends Decision point 16, which named only the logo, to every address a profile holds.

**4. The header and footer are modules.**

- **They live in `storage/modules/email/header` and `footer`,** with `cms` false.
- **A manager places them or leaves them out** (Decision point 14). They render from the email's brand profile (Decision point 7).
- **The header has no fields of its own.**
- **The footer has one optional per-email field, `footer_note`** (multi-line). It is shown before the profile's footer content.
- **The fixed legal footer still follows,** appended by the frame.

**5. Module manifests gain the key `decorative`, default false.**

- **The nothing-to-show check skips decorative modules.** That is `what_rendered` (`backend/app/rendering/frame.py:257`), from the 2026-10-08 addendum of [[ADR-086 — Decision Slots Fail Gracefully]].
- **An email holding only decorative modules and the envelope is skipped as nothing to show.**
- **Both new modules are decorative.**

This makes Decision point 15 concrete.

**6. Their links carry the profile's UTM tags, never the click-attribution parameter.**

- **The tags are those of point 3 of the third addendum above.**
- **`nl_content` is never written on them.** They are not content ([[ADR-182 — A Click Credits Content Only When the Link Names It]] point 3).

**7. A version-1 frame still reads its `header` module as the envelope.**

- **The translation stays keyed on the frame version** (Decision point 17, task-349).
- **The visible header exists only in frames of version 2 and later.**
- **There is no frame-version bump.**

**8. Templates read a link list through a template filter, `links`.**

**What this pass settles.**

- **"Where the footer module's per-email free text is stored"** from the open list of the first addendum above, and the matching Notes item: in the footer module, as its `footer_note` field.
- **The decorative marker of Decision point 15:** a manifest key, default false, read by `what_rendered`.

**Negative consequences of this pass.**

- **A `links` box relies on a typed format.** A mistake shows only on save.
- **https everywhere may refuse a company's existing http imprint link** on its next save.
- **A footer's per-email note lives in the module.** It is not shared between emails.

## Addendum 2026-10-11 (fifth) — narrowed by ADR-195

**[[ADR-195 — A Transactional Send Skips the Opt-In Check, Never Provider Suppression]] (queue task-355) narrows two of this record's points without superseding them.** Points 1–18 of the Decision are unchanged. Read points 1 and 10 together with this addendum.

**1. A transactional profile is never the default** (ADR-195 point 4).

- **Decision point 1 lets any profile be made the default:** "The default can be changed, by marking another profile default."
- **A transactional profile never can be.** Making one the default is refused. Marking the default transactional is refused.
- **So a variant becomes transactional only when someone picks such a profile.**

**2. A transactional email shows no unsubscribe line, in this slice** (ADR-195 point 3).

- **Decision point 10 lets a transactional profile carry unsubscribe wording:** "Some companies do show one on transactional mail."
- **A transactional email shows no unsubscribe line and no one-click header,** even when its profile has the wording.
- **What an unsubscribe on transactional mail would mean stays open.** It is still the item "What following an unsubscribe link on a transactional email writes" in the first addendum's open list.

**3. The transactional permission is `brand_profiles.transactional`** (ADR-195 point 5).
It is brand-scoped, as Notes inferred.

**4. Point 7 of the first addendum above is done.**
It said the API "refuses `transactional` until queue task-355 builds point 9's guard". Task-355 has built the guard (commit `68c7f1f`), so transactional profiles can now exist.

**What this settles.**

- **"How a transactional send meets the exclusion stack"** from the Decision's open list and the first addendum's: ADR-195 points 1 and 2.

## Related ADRs

### Supersedes
- [[ADR-193 — An Email's Legal Footer Is Fixed, Its Visible Header and Footer Are Placed Modules]] — its points 1 (content source), 2 and 3 are rewritten here as points 1–13. Its points 1, 4, 5, 6 (with the 2026-10-10 addendum) and 7 are restated as points 14–18.

### Depends On
- [[ADR-191 — Unsubscribe Is a Per-Message Token, a Confirm Page and One-Click]] — the token link, the one-click header and the visible-link guarantee that point 10 keeps.
- [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] — the freeze that holds the profile's values.
- [[ADR-163 — Per-Channel Consent and Addressability]] — consent per purpose and the exclusion stack that point 9 must meet.
- [[ADR-150 — Tenancy and Access Model]] — brands, and permissions as rows.
- [[ADR-153 — Audit and Accountability]] — every profile change and every transactional choice is audited.
- [[ADR-131 — Email Module Templates Use MJML as Source Format]] — why profile values must reach templates as variables.
- [[ADR-086 — Decision Slots Fail Gracefully]] — the floor whose decorative marker point 15 carries over.
- [[ADR-160 — Channel Model and Composition]] — variants, and two files per email module.

### Referenced By
- [[ADR-195 — A Transactional Send Skips the Opt-In Check, Never Provider Suppression]] — narrows points 1 and 10, and builds point 9's guard (fifth addendum of 2026-10-11).
