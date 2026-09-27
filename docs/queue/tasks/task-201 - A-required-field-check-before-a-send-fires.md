---
id: TASK-201
title: A required-field check before a send fires
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
labels:
  - backend
dependencies: []
priority: parked
type: bug
ordinal: 104900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** **A required-field check before a send fires** (Q3b). Nothing checks today — `resolve_module_variables` defaults a missing field to `""` and `ModuleVariable.required` is never enforced at render, so an empty push notification ships to a real device. Belongs in Cluster 5's pre-flight.

Source: [[Manager Workflow - design interview]] → What Cluster 2 produced, requirement 1 (Q2.3b). Cluster 5 (Q5.1) placed it: *the system blocks what is broken, and reports what is merely questionable* — an empty required field is broken.

**Verified against the code 2026-09-27:** `resolve_module_variables` (`backend/app/rendering/service.py:257`) falls back to `content.get(var.name, "")` at `:305` and never reads `var.required`; the static path does the same at `:362-369`. `ModuleVariable.required` is declared at `backend/app/modules/registry.py:43` and read only for display (`backend/app/modules/router.py:32`, `backend/app/frontend/router.py:793`).

Related: [[ADR-174 — Channel Readiness Is Asserted, Not Computed]] point 3, [[ADR-177 — A Field Is Defined Once, Required Per Module]]. task-104 is the pre-send checks bundle.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
