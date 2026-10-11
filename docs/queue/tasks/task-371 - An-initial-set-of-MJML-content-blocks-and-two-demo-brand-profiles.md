---
id: TASK-371
title: An initial set of MJML content blocks and two demo brand profiles
status: To Do
assignee: []
created_date: '2026-10-11 20:44'
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
