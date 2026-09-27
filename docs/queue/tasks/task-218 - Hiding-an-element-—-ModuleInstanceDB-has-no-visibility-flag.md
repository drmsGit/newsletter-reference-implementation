---
id: TASK-218
title: Hiding an element — ModuleInstanceDB has no visibility flag
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
labels:
  - backend
dependencies: []
priority: parked
type: feature
ordinal: 208300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** **A capability with no model, found in the editor brief:** *hiding an element*. `ModuleInstanceDB` has no visibility flag; the only "hidden" in the codebase is [[ADR-086 — Decision Slots Fail Gracefully]]'s hidden slot, which is automatic degradation rather than a manager's choice.

Source: [[Manager Workflow - design interview]] → What Cluster 3 produced.

**Verified against the code 2026-09-27:** `ModuleInstanceDB` (`backend/app/campaigns/db_models.py:75-83`) has `id`, `variant_id`, `module_type`, `position`, `content_record_id`, `module_data`, `decision_slot_id` and timestamps — no visibility column.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
