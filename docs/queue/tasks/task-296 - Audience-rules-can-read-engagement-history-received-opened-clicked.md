---
id: TASK-296
title: 'Audience rules can read engagement history: received, opened, clicked'
status: To Do
assignee: []
created_date: '2026-10-06 19:59'
labels:
  - backend
dependencies:
  - TASK-295
type: feature
ordinal: 200389
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-293 interview (2026-10-06, with the user); recorded in [[ADR-188 — Audience Rules Are Flat, and May Read Engagement History]] points 4 and 5 and [[Audience Write Surface - final design pass]] decision 7. Closes task-215 (audience criteria cannot express delivery history). Second of four build tasks.

**Build** in `backend/app/audience/service.py` (`find_by_criteria` and the schema from build 1): an engagement field — **what** (received, opened, clicked; "opened" included by the user's decision, the company's call), **which mailing** (a specific send instance, any send of a campaign, any send on the channel), **when** (absolute from/to, or relative: within the last N days / more than N days ago) — reading `DeliveryExecutionDB` (received = a sent execution, by `sent_at`) and `EngagementEventDB` (opened/clicked by `event_type`, `occurred_at`), scoped to the brand's sends. It combines with the other fields in a rule; "did not" is an exclusion rule (point 5), so no negated field. Because it lives in `find_by_criteria`, the arithmetic (task-213), the per-person lookup (task-214) and sends all follow.

**Measure** resolution with engagement rules on the dev data and add indexes where a plan shows a scan (these are the fastest-growing tables; task-106 is the benchmark task).

Tests: each what/which/when, absolute and relative windows, brand isolation, exclusion for "did not", the arithmetic and memberships following; mutation-checked.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A rule can match received, opened or clicked, for a send, a campaign or any send, in an absolute or relative window
- [ ] #2 'Did not' works as an exclusion rule; the arithmetic and per-person lookup follow
- [ ] #3 Resolution with engagement rules is measured on dev data, indexed where needed
<!-- AC:END -->
