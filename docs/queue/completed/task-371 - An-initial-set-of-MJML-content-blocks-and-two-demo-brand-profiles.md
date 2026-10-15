---
id: TASK-371
title: An initial set of MJML content blocks and two demo brand profiles
status: Done
assignee:
  - '@claude'
created_date: '2026-10-11 20:44'
updated_date: '2026-10-15 21:14'
labels:
  - backend
dependencies: []
type: feature
ordinal: 200300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** For the November 2026 presentations (docs/business/PRESENTATIONS-2026-11.md), raised by the user 2026-10-11: "initial set of mjml content blocks and 2 brand profiles (marketing / transactional), so example emails look good". Today the email modules are hand-written HTML templates in storage/modules/email/; ADR-131 names MJML as the target source format, and nothing compiles MJML yet. Brand profiles exist since task-350 (ADR-194); the demo needs two good ones, one marketing and one transactional.

**Design questions for its final-design pass.** Whether MJML is introduced now (a compile step, its dependency under ADR-173, how the compiled HTML is cached and fingerprinted for the frame, ADR-183) or the demo set stays HTML. Which blocks the initial set has (hero, image and text both ways, stack, CTA, header, footer, section heading). The two profiles as seed data, with the images from asset management (task-112) once it exists.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Seven MJML blocks render: Hero, Headline, Image left, Image right, Column, Single text, CTA
- [x] #2 Only the Hero and CTA carry buttons; other links are text links; image first on mobile
- [x] #3 Two adjacent Columns share one 50:50 row, each side crediting its own record
- [x] #4 Compiled HTML is committed and CI fails when it is stale
- [x] #5 Single Stack is retired: rendered where used, not offered, refused when added
- [x] #6 A library image uses its own alt text; forms ask alt only with a web address
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-15 (commit bc3a3e9). Decisions with the user, one at a time: one square image format, one new content field (body_long, the short/long split); only the Hero CTA and the CTA block are real buttons, everything else a text link ("Label →"); left-aligned, 50:50; image first on mobile; MJML compiled when a block is written (not daily, not on request) with CI rejecting stale output; two columns are two half-width Column modules, paired; keep Editorial, retire the rest (Single Stack), deleted at the next full reset (task-381); alt text only for web addresses.

Records: ADR-198 (new), addenda of 2026-10-15 on ADR-131 (compile when written), ADR-197 (a library image always uses its own alt), ADR-179 (section_heading's first use withdrawn), ADR-187 (compile order, the new blocks' hideable fields), and ADR-198's own final-design-pass addendum. The final-design-pass points were decided by me without asking (the user said to proceed): Headline is decorative and uses a new field heading; H3 is headline_medium; pairing is greedy in order and an empty module does not break a row; Single Stack keeps rendering its section_heading; labels Link text / Link.

Where it lands: sources in storage/modules/email/*.mjml with partials _attributes, _text_link, _column_content; frontend/scripts/build-modules.mjs (npm run build:modules, --check in CI) pastes the partials itself because MJML 5.4.1 drops body fragments included in a column and ignores included mj-attributes; only @media/.moz-text-html rules and the viewport meta go into _mjml_head.html, added by email_document only when MJML markup is in the body (older documents byte for byte). Pairing: manifest key pairs, Half/module_part/lay_out in backend/app/rendering/service.py, used by both the live and the frame render; links tagged per side. Retired: manifest key retired, list_manifests(offered=True), _refuse_module_type refuses add/switch.

Found in the live check: without MJML's viewport meta a phone lays the email out 980px wide and nothing stacks; added, with a test.

Not done here: the two demo brand profiles in this task's title moved to task-71 (realistic seed content), which also needs real square images (seed records hold relative /static/img paths that do not load in the preview). Square is a content convention; nothing crops or checks the ratio. Body text (long) lists before (short) in the record form, from the merged declared order.

Verification: pytest 1985 passed, Ruff clean; vitest 300 passed, tsc, eslint (no errors), build:modules --check; mutation checks: 9 backend and 5 client mutations, all caught; live check on scratch campaign "SCRATCH task-371 blocks" (Add "Two columns", CTA with two buttons, Headline, preview desktop and 375px).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Seven MJML email blocks (Hero, Headline, Image left, Image right, Column, Single text, CTA), compiled when written and checked in CI; Columns pair 50:50; Single Stack retired (task-381 deletes it); library images always use their own alt. ADR-198 plus addenda on ADR-131, -179, -187, -197. Verified: pytest 1985, vitest 300, mutation checks all caught, live check on a scratch campaign at desktop and 375px, CI green on bc3a3e9. The two demo brand profiles moved to task-71.
<!-- SECTION:FINAL_SUMMARY:END -->
