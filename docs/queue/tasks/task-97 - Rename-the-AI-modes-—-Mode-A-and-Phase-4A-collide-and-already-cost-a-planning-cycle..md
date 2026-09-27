---
id: TASK-97
title: >-
  Rename the AI modes — "Mode A" and "Phase 4A" collide and already cost a
  planning cycle.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - docs
dependencies: []
type: docs
ordinal: 205000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Docs]** **Rename the AI modes — "Mode A" and "Phase 4A" collide and already cost a planning cycle.** Surfaced 2026-08-07 (user). The AI capability layer uses **Mode A / B / C** ([[ADR-141 — In-App Assistive AI Actions]] / [[ADR-142 — Autonomous Workflows and the Automation Boundary]] / [[ADR-143 — AI-Assisted Development Boundary]]) while the roadmap uses **Phase 4A / 4B / 4C**. They are unrelated — Mode A is in-app assistive AI, Phase 4A is deciding the playbook's chapter structure and voice — and the user conflated them, concluding that Phase 4A was finished because the subject-line feature (Mode A) was. That misread a planning session. **Fix: name the modes by function** — Assistive / Autonomous / Development — rather than by letter, in the three ADRs, the roadmap and the backlog. Cheap now, and it removes a trap a playbook *reader* will hit too, since both vocabularies appear in the published material. Note the ADR titles already describe the functions accurately; it is the shorthand "Mode A" that does the damage. Source: user, 2026-08-07.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 275, section "Features", position 50 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
