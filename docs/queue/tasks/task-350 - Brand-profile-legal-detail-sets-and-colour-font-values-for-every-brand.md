---
id: TASK-350
title: 'Brand profile: legal-detail sets and colour/font values for every brand'
status: To Do
assignee: []
created_date: '2026-10-10 21:17'
updated_date: '2026-10-10 21:19'
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
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A brand can hold several named legal-detail sets, one marked default
- [ ] #2 A campaign or variant can choose a set; otherwise the default applies
- [ ] #3 Every marketing email's fixed footer shows the chosen set's details beside the unsubscribe link
- [ ] #4 A marketing send is refused while the applicable set lacks a required field
- [ ] #5 A brand's colour and font values change how its emails look
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10, from writing ADR-193, open for the final-design pass:
- which of the four legal fields a send requires (only the imprint was stated);
- which choice wins when both a campaign and a variant pick a legal set;
- whether transactional mail and test sends carry the legal details (transactional is task-134);
- whether the per-brand theme values join ADR-183's template and CSS fingerprint, or are frozen like the legal set.
Also, the footer_html docstring in backend/app/subscriptions/texts.py (around :13-14) says the line lasts 'until task-301's designed footer replaces it'. It does not any more (ADR-193, ADR-191 addendum 2026-10-10); reword it here.
<!-- SECTION:NOTES:END -->
