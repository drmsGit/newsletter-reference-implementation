---
id: TASK-96
title: >-
  Engagement-driven audience suggestions (Phase 3 "use case 2"): system-proposed
  audience blocks based on *engagement* rather than campaign content —
  highly-engaged recipients (`operational_signals_for…
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-10-01 20:54'
labels:
  - backend
dependencies: []
priority: p3
type: feature
ordinal: 204900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — PARKED until the automation workstream begins (do not build standalone).** Engagement-driven audience suggestions (Phase 3 "use case 2"): system-proposed audience blocks based on *engagement* rather than campaign content — highly-engaged recipients (`operational_signals_for_recipient`), reactivation/lapsed (signal decayed below a threshold, per [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]] decay-on-read), and "rested / not emailed lately" (exclude anyone with a recent `delivery_execution`). **Decision (user, 2026-07-26): do NOT build a manual "ask the system to create engagement blocks" trigger.** The rule-block model + content-driven suggestion (Phase 3A/3B, done — commits `c6061bf`/`d5eba2c`, "✨ Suggest audience" from a campaign + "↻ Recalculate") already cover the manual/manager-driven path. Engagement-driven targeting is only worth building as part of the **automation topic**, not as another button a manager clicks: the goal is an AI automation flow where the system picks and sends the right email at the right time to the right person — potentially orchestrated via a platform like **n8n** and/or AI — rather than a human manually assembling engagement segments. When that work starts, the natural shape is to add engagement predicates (recency / frequency / decay-state) as **criteria options on the existing `AudienceRuleBlockDB`** (so they compose with the content-driven include/exclude blocks already built), evaluated/applied automatically by the automation flow rather than hand-triggered. Ties to: the "Bulk send: batching + send-timing model" Needs-ADR item below (send-time optimization is the same "right time" problem), the n8n/AI cost-feedback Feature above, and Phase 3C/3D AI work in `docs/playbook-strategy.md` §6. Source: user, 2026-07-26 (Phase 3 audience session).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 273, section "Features", position 49 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
