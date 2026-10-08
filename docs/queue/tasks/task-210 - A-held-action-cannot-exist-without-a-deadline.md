---
id: TASK-210
title: A held action cannot exist without a deadline
status: In Progress
assignee:
  - '@claude'
created_date: '2026-09-27 14:20'
updated_date: '2026-10-08 18:29'
labels:
  - backend
dependencies: []
priority: p2
type: feature
ordinal: 200420
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **A held action cannot exist without a deadline** (Q7). `expires_at` is `nullable=False` and `default_ttl_seconds: int` is not optional, so "content review does not expire" is a schema change plus a hand-written migration, and every comparison must then read null as *never expires* rather than *expired*. Touches [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §4.

Source: [[Manager Workflow - design interview]] → What Cluster 1 produced, gap 8 (Q1.7).

**Verified against the code 2026-09-27:** `expires_at` is `nullable=False` at `backend/app/approvals/db_models.py:94`; `default_ttl_seconds: int` at `backend/app/approvals/actions/base.py:58`; the service always sets `now() + ttl` (`backend/app/approvals/service.py:115,126`); `expires_at: datetime` is non-optional in `backend/app/approvals/models.py:30`. `backend/app/approvals/service.py:76` already handles `expires_at is None` defensively.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
