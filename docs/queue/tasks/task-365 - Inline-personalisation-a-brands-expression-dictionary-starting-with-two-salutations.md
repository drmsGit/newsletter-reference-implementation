---
id: TASK-365
title: >-
  Inline personalisation: a brand's expression dictionary, starting with two
  salutations
status: To Do
assignee: []
created_date: '2026-10-11 19:10'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 210300
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
- [ ] #1 A brand's dictionary holds entries with cases per language and a required fallback, edited under Settings by people with brand_profiles.manage
- [ ] #2 Recipients carry gender (female, male, diverse or empty), first name and last name through the API and the import
- [ ] #3 Salutation Informal and Salutation Formal work in subject, preheader, module and content text and push, in preview and send
- [ ] #4 What a recipient received is reconstructed exactly from the delivery record, without re-reading live recipient data
<!-- AC:END -->
