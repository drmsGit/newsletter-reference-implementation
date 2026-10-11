---
id: TASK-360
title: 'Monitoring: a campaign opens its results overview, not its editor'
status: Done
assignee: []
created_date: '2026-10-11 10:01'
updated_date: '2026-10-11 16:33'
labels:
  - frontend
  - backend
dependencies: []
type: feature
ordinal: 209800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Raised by the user on 2026-10-11: on the Monitoring screen, choosing a campaign opens the campaign's editor page (frontend/src/screens/Monitoring.tsx:74, onRowAction navigates to /campaigns/{id}). From Monitoring a manager wants to see how the campaign went, not edit it. The user's shape for it: Monitoring stays the **first-glance overview**; the detail on categories and content KPIs lives in the graph (task-359).

**What it would show, per campaign.**
- Sent: per send and variant, delivered, failed, excluded and skipped counts, and the click rate (opens are under discussion in task-353, so they are not assumed here).
- Not sent yet: what is planned or scheduled, and what is still missing (the readiness checks the send would make, including brand-profile completeness since task-357).

**What exists.** GET /campaigns/monitoring (backend/app/campaigns/router.py:137) gives the list's stages per variant. Per-send results are in the delivery service (send instances, executions, sent_count) and on the Deliveries screens.

**Open for its final-design pass.**
- Whether this is a new screen (/monitoring/{campaign id}) or the campaign page's own results tab.
- The scope against task-58, which limits reporting to an export plus one small KPI view: this overview may be that view.
- Which figures, and whether clicks are counted per recipient or per click.

**Related.** task-58, task-353, task-359; ADR-176 (audience re-resolution), ADR-183 (what was sent).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Choosing a campaign on Monitoring opens a results overview
- [x] #2 The scope is decided against task-58
- [x] #3 A sent campaign shows its delivery figures and click rate; the unsent half was dropped by the user on 2026-10-11 (nothing is shown for unsent sends)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-11, the user, an alternative to a new screen: Monitoring may keep linking to the campaign page, if the campaign page itself shows the scheduled data (not sent yet) and/or a limited set of KPIs (sent). Then no extra screen is needed. The information does not have to be always visible: it can be a collapsible section on the campaign page. This answers the final-design pass's first open question (a new screen or the campaign page) in favour of the campaign page, unless the pass finds a reason against it.

2026-10-11, task-58's design pass (ADR-196) settled this task's scope: the campaign page's collapsible Results section is the overview, and Monitoring keeps linking to the campaign. Built in commit 4e59ed6. The user decided nothing is shown for unsent sends, so AC #2's planned-and-missing half is dropped; a dry-run readiness check would be its own task if wanted. What may remain here: nothing, unless the user wants Monitoring's rows to carry a figure.

Closed 2026-10-11 as covered by task-58 (commit 4e59ed6, ADR-196): Monitoring links to the campaign page, whose collapsible Results section is the overview. Verified there: live check from Monitoring on Demo Campaign 2 showed the section; tests/test_campaign_results.py and CampaignDetail.test.tsx cover the figures.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Covered by task-58: the campaign page's collapsible Results section is this overview (ADR-196); Monitoring keeps linking to the campaign. The unsent half was dropped by the user. Verified by task-58's tests and its live check opened from Monitoring.
<!-- SECTION:FINAL_SUMMARY:END -->
