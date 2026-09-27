---
id: TASK-95
title: >-
  AI/system recommendation layer on top of the (human-governed, per [[ADR-080 —
  Human-governed Taxonomy Before AI Selection]]) category taxonomy — e.g.
  "system suggests promoting this to a main categor…
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 204800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** AI/system recommendation layer on top of the (human-governed, per [[ADR-080 — Human-governed Taxonomy Before AI Selection]]) category taxonomy — e.g. "system suggests promoting this to a main category" or "system suggests this relates to category X" based on usage frequency/scoring. Reuses the same propose-don't-impose trust-building pattern already designed for content overrides (`docs/playbook-strategy.md` Decision Log, 2026-06-24) rather than making hierarchy itself emergent/scored (rejected — see Content Q5 addendum). Depends on the Phase 3C signal layer (usage/frequency signals don't exist yet) — future work, not current priority. Source: [[Interview Prep - Content, Campaigns, Audience]] → Content Q5 (addendum).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 271, section "Features", position 48 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
