---
id: TASK-365
title: >-
  Inline personalisation: a brand's expression dictionary, starting with two
  salutations
status: Done
assignee:
  - '@claude'
created_date: '2026-10-11 19:10'
updated_date: '2026-10-16 14:15'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 200400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Designed with the user on 2026-10-11, one question at a time, while working task-60. It started as "personalise the subject line" and the user widened it: "instead of personalize subject line we need to think of personalize inline text as a general concept". A small set of named variables that can be used in any text personalises the subject line, module text, content text and push alike. The model the user pointed to is Salesforce Marketing Cloud Next's "Expressions": you define a label such as {{salutation}}, and its expression says something like "if firstname is not empty then Hallo Firstname, else Hallo,".

**The user's catch, and the boundary.** Personalisation depends on what the CRM, or any other system, syncs into the platform or offers through an endpoint. This task builds the dictionary and three basic recipient fields, and implements two use cases: Salutation Informal ("Hallo Firstname") and Salutation Formal ("Sehr geehrter Herr / Sehr geehrte Frau"). Anything else belongs to the "how to get data into the system" chapter (task-294, task-364).

**What exists (verified 2026-10-11).** There is no merge or substitution mechanism anywhere, and the ADRs expect one:
- ADR-005 defines a "Merge Context".
- ADR-144 point 4 expects {{first_name}} to be filled at render.
- ADR-162 point 2's renderer contract names a merge_context, which the code does not have.
- ADR-183 point 7 says that once substitution exists, the delivery record must keep the merge context.
- ADR-154 point 5 says rendered output that holds merged personal data must be reachable by erasure.

Recipients have only a schema-less attributes bag (`backend/app/recipients/db_models.py:17`), which only `create_recipient` writes, wholesale (`backend/app/recipients/service.py:240-300`, :284). It is checked against a denylist (task-158). The seed puts only {"firstname": name} in it (`backend/scripts/seed_demo_data.py:209`). Nothing reads attributes while rendering.

Rendering has one autoescaped Jinja environment (`backend/app/rendering/service.py:33`). Only template files are compiled. User text (module_data, content fields, overrides) is always passed as escaped data, and that must stay true: **user text never goes through Jinja**, or this becomes a template-injection hole. The envelope (subject, preheader) is copied raw from the envelope module (`envelope_fields_for_variant`, `backend/app/rendering/service.py:225-257`) and frozen in the frame (`backend/app/rendering/frame.py:175`, :362-377).

The preview's recipient picker exists (`frontend/src/screens/Preview.tsx:183`) but today only changes slot picks. The planned "Related Data Access" design interview already sketches this area: `docs/architecture/interview-prep/Related Data Access - design interview.md` clusters B and C (restricted substitution and not template evaluation, a mandatory fallback, preview with sample data, the delivery record holding the values).

**Decided 2026-10-11:**
1. **Expressions are cases, not formulas.** An entry is an ordered list of cases, each checking a recipient field, plus a required fallback text. A field can be filled, empty, or equal to a value. Example: gender is female gives "Sehr geehrte Frau {{lastname}}"; gender is male gives "Sehr geehrter Herr {{lastname}}"; otherwise "Sehr geehrte Damen und Herren". This is a form, not a language: nothing to parse and nothing to inject. The user asked whether this carries further. It does, with more operators on typed fields: a CRM tier equal to VIP gives "20 %", otherwise "10 %"; a score of at least 80; a last purchase within 90 days. Those come later, see point 2.
2. **Fields.** Gender, first name and last name become real recipient columns, through a migration, the recipients API and the import. Other attributes come later as declared, typed attribute fields (text, number, date) with comparisons, next to task-294. They are not part of this task.
3. **Scope.** One dictionary per brand, and each entry holds its cases per language. Brands keep their own tone (Du or Sie).
4. **Language.** A send uses the message's language, which is the language of the variant's brand profile (ADR-194 point 6). It is frozen into the snapshot, so preview and send agree. If an entry used by the message has no cases for that language, the send is refused before it goes out, like an incomplete brand profile.
5. **Gender values** are female, male, diverse, or empty. The CRM or the import maps its own values onto these. Anything else is refused at the API with a clear error.
6. **What a text may contain.** Texts use dictionary entries only, picked from a list, for example {{salutation_formal}}. Recipient fields ({{firstname}}, {{lastname}}) appear only inside an entry's case texts. So every use has a fallback and there is never a "Hallo ,".
7. **Where variables work.** All text: subject, preheader, text and rich-text fields of modules and content, and push title and body. **Never links.** Dynamic links are a separate concept, filed as their own task. An unknown {{name}} is refused on save, and refused again at send if the entry was deleted since.
8. **Preview.** Without a recipient, the preview shows the fallback text. With a recipient picked in the existing picker, it shows their real text. A test send uses its recipient, or the fallback.
9. **Permission.** Editing the dictionary needs brand_profiles.manage, the same people who edit the brand profile's texts and legal details. No new permission key.

**Still open, to be asked before building:**
- Should the two salutations ship as starter entries for every brand, from a setup file like storage/brand_profile.json? Is an entry's name fixed once created, with only its label and cases editable? Is deleting a used entry refused?
- The final-design pass. Where the substitution runs, so it sits after escaping (rich text) and before the hash. What the frame freezes: the cases in force, at a new frame version. What the delivery record keeps per recipient: the resolved values (ADR-183 point 7), so a reconstruction never re-reads live recipient data. How the values are reached by an erasure (ADR-154 point 5). How push differs.

**An ADR is written at the start of the build** from these decisions, through the adr-author agent.

**Not this task.**
- A wholly different subject per recipient. That is separate variants, or an AI case (task-125), or an automation (ADR-162 addendum of 2026-10-11).
- Dynamic and personalised links (their own task).
- Typed attribute fields and their comparisons (task-294).

**Related.** task-60 (closed into this), task-294, task-364, task-125, task-348; ADR-005, ADR-120, ADR-121, ADR-126, ADR-144, ADR-154, ADR-162, ADR-177, ADR-183, ADR-194.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A brand's dictionary holds entries with cases per language and a required fallback, edited under Settings by people with brand_profiles.manage
- [x] #2 Recipients carry gender (female, male, diverse or empty), first name and last name through the API and the import
- [x] #3 Salutation Informal and Salutation Formal work in subject, preheader, module and content text and push, in preview and send
- [x] #4 What a recipient received is reconstructed exactly from the delivery record, without re-reading live recipient data
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final design (2026-10-16). Product decisions with the user, one at a time: starters from a setup file (storage/expressions.json), copied into a brand's dictionary when it is first used; an entry's name is fixed, its label and cases editable; deleting an entry still used is refused and names where; a case applies only when every recipient field its text uses is filled, and the fallback uses none; API and demo seed only (no recipient file import, that is task-294/task-364); a "Personalise…" button under each text field inserts an entry, typing {{name}} also works and is checked on save.

1. Migration 0051: recipients get gender (female, male, diverse or empty), first_name, last_name; brands get expressions_started_at; new table expression_entries (brand_id, name unique per brand, label, languages JSON: {lang: {cases: [{field, is: filled|empty|equals, value?, text}], fallback}}, timestamps, If-Match). Recipients API takes and validates the three fields (gender refused otherwise); seed fills them.
2. app/expressions: structure loader for storage/expressions.json (like brand_profiles/structure.py, checked at startup); service (list with seeding, create, update with If-Match, delete refused while used: a brand-scoped search of module_data, envelope modules, content records' current content and overrides for the token); resolve(entry_languages, language, recipient) -> text with the filled-fields rule; router /expressions under brand_profiles.manage for writes, read for any person of the brand (the picker needs it); audit on writes. React: Settings > Personalisation (list, edit label and cases per language, add a language).
3. Substitution, never Jinja: tokens {{name}} replaced in text and rich-text fields only, never url or image fields. Plain text gets the raw value and is escaped by the template as today; rich text (Markup, already escaped) gets the escaped value, and only outside tags, so an href is never touched. Envelope subject and preheader, module and content text, push title and body. Live render (editor preview, with or without a recipient) reads live entries, the live profile language and the live recipient.
4. Frame version 4 freezes the language and every entry's text in that language. At send each recipient's values are resolved from the frozen entries and their fields; the delivery record keeps the values actually used ({name: text}), and reconstruction uses those, never live recipient data. Frames before 4 render without substitution, unchanged.
5. Refusals: a send or test whose frame texts use an entry with no text in the message's language is refused before it goes out (expression_refusal, like profile_refusal); a recipient whose slot pick uses such an entry is excluded with that reason. An unknown {{name}} is refused on save in module_data, the envelope, content records and overrides; a token in a link target or url field is refused.
6. Preview: without a recipient, fallbacks; with one picked, their text. Test send uses its recipient, or fallbacks.
7. Erasure (ADR-154, not built): the delivery record now holds resolved personal values; recorded in the ADR and backend/app/privacy/README.md so erasure reaches them.
8. ADR written now by adr-author; tests with mutation checks; live check on scratch data.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-11, the user set the November 2026 presentations as the focus (docs/business/PRESENTATIONS-2026-11.md): salutations are on the demo list.

Built 2026-10-16 in four slices, each tested, mutation-checked and green in CI: a843dba (recipient fields, migration 0051, ADR-199), 30e39af (dictionary, /expressions, Settings > Personalisation), dab8906 (substitution in rendering, frame version 4, delivery record, refusal and exclusion), 6edc8f8 (save checks, Personalise button); records 994cb18 (ADR-199 build addendum; ADR-144, ADR-183, ADR-154 addenda; backend/app/privacy/README.md lists what erasure must reach).

Decided with the user 2026-10-16, one at a time: starters from storage/expressions.json, copied on first use; an entry's name fixed, label and cases editable; deleting a used entry refused, naming where; a case applies only when every field its text prints is filled; API and demo seed only (no recipient file import); a Personalise button under each text field.

Decided in the build without asking (ADR-199 addendum of 2026-10-16, worth a look): alt text takes no entries and is refused on save, with links and image addresses; a slot pick whose content uses an entry the frozen frame lacks excludes that recipient; tokens in case texts are {{first_name}} and {{last_name}}; save checks judge only changed values; the recipients upsert writes the three fields only when sent (left out keeps them, null clears), unlike language and attributes.

Found in the live check and fixed: a refused subject or preheader came back as a 500 on update (404 on create); now a 422 on the field, shown inline. Found and filed, not fixed: task-385, a false "somebody else changed this" conflict whenever a text starts or ends with a space (pre-existing, envelope trimming).

Not done here: dev data has first names only (the migration copied them); last names and genders arrive with task-71's realistic seed (the seed script fills them for a fresh reset). Dynamic links and typed attribute fields stay with their own tasks (task-294). The ADR-154 addendum drafted an obligation for adopters who keep activity after erasure; removed as undecided.

Verification: pytest 2062 passed; vitest 317 passed; tsc, build, eslint (no errors), Ruff; mutations: slice 2 nine (two halves of a double check caught together), slice 3 fifteen, slice 4 nine plus the 422 fix, client five plus four, all caught after two tests were strengthened; live check on scratch campaign SCRATCH task-371 blocks: starters in Settings, Personalise inserting at the caret, an unknown entry refused inline, the preview showing "Dear Sir or Madam," for nobody and "Hi Mia," for demo-003.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A brand's expression dictionary (Settings > Personalisation, brand_profiles.manage) with Salutation informal and formal as starters; recipients carry gender, first and last name through the API; entries reach subject, preheader, module and content text and push, after escaping and never in links; frame version 4 freezes them and the delivery record keeps the values used, so a rebuild never re-reads the recipient; unknown entries are refused on save and a missing language before send. ADR-199 plus addenda. Verified by pytest 2062, vitest 317, mutation checks, a live check, and CI green on all four slices.
<!-- SECTION:FINAL_SUMMARY:END -->
