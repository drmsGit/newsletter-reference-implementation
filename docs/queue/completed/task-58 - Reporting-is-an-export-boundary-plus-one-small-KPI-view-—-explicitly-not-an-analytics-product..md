---
id: TASK-58
title: >-
  Reporting is an export boundary plus one small KPI view — explicitly not an
  analytics product.
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 13:56'
updated_date: '2026-10-11 16:27'
labels:
  - backend
dependencies: []
priority: p3
type: feature
ordinal: 201100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — PARKED by the user 2026-09-18, with its shape already decided. Do not design further until there is real data to talk about.** **Reporting is an export boundary plus one small KPI view — explicitly not an analytics product.** The user's framing: *"we are no analytics platform, you get what you need and an easy way to export everything."* Concretely: keep the category graph that exists; add a **select a newsletter and/or audience group → KPIs plus summary/averages** view; and make **export to an external BI tool** the answer to everything beyond that. This agrees with [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]'s existing rule that the operational system keeps a bounded window and history is offloaded to the adopter's warehouse, so the export half is already half-decided — see the DWH export boundary item above. Verified 2026-09-18: `app/insight/router.py` exposes three endpoints and no reporting surface at all, so "when there is data" is also "when there is somewhere to look at it".
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The campaign page shows a collapsible Results section once a send has gone out: one row per variant and a campaign line
- [x] #2 Per variant: recipients, sent, delivered (email), failed, excluded by stage, bounced, complaints, total clicks, unique clickers, click rate over sent, unsubscribes; the campaign line is the totals with a pooled rate
- [x] #3 An unsubscribe and a provider suppression record the delivery they came through, so a send counts its unsubscribes; older ones are flagged as not counted
- [x] #4 No export is built; the decision and the how-to direction are recorded in ADR-196
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 164, section "Features", position 11 in that section (top = do next). The description is the original entry, verbatim.

2026-10-11, unparked by the user and designed in a final-design pass, one question at a time; recorded in [[ADR-196 — Reporting Is the Campaign's Results Section; Analysis Belongs in the Adopter's Tools]]. Decisions: (1) the one KPI view is a collapsible section on the campaign page only, which is task-360's shape; no Results screen, no audience-group selector; comparing campaigns is the analytics tool's job. (2) Nothing for unsent sends. (3) Figures per variant: delivery figures, total and unique clicks, unsubscribes; opens get room but are not built until task-353 decides; per-link and per-content figures belong on the content catalogue side (task-359). (4) Campaign line = totals; every click rate is unique clickers over sent, pooled, so email and push compare. (5) Unsubscribes record their delivery: consent_events.delivery_execution_id (migrate_0048, ON DELETE SET NULL), set by the unsubscribe link and by provider suppressions. (6) No export: it is the adopter's IT task, to be a how-to chapter (options such as CSV, endpoints, replica with ETL; message: for detailed analysis there are better tools). Promotion with a CRM and n8n setup on the website is separate. Two definitions set by Claude, not asked: bounced includes soft bounces; failed includes uncertain, like the stored failed_count.
Built: backend/app/campaigns/results.py (computed on read), GET /campaigns/{id}/results (view, working brand, not in MACHINE_READS), frontend/src/components/CampaignResults.tsx on CampaignDetail. The drop-frameless-snapshots script unlinks consent rows instead of deleting them (its foreign-key guard caught the new key).
Verified: tests/test_campaign_results.py (17), 16 backend mutations all killed; CampaignDetail.test.tsx (3 new), 7 frontend mutations all killed; full pytest 1888 passed, Ruff clean, vitest 272, tsc clean. Live check (read only) on Demo Campaign 2 opened from Monitoring: the section shows 8 recipients, 8 sent, 0 delivered and 0 clicks (mock provider: no delivery or click events), and the unsubscribe note. Commit 4e59ed6.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Unparked and designed with the user (ADR-196): the one KPI view is a collapsible Results section on the campaign page, per variant that has sent plus a pooled campaign line, computed on read; unsubscribes now record the delivery they came through so sends can count them; no export is built (a how-to chapter instead). Verified by 17 backend and 3 frontend tests with all mutations killed, full suites green, and a live read-only check on a sent demo campaign.
<!-- SECTION:FINAL_SUMMARY:END -->
