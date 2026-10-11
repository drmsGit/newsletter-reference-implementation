---
id: TASK-351
title: >-
  Visible header and footer modules render from the brand profile, marked
  decorative
status: Done
assignee:
  - '@claude'
created_date: '2026-10-10 21:17'
updated_date: '2026-10-11 10:41'
labels:
  - backend
  - frontend
dependencies:
  - TASK-350
type: feature
ordinal: 200980
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Slice 3 of 5 of the brand-profile design (ADR-194, 2026-10-11; it supersedes ADR-193, which first described these modules with content from content records).

The visible header (logo, menu links) and footer (links, service hotline, footer texts) are modules a manager places in an email, or leaves out. They render from the variant's brand profile, so switching the profile switches them. The footer module adds one optional per-email free text for a special note. The fixed legal line is appended by the frame regardless (slice 1, task-350).

Their manifests declare "decorative": true, and the nothing-to-show check (task-228; ADR-086's 2026-10-08 addendum) ignores decorative modules: an email holding only decorative modules plus the envelope still counts as nothing to show. The header's logo is a profile image field, an https URL until asset management exists (task-112).

The name `header` is free since task-349. Version-1 frames still read their `header` as the envelope, keyed on the frame version, so the new visible `header` lives only in version-2 frames. Codex's test_envelope_frame_boundaries.py already pins that boundary with a stand-in module.

Depends on task-350 (the profile).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A header module (logo, menu) and a footer module render from the variant's brand profile
- [x] #2 The footer module carries one optional per-email free text
- [x] #3 Their manifests declare decorative: true, and an email holding only decorative modules and the envelope is skipped as nothing to show
- [x] #4 An old version-1 frame still renders and reconstructs as sent
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final-design pass 2026-10-11, decided with the user one question at a time:
- D1 Link lists (the header menu, the footer links) are a new field type, links: a text box, one link per line written "Label | https://address", any number, in the order written, checked on save.
- D2 The shipped setup file declares Header: logo (image), logo_alt (text), logo_link (url), menu_links (links); Footer: footer_links (links), service_hotline (text), footer_text (multi-line text). Empty fields leave their part out.
- D3 https everywhere: url, image and links fields refuse http:// (also the legal imprint and privacy links). Values already saved are only refused on their next save; frozen frames are untouched.

Settled in the pass without a question:
- Header module (storage/modules/email/header.html/.json): cms false, no fields of its own, decorative. Renders the logo (an img with its alt text, wrapped in a link when logo_link is set) and the menu links from the email's profile.
- Footer module (footer.html/.json): cms false, decorative, one optional per-email field footer_note (multi-line, in storage/fields.json). Renders the note, then the profile's footer links, hotline and footer text. The legal footer follows it, appended by the frame (task-357).
- Templates read link lists through a Jinja filter, links, registered on the rendering environment: {% for link in profile.menu_links | links %}.
- Every link these modules render carries the profile's UTM tags (task-354 D3), never nl_content: they are not content.
- Manifests gain the key decorative (default false, MANIFEST_KEYS and ModuleManifest). what_rendered skips decorative modules, so an email of only decorative modules and the envelope is nothing to show (ADR-086 addendum 2026-10-08).
- Version boundaries: a version-1 frame still reads its header as the envelope (lookup_type, keyed on the version); the visible header exists only in frames of version 2 and later. No frame-version bump.
- brand.css gains classes for the two modules, with var() values where a starter look field fits.
- Frontend: the profile form shows links fields as a text box with the format hint; the variant editor offers the two modules like any other (accepted_module_types).
ADR: a dated ADR-194 addendum for D1-D3 and the decorative key, via adr-author.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10, from writing ADR-193: the url field type has no server-side https check. The only check is the editor's <input type=url> (frontend/src/components/EditorFields.tsx around :66), which accepts any scheme. 'The logo is an https URL' therefore needs enforcing here (or in the field model) for the header's logo field.

2026-10-11: rescoped by the brand-profile design session (ADR-194 supersedes ADR-193). The original description, kept verbatim:

**[Feature]** Nothing a recipient sees at the top or bottom of an email exists as a module: the email modules are cta, editorial, header (the envelope), hero, img_left, img_right and single_stack.

Decided by the user 2026-10-10 (task-301, ADR-193 points 1, 4 and 5):
- The designed visible header (a logo) and footer (links, special texts) are ordinary modules a manager places. Several footer variants per brand are several footer modules.
- Their content comes from content records, which already belong to one brand.
- Their manifests declare "decorative": true, and task-228's nothing-to-show check ignores decorative modules: an email holding only those plus the envelope still counts as nothing to show (ADR-086, 2026-10-08 addendum).
- The header's logo is an https URL in its content for now, and an asset id once task-112 exists.

Depends on the envelope rename (the name header must be free). Third of three build tasks from task-301. task-108's section heading will use the same flag.

2026-10-11, built. Commits eb8b346 (ADR-194 addendum 2026-10-11 (fourth)) and ad46272. Before it, Codex doc-14's two regressions in task-350's code were fixed with their tests (98b6d29).

Decided with the user (D1-D3 in the plan): link lists are a new field type, links (Label | https://address per line); the setup file ships seven header and footer fields; https everywhere (url, image and links).

Where it landed:
- storage/modules/email/header.html/.json and footer.html/.json: cms false, decorative. The header: logo (linked when logo_link is set) and menu, nothing of its own, and nothing at all while both are empty. The footer: footer_note (new in storage/fields.json, richtext, optional), then the profile's footer links, hotline and text.
- modules/registry.py: manifest key decorative (MANIFEST_KEYS, ModuleManifest.decorative).
- rendering/frame.py what_rendered: decorative modules never count as content (looked up by today's name via lookup_type).
- rendering/service.py: parse_links and the Jinja filter links.
- brand_profiles: FIELD_TYPES gains links; _URL is https only; links lines checked on save.
- storage/brand_profile.json: Header (logo, logo_alt, logo_link, menu_links) and Footer (footer_links, service_hotline, footer_text) groups. brand.css: module-header and module-footer classes, using var() where a look field fits.
- Frontend: links fields are a text box with the format hint.
- Tests: test_header_footer.py (14). Updated: test_envelope_rename (header is now the visible decorative module), test_composer_audit (an unknown type for a refused write, as header now exists), BrandProfiles.test (links box). Codex's envelope-boundary tests pass unchanged with the real header installed.

Verification: backend 1778 passed, Ruff clean; frontend 263 passed, tsc and eslint clean. 7 mutations: 6 caught after pinning the empty-header case; the 7th (looking up a version-1 header by its frozen name) is equivalent, because the envelope is excluded either way. Byte-identity: with no profile values the extended brand.css inlines the existing modules exactly as the original did. Live check 2026-10-11 on scratch data: an http logo was refused on its field; in the variant editor Header and Footer were offered, added, and the note typed; the preview showed the logo, menu, note, footer links, hotline and text; the snapshot had them in that order before the legal footer, the menu link with UTM tags and no nl_content, the imprint link untagged. Scratch profile deleted through the API, campaign rows removed by id.

Noticed, not changed: the editor lists the header as "Header · typed in" though it has no fields of its own; the live editor preview shows no legal footer (as since task-357).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Slice 3 of brand profiles: header and footer modules render from the email's brand profile (logo and menu; a per-email note, then footer links, hotline and text, before the legal footer), are decorative so an email of only them and the envelope is nothing to show, and version-1 frames still read header as the envelope. Link lists are a new field type (Label | https://address per line), and profile addresses are https only; decided with the user and recorded in an ADR-194 addendum. Verified by 1778 backend and 263 frontend tests, mutation checks, a byte-identity check, green CI (ad46272) and a live check on scratch data.
<!-- SECTION:FINAL_SUMMARY:END -->
