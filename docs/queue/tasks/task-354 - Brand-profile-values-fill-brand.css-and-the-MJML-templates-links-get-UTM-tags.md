---
id: TASK-354
title: Brand profile values fill brand.css and the MJML templates; links get UTM tags
status: To Do
assignee: []
created_date: '2026-10-11 08:39'
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
- [ ] #1 Two profiles with different colours and fonts produce visibly different emails from the same variant
- [ ] #2 Values reach both brand.css and the module templates
- [ ] #3 Content links carry the profile's UTM parameters; unsubscribe, imprint and privacy links do not
<!-- AC:END -->
