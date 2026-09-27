---
id: TASK-58
title: >-
  Reporting is an export boundary plus one small KPI view — explicitly not an
  analytics product.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: parked
type: feature
ordinal: 201100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — PARKED by the user 2026-09-18, with its shape already decided. Do not design further until there is real data to talk about.** **Reporting is an export boundary plus one small KPI view — explicitly not an analytics product.** The user's framing: *"we are no analytics platform, you get what you need and an easy way to export everything."* Concretely: keep the category graph that exists; add a **select a newsletter and/or audience group → KPIs plus summary/averages** view; and make **export to an external BI tool** the answer to everything beyond that. This agrees with [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]'s existing rule that the operational system keeps a bounded window and history is offloaded to the adopter's warehouse, so the export half is already half-decided — see the DWH export boundary item above. Verified 2026-09-18: `app/insight/router.py` exposes three endpoints and no reporting surface at all, so "when there is data" is also "when there is somewhere to look at it".
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 164, section "Features", position 11 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
