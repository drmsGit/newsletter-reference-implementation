---
id: TASK-82
title: >-
  Reevaluate the decay model: calendar-time vs. activity-relative decay —
  surfaced 2026-07-15.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 203500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** Reevaluate the decay model: **calendar-time vs. activity-relative decay** — surfaced 2026-07-15. Today decay is measured in absolute calendar time (`age = now - occurred_at`). Edge case: a recipient on holiday for 90 days returns with (arguably) unchanged interest, yet their signals have decayed as if they'd disengaged. Open question whether to slow/pause decay during inactivity (measure decay in "email opportunities seen" or active time rather than wall-clock). **Leaning: probably leave it as calendar-time** — a genuinely interested person reads newsletters even on holiday, so continued non-engagement *is* signal, and decaying + starting fresher on return may be the right call. Noted for reevaluation with real data, not a change now. Depends on / relates to [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]. Source: user, 2026-07-15 (signal-layer design session). **Update (user, 2026-07-15): will most likely stay calendar-time / not build this.** Reasoning: if someone didn't read for 3 months, they also *lived* 3 different months — we can't assume their interests are unchanged from before, so re-earning the signal is more honest than pausing decay. Don't add complexity for a case we can't actually verify. If a specific company disagrees and wants activity-relative decay, the decay function is a code/plugin swap (per ADR-132's "different decay model = code change") — a good candidate for an open-source-community contribution rather than core. Likely to be moved to **Won't Do (core)** unless a real adopter pushes for it.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 240, section "Features", position 35 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
