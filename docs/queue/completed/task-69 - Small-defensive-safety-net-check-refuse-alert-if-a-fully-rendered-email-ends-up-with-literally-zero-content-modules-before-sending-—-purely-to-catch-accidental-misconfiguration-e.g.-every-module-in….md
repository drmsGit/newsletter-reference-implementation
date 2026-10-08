---
id: TASK-69
title: >-
  Small defensive safety-net check: refuse/alert if a fully rendered email ends
  up with literally zero content modules before sending — purely to catch
  accidental misconfiguration (e.g. every module in…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-10-08 19:05'
labels:
  - backend
dependencies: []
type: feature
ordinal: 202200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** Small defensive safety-net check: refuse/alert if a fully rendered email ends up with literally zero content modules before sending — purely to catch accidental misconfiguration (e.g. every module in a variant is decision-slot-driven and all happened to resolve to nothing), not a business-policy decision. Confirmed the composition model (static content blocks) and strategy-plugin system already let a company guarantee content by construction if they want to — this is just a cheap guard against the accidental case, lowest priority. Source: `docs/business-interview-baseline.md` §E3 (via `/business-review`).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 214, section "Features", position 22 in that section (top = do next). The description is the original entry, verbatim.

Closed 2026-10-08 in the pre-review queue cleanup, without a build of its own: superseded by task-228 (ADR-086 addendum 2026-10-08). Its accidental case - every module slot-driven and all resolving to nothing - is exactly task-228's floor: a recipient for whom nothing but the envelope rendered is not sent to, recorded as excluded under the stage render ("nothing to show"), and a send in which that happens to everyone ends no_recipients. The "alert" half is the send's detail, which counts the render exclusions; no notification is sent, consistent with Manager Workflow Q1.7's no-notification principle.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Not built on its own: superseded by task-228, whose floor skips any recipient for whom nothing but the envelope rendered and records why. Closed in the 2026-10-08 queue cleanup.
<!-- SECTION:FINAL_SUMMARY:END -->
