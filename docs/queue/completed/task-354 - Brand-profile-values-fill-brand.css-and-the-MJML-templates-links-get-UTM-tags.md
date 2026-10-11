---
id: TASK-354
title: Brand profile values fill brand.css and the MJML templates; links get UTM tags
status: Done
assignee:
  - '@claude'
created_date: '2026-10-11 08:39'
updated_date: '2026-10-11 10:21'
labels:
  - backend
dependencies:
  - TASK-350
type: feature
ordinal: 200975
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Slice 2 of 5 of the brand-profile design (ADR-194, 2026-10-11).

brand.css stays one shared file (storage/modules/email/brand.css, inlined in backend/app/rendering/service.py). Its values come from the variant's brand profile: it refers to profile fields by name, and the renderer fills them in before inlining, because email clients do not support CSS custom properties.

MJML (ADR-131): many MJML styles are tag attributes, not CSS, so profile values must also reach the module templates as variables.

Links: the profile sets utm_source and utm_medium plus optional extra key=value pairs. utm_campaign comes from the campaign and utm_content from the variant. They are added at render to content links, never to unsubscribe, imprint or privacy links. This is link tagging only; open tracking is task-353.

Final-design pass:
- how placeholders are written in brand.css (for example a resolved var(--name), or a template syntax);
- how MJML attributes take values;
- the interplay with the existing click-attribution link tagging (backend/app/rendering/tracking.py tag_links);
- whether theme values join ADR-183's templates fingerprint or are frozen with the profile (slice 1 freezes them).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Two profiles with different colours and fonts produce visibly different emails from the same variant
- [x] #2 Values reach both brand.css and the module templates
- [x] #3 Content links carry the profile's UTM parameters; unsubscribe, imprint and privacy links do not
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final-design pass 2026-10-11, decided with the user one question at a time:
- D1 brand.css names a profile value as a standard CSS variable with its fallback, var(--field_name, fallback). The renderer replaces every var() with the profile's value, or the fallback when the profile leaves it empty, before inlining. No email ever contains var().
- D2 The shipped setup file declares a starter set from today's look, each falling back to today's value: colour_text, colour_body_text, colour_button, colour_button_text, colour_hero_background, font_family, size_headline, size_body, radius_button (group Look).
- D3 UTM tags go on every http(s) link a module renders (content and static buttons, later the header/footer modules' menu links), never the legal footer. A key the link already carries is kept. No tags at all unless the profile sets utm_source. nl_content click tracking is separate and unchanged.
- D4 utm_campaign and utm_content are the campaign and variant names as slugs (lowercase, other characters to hyphens), frozen at snapshot time.

Settled without a question: theme values are frozen with the profile (the frame holds all values since task-357), so a rebuilt email keeps its colours. utm_source, utm_medium and utm_extra (further key=value pairs, one per line) are CORE fields, optional, group Link tracking, because the platform reads them by name.

Where it lands:
1. brand_profiles/structure.py: three optional core fields. service.clean_values: font_family limited to letters, digits, spaces, commas, quotes, hyphens and dots (it goes into CSS); utm_extra lines must be key=value.
2. New brand_profiles/theme.py: resolve_css(css, values) (only colour, size, font_family and number values are filled in; anything else falls back); slug(name); link_params(values, campaign_name, variant_name).
3. rendering/tracking.py: with_params / tag_params adds missing keys to every http(s) href.
4. rendering/service.py: a theme {values, link_params} passed through render_variant_html, render_module, render_cms_module, render_static_module and module_html (templates get profile.<field>; links tagged after nl_content) and into email_document (brand.css resolved). Live renders (preview, test send) use the variant's live profile and names.
5. rendering/frame.py: build_frame freezes link_params next to brand_profile; render_frame passes the frozen theme. Frames without them render as before. No version bump: the keys are optional, and v3 frames made before this have no look values.
6. storage/modules/email/brand.css: values become var(--field, today's value). css_inline drops the style block after inlining, so with the fallbacks the inlined output is byte-identical for old frames; the fingerprint changes once, as for any template edit.
7. storage/brand_profile.json: the starter set.
8. Tests: two profiles give visibly different emails from one variant (AC1); a profile value reaches a module template (AC2, through a test template); UTM on module links incl. a static CTA, not on footer links, kept own keys, none without utm_source (AC3); old frames byte-identical; validation of font_family and utm_extra; slugs.
ADR: a dated ADR-194 addendum for D1-D4 via adr-author.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-11, built. Commits efc7bbe (ADR-194 addendum 2026-10-11 (third)) and 8e70ea7.

Decided with the user (D1-D4 in the plan): var(--field, fallback) in brand.css; a starter set of nine look fields; UTM tags on every module link, never the legal footer; utm_campaign/utm_content as name slugs.

Where it landed:
- brand_profiles/structure.py: optional core fields utm_source, utm_medium, utm_extra (group Link tracking).
- brand_profiles/service.py: font_family limited to names, commas, quotes, hyphens and dots; utm_extra lines must be key=value.
- New brand_profiles/theme.py: resolve_css (only colour, size, font_family and number values; anything else and empty values fall back), slug, link_params (none without utm_source), live_theme.
- rendering/tracking.py: with_params / tag_params (a link's own keys win; hrefs unescaped first so &amp; stays a separator).
- rendering/service.py: a theme {values, link_params} through render_variant_html, render_module, render_cms_module, render_static_module, module_html (templates get profile.<field>; links tagged after nl_content) and email_document (brand.css resolved).
- rendering/frame.py: build_frame freezes link_params beside brand_profile; render_frame uses the frozen theme. No version bump.
- storage/modules/email/brand.css: today's values became var(--field, today's value). storage/brand_profile.json: the starter set.

Verification: backend 1763 passed, Ruff clean; 11 mutations, all caught after adding the escaped-ampersand test. Byte-identity: with no profile values the new brand.css inlines exactly as the original did, checked on all 13 dev email variants and on every module type with sample values (css_inline drops the style block, so only the applied values matter). Live check 2026-10-11 on scratch data: a profile with button #c0392b, body text #2e7d32 at 18px and UTM tags gave a snapshot whose button carried the colour and utm_source, utm_medium, utm_campaign=scratch-theme-check, utm_content=variant-b, ref=tarrow; the body text the colour and size; the imprint link no tags; no var() left. A font value with a semicolon was refused (422). The profile form shows the Link tracking and Look groups. Scratch profile deleted through the API, scratch campaign rows removed by id.

Known limits:
- The font family applies inside the content modules' wrapper (img_left, img_right, single_stack), as today's brand.css does; a CTA or editorial module takes the mail program's default font.
- The form gives Further link parameters no format hint (key=value per line); the refusal message explains it on save.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Slice 2 of brand profiles: brand.css names profile values as var(--field, fallback), filled in before inlining (older frames inline byte-identically); the setup file ships nine look fields; templates get profile.<field> for MJML later; every module link carries the profile's UTM tags (utm_campaign/utm_content as name slugs, frozen in the frame), never the legal footer's links. Decided with the user and recorded in an ADR-194 addendum. Verified by 1763 backend tests, 11 mutation checks, a byte-identity check on all dev variants, green CI (8e70ea7) and a live check on scratch data.
<!-- SECTION:FINAL_SUMMARY:END -->
