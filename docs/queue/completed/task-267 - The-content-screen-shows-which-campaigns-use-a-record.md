---
id: TASK-267
title: The content screen shows which campaigns use a record
status: Done
assignee:
  - '@claude'
created_date: '2026-10-04 09:23'
updated_date: '2026-10-04 11:17'
labels:
  - frontend
  - backend
dependencies: []
type: feature
ordinal: 200067
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Raised by the user 2026-10-04 while trying the variant editor: "we don't have a list of 'used in campaign' on the content screen, but I assume we will work on the content screen later." A manager looking at a record cannot see where it is used. What exists: GET /content/{id}/unsent-campaigns (task-224) answers the unsent campaigns using it, the count the editor shows beside a catalogue act (ADR-186 point 8). A content screen probably wants all campaigns using the record — sent ones too, marked as sent — which is a small extension of the same query (backend/app/campaigns/monitoring.py: unsent_campaigns_using). To be built with the content screen work rather than on its own.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The content detail screen lists the campaigns whose modules use the record, each linked, sent ones marked as such
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. monitoring.campaigns_using(db, record_id, brand_id): each brand campaign with a module bound to the record, plus the variants using it (id, name, channel, stage), in campaign_monitoring order. unsent_campaigns_using is rebuilt on it and keeps its behaviour and tests.
2. GET /content/{id}/campaigns returns Page[ContentCampaign] (ADR-185: grows with use), 404 for another brand's record.
3. ContentDetail.tsx gets a "Used in" section: each campaign linked; each variant linked to its editor with its stage, "sent" marked; a note that slot picks are not listed; "Showing N of M" if paged.
4. Tests: backend (sent marked, unused left out, variants that do not use it left out, brand 404, the unsent count unchanged); client (the list renders with links and the sent mark). Mutation-check. Regenerate schema.d.ts.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-04.
- backend/app/campaigns/monitoring.py: campaigns_using lists each brand campaign with a module bound to the record, with only the variants that use it (id, name, channel, stage). unsent_campaigns_using is now a filter over it, so the content screen, the composer's reach count and monitoring share one definition of "sent" (task-216).
- GET /content/{id}/campaigns returns Page[ContentCampaign]. It is classified as PAGED in test_pagination.py (ADR-185: grows with use), and another brand's record gets a 404.
- ContentDetail.tsx gets a "Used in" section: each campaign is linked and each using variant links to its editor, with channel and stage in monitoring's words (STAGE_LABEL, now exported). A sent variant is bold. It shows "Showing N of M" past one page, and says decision slots that may pick the record are not listed: bound modules only, as for the reach count.
- Tests: 5 new backend tests (one pins the reach rule through the refactor) and 3 new client tests in ContentDetail.test.tsx. Mutation-checked against 12 mutants, each caught. Backend 1222 passed; client tsc clean, vitest 143 passed.
- Checked live: record 101 shows "Demo Campaign 1: Variant 1A (email, sent), Variant 1A (copy) (email, composing)".
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The content detail screen lists where a record is used: every campaign with a module bound to it, each using variant linked with its stage, sent ones marked. It is served by a paged GET /content/{id}/campaigns that shares its "sent" definition with the composer's reach count. Verified by 8 new tests mutation-checked against 12 mutants, both full suites, and a live check.
<!-- SECTION:FINAL_SUMMARY:END -->
