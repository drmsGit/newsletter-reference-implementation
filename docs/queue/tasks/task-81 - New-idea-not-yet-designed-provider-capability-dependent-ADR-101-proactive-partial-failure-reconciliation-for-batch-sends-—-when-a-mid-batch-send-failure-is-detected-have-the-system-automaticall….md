---
id: TASK-81
title: >-
  New idea, not yet designed, provider-capability-dependent (ADR-101): proactive
  partial-failure reconciliation for batch sends — when a mid-batch send failure
  is detected, have the system automaticall…
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 203400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** New idea, not yet designed, provider-capability-dependent (ADR-101): proactive partial-failure reconciliation for batch sends — when a mid-batch send failure is detected, have the system automatically check the provider's own send log/events for the affected send and surface "these N recipients already received this send — exclude them from a retry?" instead of requiring manual lookup via the provider's dashboard. Lowest priority — parked idea, explicitly deferred as an IT/ops concern for now rather than something to automate immediately. Source: [[Interview Prep - Delivery, Providers, Recipients]] → Delivery Q3 (addendum).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 238, section "Features", position 34 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
