---
id: TASK-143
title: >-
  Add `subject`/`preheader` fields to `CampaignDB`/`VariantDB` (currently
  missing — `send_instance.name` is reused as the subject at send time,
  `delivery/service.py:164`, conflating an internal label w…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 500700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Feature]** Add `subject`/`preheader` fields to `CampaignDB`/`VariantDB` (currently missing — `send_instance.name` is reused as the subject at send time, `delivery/service.py:164`, conflating an internal label with the actual email subject line; same gap independently flagged in the Delivery cluster's review of `send_send_instance`). Part of a broader "campaigns/content need more first-class fields (settings, etc.)" effort not yet done — not an oversight in this one spot, just not reached yet. Source: [[Interview Prep - Content, Campaigns, Audience]] → Campaigns Q4. **Done 2026-07-15** — put `subject`/`preheader` on **`VariantDB`** (not `CampaignDB`): "one campaign = one email" but variants are the A/B versions, so per-variant subject/preheader is what a real send needs. `send_send_instance` now sends `variant.subject` (falling back to `send_instance.name` only when a variant has no subject, so old data still sends); `preheader` is emitted as a hidden inbox-preview span at the top of the rendered `<body>` (escaped) in both preview and send. Variant create/edit UI on the campaign detail page carries both fields, and the header flags "subject not set" when missing. Verified live end-to-end: drove a full snapshot→send-instance→execution→send and confirmed the mock provider received `"Your summer beach escape awaits"` (the variant subject) rather than the send-instance's internal label; preheader span confirmed present at body top in a live render. **⚠️ REVERSED BY DESIGN 2026-09-12 — done, then superseded, not a defect.** [[ADR-162 — Channel Rendering and Artifacts]] §1 moves `subject` and `preheader` off `VariantDB` and into **module fields declared in a manifest**, so that nothing on the variant is channel-shaped. The columns this item added require a migration out again. Two things this buys that the column form could not: a personalised subject line becomes an ordinary override (the override layer edits module fields), and Mode A's "suggest subject & preheader" generalises to a push title or letter salutation instead of reaching into variant columns. Downstream files: `app/ai/tasks/subject_preheader.py`, `app/campaigns/{db_models,models,service}.py`, `app/rendering/service.py`, `app/frontend/router.py`, `app/templates/campaign_detail.html`.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 515, section "Done", position 7 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
