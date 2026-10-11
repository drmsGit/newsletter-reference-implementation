---
id: TASK-350
title: >-
  Brand profiles 1a: the setup file, profiles per brand with their screens,
  chosen on the variant
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-10 21:17'
updated_date: '2026-10-11 09:00'
labels:
  - backend
  - frontend
dependencies:
  - TASK-301
type: feature
ordinal: 200970
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Slice 1 of 5 of the brand-profile design (ADR-194, decided with the user 2026-10-11; the decisions and their reasons are in this task's notes).

Today BrandDB holds only a key and a name (backend/app/auth/db_models.py around :35-38). The fixed footer the rendering frame appends to every marketing email shows the brand name and the unsubscribe link (ADR-191; backend/app/rendering/frame.py, subscriptions/texts.py footer_html, subscriptions/service.py footer_for). There is no place for legal details, texts or a look per brand.

This slice builds:
- **The setup file** storage/brand_profile.json. It declares a profile's fields (name, type, label, required, group) and is read at startup like the module manifests. A fixed core is always present: legal company name, address, imprint URL, privacy URL, unsubscribe text.
- **Profiles per brand:** create, edit, duplicate, mark default (the first is the default; the default can be changed but not deleted). Deleting a profile makes unsent variants that use it fall back to the default, with a notice in the composer.
- **Permissions:** a per-brand permission to manage profiles, with every change audited.
- **Language and type:** each profile records its language (one profile per language) and is marked marketing or transactional (marketing by default). The transactional switch itself, which skips the opt-in check, is slice 4; here it is only stored.
- **The choice on the variant:** a dropdown of the brand's profiles, default preselected. A new variant copies the profile it was duplicated from. A campaign copied into another brand uses that brand's default.
- **The snapshot freezes the chosen profile's values,** so editing a profile never changes an email already sent (ADR-183).
- **The fixed footer on every email** (marketing, transactional, test sends): the profile's legal details, plus for marketing the profile's unsubscribe text with the platform's token link and one-click header (ADR-191).
  - A marketing profile must have unsubscribe text.
  - Any send is refused while its profile lacks a required field.
- **The footer_html docstring** in backend/app/subscriptions/texts.py (around :13-14) is reworded: the line is permanent now (ADR-191 addendum 2026-10-10).

Not in this slice: filling brand.css and the templates (slice 2), header and footer modules (slice 3, task-351), skipping the opt-in check (slice 4), the manager app's look (slice 5).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A setup file declares the profile's fields; the core legal and unsubscribe fields are always present
- [ ] #2 A brand can hold several profiles; one is the default; profiles can be duplicated and deleted, falling back to the default
- [ ] #3 Profile changes need the per-brand permission and are audited
- [ ] #4 Every brand has a default profile; existing brands get an English 'Default' one by migration
- [ ] #5 A variant chooses a profile (default preselected); a copied variant keeps it within the brand and takes the target brand's default across brands
- [ ] #6 Managers edit profiles in a screen built from the setup file; incomplete profiles say which fields are missing
- [ ] #7 A profile cannot be created as transactional yet (task-355)
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final-design pass 2026-10-11 (Plan agent map plus the user's decisions). Split by effect: THIS task is 1a, 'profiles exist', with no change to any sent email. 1b, 'every email carries them', is task-357.

1a lands in:
1. Setup file: new backend/app/brand_profiles/structure.py.
   - CORE_FIELDS: legal_company_name, legal_address, imprint_url, privacy_url, unsubscribe_text.
   - FIELD_TYPES: colour, font_family, size, image, text, url, number.
   - storage/brand_profile.json is shaped like storage/fields.json ({_comment, fields}) and ships with empty fields.
   - Loading follows the module registry: mtime refresh, _refuse_unknown, assert_structure_loads() at startup in main.py next to assert_manifests_load. Field names must match [a-z][a-z0-9_]*. The file may relabel or regroup a core field, never change its type or required flag.
2. Model: brand_profiles (id, brand_id FK, name, language, kind CHECK marketing/transactional, is_default, field_values JSON default {}, created_at, updated_at).
   - UNIQUE(brand_id, name), and a partial unique index for one default per brand (pattern: overrides/db_models.py).
   - variants.brand_profile_id is a nullable FK; NULL reads as the brand's default.
   - variants.brand_profile_notice String(255) (D6): set when a delete re-points the variant, cleared when a profile is picked.
   - Migration 0044: table, indexes, one 'Default' profile per brand (language en, marketing, unsubscribe_text 'Unsubscribe'), and a backfill of variants via raw SQL.
   - ensure_default_profile() runs in create_brand, ensure_default_brand and bootstrap.
   - Brand delete: profiles are DELETED_WITH_BRAND, not counted in brand_holders().
3. Permission brand_profiles.manage (BRAND_SCOPED; Admin automatic, Manager not by default). The transactional permission is NOT declared yet (task-355).
   - Policy: ('/brand-profiles', BRAND_PROFILES_MANAGE) and a BRAND_OWNED reason.
   - Writes are people only.
   - Audit brand_profile.created/updated/duplicated/deleted/made_default, recording changed field NAMES only, never values (the audit email check would raise; D8).
4. API /brand-profiles:
   - structure; paged list with complete/missing; get; create; PUT with If-Match; duplicate ('X (copy)', marketing); make-default; delete.
   - Delete: 409 for the default; otherwise re-point variants to the default with a notice.
   - Values are checked by type; incomplete profiles may be saved.
   - kind 'transactional' is refused with 422 until task-355 (D2).
5. Variant:
   - brand_profile_id on the Variant, VariantCreate and VariantUpdate models, checked to belong to the brand.
   - Defaults on create_campaign and create_variant_for_campaign.
   - _copy_variant_into: same brand copies the profile, another brand takes the target's default.
   - campaign_composition reports brand_profile {id, name, language, kind, is_default, missing, notice}.
6. Frontend:
   - BrandProfiles.tsx (list) and BrandProfileDetail.tsx (form from the structure, explicit Save, If-Match).
   - Routes, a nav entry (g b), the variant editor dropdown with incomplete and fallback notices, hooks, regenerated schema.d.ts, screen inventory.
7. Seed and fixtures: seed_demo_data fills complete example.test profiles for the default brand and demo-b; temp_brand creates a complete profile; conftest cleanup; test_brand_scoping and test_permission_split updated.

Decided by the user 2026-10-11:
- D7: unsent snapshots made before profiles are refused (in 1b).
- D4: migrated defaults are English, 'Unsubscribe'.
- D5: Imprint and Privacy labels come from a built-in per-language table (en/de, fallback en); the whole unsubscribe text is the link.
- D1: required are legal name, address, imprint URL and privacy URL always, plus unsubscribe text on marketing; the setup file can never make a core field optional.
- Split: 1a then 1b.

Agreed technical defaults: writes people only; refuse at send, not at snapshot (D9); the shipped file has no extra fields (D10); a dated ADR-194 addendum records this pass (D12).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10, from writing ADR-193, open for the final-design pass:
- which of the four legal fields a send requires (only the imprint was stated);
- which choice wins when both a campaign and a variant pick a legal set;
- whether transactional mail and test sends carry the legal details (transactional is task-134);
- whether the per-brand theme values join ADR-183's template and CSS fingerprint, or are frozen like the legal set.
Also, the footer_html docstring in backend/app/subscriptions/texts.py (around :13-14) says the line lasts 'until task-301's designed footer replaces it'. It does not any more (ADR-193, ADR-191 addendum 2026-10-10); reword it here.

2026-10-11, design session on BRAND PROFILES. It replaces ADR-193 points 2-3: the legal-detail sets and theme values become one concept, and the header and footer content source changes too. A superseding ADR follows.

Settled by the user before the questions:
- A brand has as many brand profiles as it needs. The first is the default; deleting a profile falls back to the default.
- A profile holds colours, font families, font sizes, images, texts (service, unsubscribe, legal imprint), URLs (menu links), and if reasonable basic tracking, padding and border radius.
- brand.css stays one file whose values come from the profile. Email clients cannot use CSS custom properties, so the renderer fills the values in before inlining.
- Duplicating within a brand keeps the profile; copying to another brand uses that brand's default (changeable later). The profiles offered are those of the selected brand, within the manager's permissions.
- Use case: a flashy marketing look, a calm transactional one, a dark Black Friday one. Header menus, hotlines and footer texts also differ per profile.
- There is no separate dark-mode logo field: mail programs cannot be told to swap images. Logos are PNGs with a thin white edge.
- The profile STRUCTURE (which fields exist) is declared in a deploy-time setup file, like the module manifests, and not fixed in code. One company has 2 font sizes, another 4; IT changes it in a normal deployment.

Q1, decided: the profile is chosen on the VARIANT. That allows A/B tests of designs and matches how emails are frozen (one snapshot per variant). A new variant takes the profile of the variant it is copied from, else the default.

2026-10-11, design session continued; all decided by the user:
- Q2: a fixed core plus free fields. The platform's core (legal company name, address, imprint URL, privacy URL, unsubscribe text) is always present. The setup file adds any further fields. A send is refused while a required field of the chosen profile is empty.
- Q3: a new per-brand permission for profiles; Admin has it, and Managers if the company grants it. Changes are audited.
- Q4: one profile per language (e.g. Default DE / Default EN). The profile records its language so the composer can warn on a mismatch.
- Q5: tracking. The profile sets utm_source and utm_medium plus optional extra key=value pairs. utm_campaign comes from the campaign and utm_content from the variant. They are added at render to content links, never to unsubscribe, imprint or privacy links.
- Q6: the manager app reads the working brand's default profile for accent colour, logo and font only, with a contrast guard (fallback to the app's own accent). This replaces task-94's separate web palette.
- Q7: the header and footer modules render from the chosen profile (logo, menu links, hotline, footer texts). The footer module adds one optional per-email text. A manager still places them; the fixed legal line is always appended.
- Q8: legal details on EVERY email, marketing, transactional and test sends.
  - The unsubscribe line's text comes from the profile; an empty text means no line.
  - A profile is marked marketing or transactional, which decides whether an email may go out without opt-in. Different unsubscribe and other footer links go in free fields or extra core fields.
- Q8a: transactional needs a separate right to create or mark such a profile; changes are audited; choosing one on a variant shows a 'sent without opt-in check' label and is audited. Plus a 'duplicate brand profile' function. Copying a transactional profile keeps it transactional only for someone holding that right; otherwise the copy is marketing.
- Q8b: the profile sets the unsubscribe TEXT; the link stays the platform's per-recipient token link, and every marketing email keeps the one-click header (ADR-191). Other links go in free fields.
- Confirmed:
  1. Marketing profiles must have unsubscribe text (ADR-191's guarantee); transactional ones may leave it empty.
  2. The default can be changed but not deleted.
  3. Deleting a profile used by unsent variants makes them fall back to the default, with a notice; frozen snapshots keep its values.
  4. A snapshot freezes the profile's values.
  5. The setup file is storage/brand_profile.json (name, type, label, required, group), with the core always present. brand.css refers to fields by name and the renderer fills them before inlining. KEEP MJML IN MIND: MJML styles are often tag attributes, so profile values must reach the templates as variables too, not only brand.css (ADR-131).
  6. Any send is refused while its profile lacks a required field.

2026-10-11: rescoped by the brand-profile design session (ADR-194 supersedes ADR-193). The original description, kept verbatim:

**[Feature]** BrandDB holds only a key and a name (backend/app/auth/db_models.py around :35-38). The fixed footer the rendering frame appends to every marketing email shows only the brand name and the unsubscribe link (ADR-191; backend/app/rendering/frame.py around :286-292, subscriptions/texts.py footer_html). A German marketing email legally needs the sender's details: legal name, address, imprint.

Decided by the user 2026-10-10 (task-301, ADR-193 points 1-3):
- Each brand has a profile holding several named legal-detail sets: legal company name, address, imprint link, privacy link. One set is the default; a campaign or variant may choose another.
- The frame's legal footer reads the chosen set at render. A snapshot freezes it, so a resend shows what was sent.
- A marketing send is refused while the applicable set lacks a legally required field.
- The profile also carries colour and font values, applied on top of the shared brand.css at render.

Open for the final-design pass:
- how the values are applied, since email clients handle CSS custom properties poorly (task-94 note);
- whether a set is chosen per campaign or per variant;
- which fields are required;
- who may edit the profile (an Admin, in Settings).

Second of three build tasks from task-301.

2026-10-11, revised after reading docs/design/DESIGN.md: Q6 is narrowed by the user to the LOGO only. The manager app keeps one palette and its Plex fonts per installation, so the design's teal (system) and ochre (human) keep their meaning; task-356 is rescoped accordingly. The design draft covers only the manager app; emails are out of its scope, so the profile's email fields still come from the setup file.

2026-10-11: rescoped to 1a after the final-design pass. The criteria about freezing, the footer on every email and refusing sends moved to task-357 (1b).
<!-- SECTION:NOTES:END -->
