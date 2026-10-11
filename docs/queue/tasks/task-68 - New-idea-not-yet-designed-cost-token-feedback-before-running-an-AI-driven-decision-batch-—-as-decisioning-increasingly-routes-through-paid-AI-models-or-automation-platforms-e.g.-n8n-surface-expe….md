---
id: TASK-68
title: >-
  New idea, not yet designed: cost/token feedback before running an AI-driven
  decision batch — as decisioning increasingly routes through paid AI models or
  automation platforms (e.g. n8n), surface expe…
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-10-11 19:15'
labels:
  - backend
dependencies: []
type: feature
ordinal: 202100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** New idea, not yet designed: cost/token feedback before running an AI-driven decision batch — as decisioning increasingly routes through paid AI models or automation platforms (e.g. n8n), surface expected cost/token usage before committing to a run, for the recipients who *will* receive something (separate from the consent gate above, which is about not running decisioning for people who won't). Ties into the pluggable AI-capability extension points from the E1 resolution and the not-yet-built Phase 3C/3D AI work. Source: `docs/business-interview-baseline.md` §M3 (via `/business-review`).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 212, section "Features", position 21 in that section (top = do next). The description is the original entry, verbatim.

2026-10-11, the user changed the scope: no cost display before running a batch is needed; running Condor in production showed how cheap the calls are. What is wanted instead is basic spend monitoring under Settings: what was spent today, yesterday and in the current budget period (the period exists since task-345, ADR-144 addendum 2026-10-11; settings.ai_budget_status already reports the period). An AI action that cannot run because of the spending limit keeps showing its warning, as today.
<!-- SECTION:NOTES:END -->
