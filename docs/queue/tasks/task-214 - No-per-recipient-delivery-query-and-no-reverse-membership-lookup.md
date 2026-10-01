---
id: TASK-214
title: No per-recipient delivery query and no reverse membership lookup
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-01 20:54'
labels:
  - backend
dependencies: []
priority: p2
type: feature
ordinal: 200385
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **No per-recipient delivery query and no reverse membership lookup** (Q5) — and the second is structural, not missing: rule-based membership is **computed at resolution time and never stored**, so only pins are rows. "Which groups is Anna in" is answerable only by resolving every group. Bears on [[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]].

Source: [[Manager Workflow - design interview]] → What Cluster 4 produced, gap 14 (Q4.5).

**Verified against the code 2026-09-27:** delivery lists by snapshot (`backend/app/delivery/router.py:90`) and executions by send instance (`:107`), never by recipient; audience lists members by group only (`backend/app/audience/router.py:72`). No `groups_for_recipient` / `executions_for_recipient`-shaped function exists in `backend/app/`.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
