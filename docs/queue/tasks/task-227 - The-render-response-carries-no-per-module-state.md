---
id: TASK-227
title: The render response carries no per-module state
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
updated_date: '2026-10-01 20:54'
labels:
  - backend
dependencies: []
priority: p2
type: feature
ordinal: 200365
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** The render response carries no per-module state; slot states exist only as HTML comments. A slot that **found nothing** is marked distinctly from one that has not run (4.4) — *the system tried and found nothing* is not *nobody tried*. Identical appearance, different meaning, only one actionable — **and collapsing them trains a manager to ignore both.**

| # | Gap | Where |
|---|---|---|
| 23 | The render response carries no per-module state; slot states exist only as HTML comments | `rendering/router.py` |

Source: [[Variant Editor - design interview]] → What Cluster 4 produced, gap 23 (Q4.4).

**Verified against the code 2026-09-27:** `RenderedVariant` (`backend/app/rendering/router.py:16-28`) holds `variant_id`, `channel`, `role`, `artifact_body` and `fields`. Slot state appears only as HTML comments at `backend/app/rendering/service.py:324` (slot hidden) and `:391` (unknown module).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
