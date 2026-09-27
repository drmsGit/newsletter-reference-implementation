---
id: TASK-90
title: >-
  Audience/segment override mechanism — the second half of the override
  redesign, deferred (2026-07-15) because it depends on Phase 3B
  (system-suggested audience), which isn't built yet: an audience ov…
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 204300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** Audience/segment override mechanism — the second half of the override redesign, deferred (2026-07-15) because it depends on **Phase 3B (system-suggested audience), which isn't built yet**: an audience override deviates from a *system-proposed* audience, but today audience groups are 100% manually assembled (`add_member`/`remove_member`/`find_by_criteria`), so there's no system pick to log a human deviation from. Build once 3B exists, reusing the **shared override foundation** already established by the content-override redesign (Done 2026-07-15): same lifecycle (create → active → reset), same audit/outcome shape (`system_*` vs chosen, retroactive `outcome_delta`), same trust-loop framing — as a separate `AudienceOverrideDB` with its own target (audience group / send) and payload (recipient add/remove), **not** a polymorphic single table (that anti-pattern was rejected in Campaigns Q2). This is also where the **scale/anomaly friction guard** lands (per `docs/playbook-strategy.md` Decision Log 2026-07-05, item 2: low-friction across the board, a "why are you doing this?" prompt only when a manager drastically inflates an already-trusted proposal, e.g. a segment ballooning to 200k) — content overrides are always frictionless, so that guard belongs with audience, not content. The audience-override-via-deletion counterfactual remains partly open in the shadow-variant Needs-ADR item. Source: [[Interview Prep - Content, Campaigns, Audience]] → Campaigns Q3; [[Interview Prep - Decision, Overrides, Insight]] → Overrides Q1.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 256, section "Features", position 43 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
