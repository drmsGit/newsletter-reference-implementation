---
id: TASK-140
title: >-
  Build the Signal layer (Phase 3C, [[ADR-110 — Insight Layer Transforms Events
  Into Signals]]/[[ADR-112 — Signals Use Time-Based Decay]]/[[ADR-113 — Separate
  Operational and Historical Signals]]) — re…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 500400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Feature]** Build the Signal layer (Phase 3C, [[ADR-110 — Insight Layer Transforms Events Into Signals]]/[[ADR-112 — Signals Use Time-Based Decay]]/[[ADR-113 — Separate Operational and Historical Signals]]) — replace `apply_event_to_preferences`'s direct writes to mutable `RecipientPreferenceDB.score` with a proper Signal abstraction supporting decay and operational/historical separation. Source: [[Interview Prep - Decision, Overrides, Insight]] → Insight Q1. **Designed 2026-07-15 in [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]] and implemented.** New `SignalContributionDB` append-only log (evolved `preference_update_logs`): `(recipient, category, contribution_type, base_weight, occurred_at, event_id, source)`. A signal is a decay-weighted sum computed on read — `Σ base_weight × 0.5^(age/half_life)` (`app/insight/signals.py`), never a stored running total. **`RecipientPreferenceDB` (the mutable running-total) dropped**; the decision strategy (`recipient_top_score`), audience `find_by_criteria`, and the recipient/category frontend views all read `get_operational_signal(...)` / `operational_signals_for_*` instead. `apply_event_to_preferences` → `apply_event_to_signals`: click/open events become per-category contributions scaled by content-category relevance (open weight 0 by default — Apple-MPP noise); unsubscribe handled on the consent path, not per-category. Manual/declared preferences are `manual` contributions (heavy base weight = declared magnitude, 180-day half-life; no permanent floor — behavior wins over time). Seed's manual preferences migrated to manual contributions. Verified live: decay halves correctly (click every 45d, manual every 180d), a click on Mallorca added +5 to Beach / +3.5 to Family (category-weighted), decision score matches the old model (~910 for Anna/Mallorca), recipient/category views render signals. 8 new signal tests + the 13 override tests pass (21 total). Prerequisite now satisfied for: category archive-vs-decay (an archived category just stops adding contributions), negative category-affinity, AI-taxonomy recs, Phase 3B/3D. Companion items (anti-bubble exploration, conversion sourcing, DWH export/retention) tracked separately in Features.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 509, section "Done", position 4 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
