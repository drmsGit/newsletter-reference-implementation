---
id: TASK-87
title: >-
  New idea, not yet designed: a "most recipients matched" tiebreak variant for
  personalized decision strategies — when candidates tie in
  `recipient_top_score`, prefer the one that also matches the most…
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 204000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** New idea, not yet designed: a "most recipients matched" tiebreak variant for personalized decision strategies — when candidates tie in `recipient_top_score`, prefer the one that also matches the most *other* recipients (a global popularity/social-proof signal), instead of (or as an option alongside) the explicit random tiebreak. This is a bigger design question than a simple tiebreaker — it injects a cross-recipient signal into what's currently a purely individual-preference-driven strategy, and would need its own query/strategy design (possibly a distinct strategy variant, e.g. `recipient_top_score_popularity_tiebreak`, rather than baked into the existing one). Lowest priority — parked as an idea, not scoped. Source: [[Interview Prep - Decision, Overrides, Insight]] → Decision Q7 (alternative considered, kept separate).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 250, section "Features", position 40 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
