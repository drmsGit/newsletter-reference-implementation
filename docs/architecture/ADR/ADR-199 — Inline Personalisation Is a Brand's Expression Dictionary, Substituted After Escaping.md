---
type: adr
status: accepted
topic:
  - architecture
  - rendering
  - personalization
  - snapshot
  - privacy
created: 2026-10-16
modified: 2026-10-16
source:
  - "task-365 design, decided by the user 2026-10-11, one question at a time (task Description, points 1–9)"
  - "task-365 final-design pass, decided with the user 2026-10-16, one question at a time (task Implementation Plan)"
depends_on:
  - "[[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]"
  - "[[ADR-162 — Channel Rendering and Artifacts]]"
  - "[[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]]"
  - "[[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]]"
  - "[[ADR-154 — Erasure and Retention]]"
  - "[[ADR-144 — AI Data and Model Governance]]"
  - "[[ADR-120 — CRM as Customer Source of Truth]]"
  - "[[ADR-121 — Minimal Recipient Model]]"
  - "[[ADR-126 — Maintain Local Recipient Projection]]"
  - "[[ADR-177 — A Field Is Defined Once, Required Per Module]]"
  - "[[ADR-063 — Rendering Parity Over Rendering Implementation]]"
  - "[[ADR-153 — Audit and Accountability]]"
---

## Status
Accepted

## Context

**The request began as "personalise the subject line" and was widened by the user** on 2026-10-11, while working queue task-60: *"instead of personalize subject line we need to think of personalize inline text as a general concept"*. A small set of named entries, usable in any text, then personalises the subject line, module text, content text and push alike. The model the user pointed to is Salesforce Marketing Cloud Next's "Expressions": a label such as `{{salutation}}` whose expression says something like "if firstname is not empty then Hallo Firstname, else Hallo,". The design is queue task-365.

**The user's catch sets the boundary.** Personalisation can only be as rich as what the CRM, or any other system, syncs into the platform or offers through an endpoint. This record builds the dictionary and three basic recipient fields, and two uses: Salutation informal ("Hallo Firstname") and Salutation formal ("Sehr geehrter Herr … / Sehr geehrte Frau …"). Anything more belongs to the "how data gets into the system" chapter (task-294, task-364).

**The ADRs already expect a merge mechanism, and none exists** (verified 2026-10-11 in task-365).

- [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]] defines a "Merge Context" that must remain available after delivery.
- [[ADR-144 — AI Data and Model Governance]] point 4 expects `{{first_name}}` to be filled locally at render.
- [[ADR-162 — Channel Rendering and Artifacts]] point 2 names the renderer contract `render(composition, merge_context)`. The code has no merge context. Its addendum of 2026-10-11 says a salutation in a subject comes from a brand's expression dictionary and gets its own ADR. This is that ADR.
- [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] point 7 leaves the merge context undecided: once substitution exists, the delivery record must gain it.
- [[ADR-154 — Erasure and Retention]] point 5 says rendered output holding merged personal data must be reachable by erasure.

**What exists in the code** (verified 2026-10-11 in task-365).

- **Recipients have only a schema-less attributes bag** (`backend/app/recipients/db_models.py:17`). Only `create_recipient` writes it, wholesale (`backend/app/recipients/service.py:240-300`), checked against a denylist (task-158). The demo seed puts only `{"firstname": name}` in it (`backend/scripts/seed_demo_data.py:209`). Nothing reads attributes while rendering.
- **Rendering has one autoescaped Jinja environment** (`backend/app/rendering/service.py:33`). Only template files are compiled. User text (module data, content fields, overrides) is passed as escaped data. **That must stay true: user text never goes through Jinja,** or it becomes a template-injection hole.
- **The envelope is copied raw from the envelope module** (`envelope_fields_for_variant`, `backend/app/rendering/service.py:225-257`) and frozen in the frame (`backend/app/rendering/frame.py`). The current frame version is 3, the version that freezes a brand profile ([[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]], addendum of 2026-10-11, point 5).
- **The preview's recipient picker exists** (`frontend/src/screens/Preview.tsx:183`) and today changes only slot picks.
- **The planned "Related Data Access" design interview sketches this area** (`docs/architecture/interview-prep/Related Data Access - design interview.md`, clusters B and C): restricted substitution rather than template evaluation, a mandatory fallback, preview with sample data, and the delivery record holding the values.

**Options not taken, with the reason given.**

- *A formula or expression language* was not taken. A form of cases has nothing to parse and nothing to inject (point 1).
- *Recipient fields written straight into a text* (`{{first_name}}` in a subject) were not taken. Every use must have a fallback, so there is never a "Hallo ," (points 8 and 9).
- *Substitution by rendering user text as a Jinja template* was not taken. It is the template-injection hole named above (point 10).
- *A personalised subject line as an override* will not be built. [[ADR-162 — Channel Rendering and Artifacts]]'s addendum of 2026-10-11 withdrew that reading: the envelope module is never overrideable, and per-recipient text is a separate mechanism.
- *A wholly different subject per recipient* is not this mechanism. It is separate variants, an AI case (task-125) or an automation (the same addendum).
- *Dynamic and personalised links* are a separate concept with their own task.
- *A recipient file import* is not part of this decision. The fields arrive through the recipients API and the demo seed. A file import is task-294's and task-364's chapter (decided 2026-10-16).

**No supersession.** This record decides what [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] point 7 explicitly left open, and gives shape to what ADR-005 and ADR-162 point 2 already name. No Accepted Decision section is changed.

## Decision

### The dictionary

**1. Expressions are cases, not formulas.**

- **An entry is an ordered list of cases per language, plus a required fallback per language.**
- **Each case tests one recipient field:** the field is filled, is empty, or equals a value.
- **Example, Salutation formal in German:** gender is female gives "Sehr geehrte Frau {{last_name}}"; gender is male gives "Sehr geehrter Herr {{last_name}}"; otherwise the fallback "Sehr geehrte Damen und Herren".
- **This is a form, not a language.** Nothing in an entry is parsed as code, so there is nothing to inject.
- **It carries further with more operators on typed fields,** for example a CRM tier equal to VIP gives "20 %", otherwise "10 %"; a score of at least 80; a last purchase within 90 days. Those come later, with typed attribute fields (point 2).

**2. Three recipient fields become real columns.**

- **`gender`, `first_name` and `last_name` are columns on the recipient,** written through the recipients API and filled by the demo seed.
- **`gender` is `female`, `male`, `diverse` or empty.** Anything else is refused at the API with a clear error. The CRM maps its own values onto these four.
- **No recipient file import is part of this decision** (decided 2026-10-16). That is task-294's and task-364's chapter.
- **Typed attribute fields (text, number, date) and further operators come later,** declared, next to task-294. They are not part of this decision.

**3. One dictionary per brand, with cases per language.** Brands keep their own tone, Du or Sie.

**4. A message's language is its brand profile's language.**

- **The language is that of the variant's brand profile** ([[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]] point 6).
- **This holds for email and push alike.** A push variant also resolves to a profile: its own, or the brand's default.
- **The language is frozen with the snapshot** (point 11), so preview and send agree.

**5. Two starter entries come from a setup file** (decided 2026-10-16).

- **`storage/expressions.json` declares Salutation informal and Salutation formal.** It is loaded and checked at startup, like `storage/brand_profile.json`, so a bad file fails the deploy.
- **The starters are copied into a brand's dictionary the first time the dictionary is used:** read in Settings or in the picker, or when a text is checked.
- **After that the brand owns its copies.** An installation may change the file or empty it; brands already started are not touched.

**6. An entry's name is fixed once created** (decided 2026-10-16). Its label and its cases stay editable. A different name is a new entry. The name is what texts carry, for example `{{salutation_formal}}`.

**7. Deleting an entry still in use is refused, naming where** (decided 2026-10-16).

- **"In use" means any campaign text, content record or override of the brand** that carries the entry's token.
- **A planned send is unaffected,** because its snapshot froze the entry (point 11).

### How an entry resolves

**8. A case applies only when every recipient field its text uses is filled** (decided 2026-10-16).

- **Otherwise the next case is tried, then the fallback.**
- **The fallback uses no recipient field.**
- **So there is never a "Hallo ,".** A case "first name is filled" with "Hallo {{first_name}}" and a case "gender is male" with "Sehr geehrter Herr {{last_name}}" both fall through when the name they print is empty.

### Where entries may appear

**9. Texts contain entries only; recipient fields appear only inside case texts.**

- **A text carries `{{name}}`, where name is a dictionary entry.** It is picked from a "Personalise…" button under each text field, or typed (the button decided 2026-10-16).
- **Entries work in all text:** subject, preheader, the text and rich-text fields of modules and content, and push title and body.
- **Never in links, url or image fields.** Dynamic links are their own task.
- **An unknown `{{name}}` is refused on save,** in module data, the envelope, content records and overrides. **A token in a link target or a url field is refused on save.**

### Substitution

**10. Substitution never goes through Jinja, and runs after escaping.**

- **User text is still never compiled as a template.** Tokens are replaced in the already-assembled values, never by evaluating the text.
- **Plain text gets the raw value,** and the autoescaping template escapes it as it does today.
- **Rich text, already escaped and formatted, gets the escaped value, and only outside tags.** So an `href` is never touched.
- **The envelope's subject is substituted on the artifact's envelope.** Push title and body are substituted in the push field set.
- **Case resolution comes first and the renderer receives values.** Each recipient's values `{name: text}` are resolved from the entries and the recipient's fields before rendering. They are what [[ADR-162 — Channel Rendering and Artifacts]] point 2 calls the `merge_context`. The renderer formats them in; it decides nothing.

### Freezing, sending and reconstruction

**11. Frame version 4 freezes the message language and every entry's text in that language.**

- **At send, each recipient's values are resolved from the frozen entries and that recipient's fields.**
- **The delivery record keeps the values actually used, as `{name: text}`.**
- **A reconstruction substitutes those recorded values, never live recipient data** ([[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] point 7).
- **Frames before version 4 render unchanged, without substitution.** Deliveries already sent reconstruct as before.

**12. A missing language refuses a send, or excludes a recipient.**

- **A send or test whose own texts use an entry with no text in the message's language is refused before it goes out,** the way an incomplete brand profile is refused ([[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]], addendum of 2026-10-11, point 6).
- **A recipient whose slot pick's content uses such an entry is excluded, with that reason.** The send goes on for the others.

### Preview and test

**13. The preview shows fallbacks, or the picked recipient's text.**

- **With no recipient picked, the preview shows the fallbacks.**
- **With a recipient picked in the existing picker, it shows their text.**
- **A test send uses its recipient, or the fallbacks.**
- **The live editor preview reads the live entries, the live profile language and the live recipient.** What goes out and the test render the frame as it would be frozen now ([[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]], addendum of 2026-10-13), so they read the entries as that frame would freeze them.

### Access

**14. Editing the dictionary needs `brand_profiles.manage`; reading it is open to any person of the brand.**

- **No new permission key.** The people who edit a brand profile's texts and legal details edit its dictionary.
- **Reading is open to every person of the brand,** because the "Personalise…" picker needs the list.
- **Writes are audited** ([[ADR-153 — Audit and Accountability]]).

### What this realises, and what it now owes

**15. The merge context of ADR-005 and ADR-162 is the resolved values.**
[[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]'s "Merge Context" and [[ADR-162 — Channel Rendering and Artifacts]] point 2's `merge_context` are realised as the per-recipient `{name: text}` values of point 11. They remain available after delivery, in the delivery record.

**16. The delivery record now holds personal data, and erasure must reach it.**
Erasure is not built ([[ADR-154 — Erasure and Retention]], Notes, 2026-09-14). The resolved values are names, so the delivery record now holds the merged personal data of ADR-154 point 5. Any erasure has to reach it. This is recorded in `backend/app/privacy/README.md` as well.

## Consequences

### Positive

- **Personalisation adds no injection surface.** Entries are data in a form, user text is still never compiled, and substitution happens after escaping.
- **Every use has a fallback.** Texts can carry only entries, and an entry falls through to a fallback that needs no recipient data, so no recipient sees "Hallo ,".
- **What a recipient got stays provable without live data.** The frame freezes the entries and the delivery record keeps the values used, so a reconstruction is exact even after the recipient's name or the dictionary changes.
- **One mechanism covers every text and both channels.** Subject, preheader, module and content text and push title and body work the same way.
- **Brands keep their own tone,** one dictionary per brand, with cases per language.
- **The demo has two salutations out of the box,** and an installation can change the starters without a code change.
- **The merge context that ADR-005 named and ADR-183 point 7 left open now exists.**

### Negative

- **Case texts are only as good as the CRM's data.** A wrong gender or a misspelt name goes out as synced. The CRM's mapping onto the four gender values is the adopter's work.
- **Each entry must be kept per language.** A brand sending in German and English maintains every entry twice, and a missing language refuses a send.
- **The delete refusal needs a brand-wide text search** across campaign texts, envelope modules, content records and overrides for the token.
- **A slot pick can exclude recipients.** Content whose text uses an entry lacking the message's language removes each recipient it was picked for.
- **Frozen delivery records now carry personal data** (names), and erasure does not exist yet to reach them.
- **The dictionary is per brand,** so a tone shared across brands is copied into each, not shared. A later change in one brand does not reach the others.
- **The recipient grows three personal-data columns** beyond what [[ADR-121 — Minimal Recipient Model]] lists, synced from the CRM.
- **Both render paths gain substitution.** The live editor preview reads live entries, while sends and tests read frozen ones. This is the second render path of ADR-183's Negative list, now with one more thing to keep in step.

## Notes

- **Where it lands, from task-365's plan of 2026-10-16.** Migration 0051 adds the three recipient columns, `expressions_started_at` on brands, and a table `expression_entries` (brand, name unique per brand, label, languages, timestamps, If-Match). The languages shape is `{lang: {cases: [{field, is: filled|empty|equals, value?, text}], fallback}}`. The service and router live in `backend/app/expressions/`, the editor under Settings > Personalisation in the React client. Refusal at send is a new `expression_refusal`, beside `profile_refusal`. These are the plan's, not decisions of this record.
- **Point 7 of the 2026-10-11 Description is narrowed.** It said an unknown name is refused on save "and refused again at send if the entry was deleted since". Since 2026-10-16 a used entry cannot be deleted (point 7) and a planned send carries frozen entries (point 11), so the second refusal becomes the missing-language refusal of point 12.
- **Token spelling inside case texts.** The 2026-10-11 Description writes `{{firstname}}` and `{{lastname}}`; the columns are `first_name` and `last_name`. This record writes the column names. The exact spelling is the build's.
- **Not decided here, and not put to the user.**
  - **Image alt text.** Alt fields are `text` fields in `storage/fields.json` ([[ADR-177 — A Field Is Defined Once, Required Per Module]]). Point 9 allows all text and excludes url and image fields; whether an image's alt text takes entries is not stated.
  - **An entry created after the freeze.** Point 11 freezes the dictionary as it stands. Slot picks resolve at send time, so a picked content record may carry an entry created after the snapshot, which the frame does not hold. Point 12 does not say whether that excludes the recipient.
- **Other records this touches, none of them edited here.**
  - [[ADR-144 — AI Data and Model Governance]] point 4 shows an AI writing `{{first_name}}` into a text. Under point 9 a text carries entries only, so that token would be refused on save. A dated addendum on ADR-144 should say the AI personalises through entries, for example `{{salutation_informal}}`. The privacy property ADR-144 wants holds unchanged: values are filled locally.
  - [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]'s Merge Context example lists raw fields (`firstname`, `language`, `preferred_airport`). Here the merge context is the resolved values. That is narrower, not contrary. ADR-005 is not changed.
  - [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] point 7 and [[ADR-154 — Erasure and Retention]] point 5 are answered here. A short dated addendum on each, pointing here, would let a reader of either record alone find it.
  - [[ADR-121 — Minimal Recipient Model]] lists neither gender nor names. The three columns are business fields synced from the CRM ([[ADR-120 — CRM as Customer Source of Truth]], [[ADR-126 — Maintain Local Recipient Projection]]).
- **No decision-log entry.** `docs/playbook-strategy.md` §5 has no entry for the 2026-10-11 or 2026-10-16 sessions. Its 2026-10-11 entry on the November presentations lists "salutations" among the demo items. Its entry "Addresses in the platform (G1)" ends "Where a salutation's data comes from stays deferred"; point 2 answers it for the three fields: the recipients API, fed by the CRM. The reasoning here comes from task-365's Description and Implementation Plan.

## Addendum 2026-10-16 — decided in the build

**These were decided by the implementer during the build of task-365, not by the user.** The build is commits a843dba, 30e39af, dab8906 and 6edc8f8, all of 2026-10-16. The user had said to proceed and has not reviewed these points one by one. The Decision above is unchanged. Points 1 and 2 answer the two open points under "Not decided here, and not put to the user" in the Notes. Point 3 settles the Notes' token spelling. The rest records the shape the build took.

1. **Alt text takes no entries.** An image's alt text describes the image, not the reader.
   - Substitution skips alt fields (`Personal.fields` in `backend/app/expressions/substitute.py`).
   - A token in an alt field is refused on save, as it is in url and image fields.
   - Point 9's "all text" therefore excludes alt text, although alt fields are `text` fields.
2. **An entry the frozen frame does not hold excludes the recipient.** This covers a slot pick whose content uses an entry created after the freeze, or one without a text in the message language.
   - That recipient is excluded with the reason "personalisation without a text in this message's language: {{name}}" (`REASON_PERSONAL_MISSING` in `backend/app/delivery/exclusion.py`).
   - A text is never sent with `{{name}}` still in it.
   - The frame's own texts are covered by the refusal before sending (`expression_refusal` in `backend/app/rendering/frame.py`), point 12's first bullet.
3. **Token spelling inside case texts is `{{first_name}}` and `{{last_name}}`,** matching the columns.
   - Gender is tested, never printed.
   - A fallback prints no recipient field.
   - An entry's name may not be a recipient field's name.
4. **Save checks judge only a changed value** (`backend/app/expressions/checks.py`), as image checks do. A text stored earlier stays editable in its other fields.
   - They run on module fields, the envelope, content records and overrides.
   - A refused subject or preheader is answered 422 on its field by the variant routes. The live check found that these routes had answered 500 on update and 404 on create.
5. **The starters are copied in a short session of their own, with the brand row locked.** The caller's transaction is untouched, and two first uses at once copy them only once. Rendering reads the dictionary without starting it, so a send never writes to it.
6. **The frame and the delivery record have this shape.**
   - Frame version 4 holds `expressions: {language, entries}`.
   - Readers key on `frame_version`. Below 4 there is no substitution, even if a frame holds the key.
   - The delivery record's key is `personal`: `{name: text}` of the entries used.
   - The artifact carries `personal` and `personal_missing`. Neither is part of the artifact hash. The text they produced is.
7. **The recipients API upsert writes `gender`, `first_name` and `last_name` only when the payload sends them.** A field left out is kept; null clears it. This differs from `language` and `attributes`, which the upsert writes wholesale. Migration 0051 (`backend/scripts/migrate_0051_personalisation.sql`) copied existing `firstname` and `lastname` attributes into the columns.
8. **The "Personalise…" button is opt-in per field.**
   - It appears on texts that take entries: subject, preheader, module and content text, overrides and push.
   - It never appears on titles, names or links.
   - It inserts at the caret and saves at once.

**The addenda the Notes asked for were added on the same date.** [[ADR-144 — AI Data and Model Governance]], [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] and [[ADR-154 — Erasure and Retention]] each carry an addendum of 2026-10-16 that points here.

**No decision-log entry.** `docs/playbook-strategy.md` has no entry for these points. They come from the build of task-365.

## Related ADRs

### Depends On
- [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]] — the Merge Context this record realises as resolved values.
- [[ADR-162 — Channel Rendering and Artifacts]] — the renderer contract's `merge_context`, and the 2026-10-11 addendum that sent per-recipient text here.
- [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]] — the frame and the delivery record; point 7's merge context is decided here.
- [[ADR-194 — Brand Profiles Carry an Email's Look, Texts and Legal Details]] — the message language (point 6), the `brand_profiles.manage` permission, and the refusal convention.
- [[ADR-154 — Erasure and Retention]] — point 5: the delivery record's resolved values must be reachable by erasure.
- [[ADR-144 — AI Data and Model Governance]] — point 4's local filling of personal values.
- [[ADR-120 — CRM as Customer Source of Truth]] — the CRM supplies and maps the recipient fields.
- [[ADR-121 — Minimal Recipient Model]] — the recipient model the three columns join.
- [[ADR-126 — Maintain Local Recipient Projection]] — the local projection that holds them.
- [[ADR-177 — A Field Is Defined Once, Required Per Module]] — field types decide where substitution applies.
- [[ADR-063 — Rendering Parity Over Rendering Implementation]] — preview, test and send show the same personalised text.
- [[ADR-153 — Audit and Accountability]] — dictionary writes are audited.
