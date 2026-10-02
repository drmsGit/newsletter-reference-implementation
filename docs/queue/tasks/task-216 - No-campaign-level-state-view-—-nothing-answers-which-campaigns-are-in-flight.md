---
id: TASK-216
title: No campaign-level state view — nothing answers which campaigns are in flight
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 14:20'
updated_date: '2026-10-02 20:18'
labels:
  - backend
dependencies: []
priority: p1
type: feature
ordinal: 200340
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **No campaign-level state view** (Q4). Nothing answers "which campaigns are in flight" — *in flight* is derived from variants, snapshots and sends.

Source: [[Manager Workflow - design interview]] → What Cluster 5 produced, gap 18 (Q5.4).

**Verified against the code 2026-09-27:** `CampaignDB.status` exists (`backend/app/campaigns/db_models.py:13`, default `"draft"`) and is set only at creation (`backend/app/campaigns/service.py:191,221,232`); the send lifecycle never moves it. No in-flight route in `backend/app/campaigns/router.py`.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Final-design pass 2026-10-02. Governing: ADR-160 point 4 (channel lives on the variant; a variant is planned and sent, not a campaign), ADR-172 (brand-scoped read, other brands absent), ADR-163 by analogy (state computed from facts, not stored). Interview: Manager Workflow Q3.1/3.1b, Q5.4 ('a screen answers one question': monitoring is campaign-level, deliveries send-level).
1. A derived read model, nothing stored. CampaignDB.status stays as is (set only at creation, `backend/app/campaigns/service.py`). It isn't moved, and isn't made to agree.
2. Per-variant stage, the furthest along: sending > scheduled > planned (draft send) > snapshotted (a snapshot with no send yet) > sent (only finished sends: sent / partial_failed / failed / no_recipients) > composing (no snapshot). has_failures marks a failed or partial_failed send.
3. Campaign state (DECISION, user): in_flight if any variant is snapshotted / planned / scheduled / sending; else sent if any variant sent; else in_preparation. Ordered in_flight, in_preparation, sent, then by updated_at desc. Each row carries next_scheduled_at, last_sent_at and the per-variant stages.
4. New `backend/app/campaigns/monitoring.py` (one query per table, assembled in Python, no N+1). Route GET /campaigns/monitoring under the existing policy (view). Response models in `backend/app/campaigns/models.py`. No pagination (task-88).
5. React: a Monitoring screen (DECISION, user: separate from the campaigns list, per Q3.1), with nav entry and rows opening /campaigns/:id. Read-only.
Not touched: the deliveries screen, CampaignDB.status, Jinja.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.

Built 2026-10-02. `backend/app/campaigns/monitoring.py` (campaign_monitoring, one query per table), route GET /campaigns/monitoring (`backend/app/campaigns/router.py`, view), models MonitoredCampaign / MonitoredVariant. React Monitoring screen (`frontend/src/screens/Monitoring.tsx`) with nav entry, rows open the campaign screen. Decided by the user: in flight = approved but not finished (a snapshot no send has used, or a send planned/scheduled/sending); route plus screen. An unknown send status counts as still underway, so a campaign is shown rather than hidden. Two test faults found and fixed during the work: (1) the cross-brand test's cleanup re-assigned rows between brands, which on a shared dev DB could move real data. It failed harmlessly here (brand ids checked; the seeded Brand B is 8700 and untouched), and it was replaced with a fixture ordered so that teardown never moves rows. (2) The ordering test created campaigns in the same order that newest-first produces, so removing the state sort passed it; creation order reversed. Tests: 13 backend (`backend/tests/test_campaign_monitoring.py`, 9 mutants caught), 2 frontend (3 mutants caught). Suite 1024 passed, rc=0; frontend 37. Browser-verified against the dev DB.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Campaign state is now derived (in flight / in preparation / sent, with a failures flag and per-variant stages) from snapshots and sends, never stored. It is served at GET /campaigns/monitoring and shown on a new Monitoring screen. Verified: 15 tests, 12 mutants caught, suite 1024 passed, checked in the browser.
<!-- SECTION:FINAL_SUMMARY:END -->
