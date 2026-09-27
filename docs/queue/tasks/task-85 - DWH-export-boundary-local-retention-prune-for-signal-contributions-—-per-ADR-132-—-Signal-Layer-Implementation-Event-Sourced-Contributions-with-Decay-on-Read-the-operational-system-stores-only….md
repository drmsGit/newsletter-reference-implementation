---
id: TASK-85
title: >-
  DWH export boundary + local retention/prune for signal contributions — per
  [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with
  Decay-on-Read]], the operational system stores only…
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 203800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** DWH export boundary + local retention/prune for signal contributions — per [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]], the operational system stores only a bounded window of signal contributions (a few operational half-lives); long-term historical engagement + AI training data belong in the adopter's DWH / data lake. Needs: an export path (contributions are exportable in a stable shape), a local retention/prune policy (tied to the general data-lifecycle Needs-ADR item), and documentation that Phase 3D AI trains from the DWH, not local tables. Not required for the first operational signal build; sequenced after it, before real historical volume accrues. Source: user, 2026-07-15 (signal-layer design session).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 246, section "Features", position 38 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
