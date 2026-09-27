---
id: TASK-195
title: >-
  Editing a signal *weight* in Settings changes nothing; the half-life editor
  beside it works.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
  - frontend
dependencies: []
priority: p2
type: bug
ordinal: 505900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — P2. Corrects a Done claim in this file.** **Editing a signal *weight* in Settings changes nothing; the half-life editor beside it works.** `insight/service.py:92` reads `CONTRIBUTION_WEIGHTS[event.event_type]` — the module-level dict at `insight/signals.py:22-29` — instead of `get_signal_weights(db)`. Full trace: the form persists under `SIGNAL_WEIGHTS` (`frontend/router.py:220`); `settings/service.py:59-62` merges the override over code defaults; but `get_signal_weights` has exactly two consumers repo-wide — re-displaying the form (`frontend/router.py:81`) and the `if base_weight is None` fallback inside `record_contribution` (`signals.py:76-82`) — and **both callers of `record_contribution` pass `base_weight` explicitly** (`insight/service.py:158`, `recipients/service.py:267`), so that fallback has no in-app caller and the stored weight override reaches nothing. Half-lives are unaffected because they apply **on read** via `_configured_half_lives`. **Fix: +3 loc** — a lazy `from app.settings.service import get_signal_weights` mirroring the existing pattern at `signals.py:57`, reading the merged dict at `:92` with `.get(type)` plus the existing `raise ValueError` shape (the webhook caller at `providers/service.py:183-185` already handles it). **Ship the copy fix in the same commit:** `templates/settings.html:59-60` promises *"Changes apply immediately to computed signals"* for both editors, and that stays half-false even after the fix — weights are frozen into `base_weight` at write time, so a weight change affects only *future* contributions while a half-life change retroactively re-scores the whole log. **That asymmetry is inherent to ADR-132** (§1 makes the decay constant changeable without losing history and says nothing of the sort about the weight) — not a defect, but the Settings copy must stop implying symmetry. **This contradicts the Done entry below** (Config/settings layer, 2026-07-15), whose verification exercised only the half-life half; a correction note is appended there. No test covers `apply_event_to_signals`; `tests/test_signals.py:131-141` covers only the half-life override. Source: code-slimmer sweep 2026-08-21, Cluster 4 C1. **DONE 2026-09-13** in `b0efbf7`. `insight/service.py:97-99` now takes a lazy `from app.settings.service import get_signal_weights` and reads the merged dict with `.get(event.event_type)`, so a stored weight override finally reaches `record_contribution`. The copy fix shipped with it: `templates/settings.html:65` now spells out that a **weight** change affects only *future* contributions while a half-life change re-scores the whole log on read — the asymmetry ADR-132 makes inherent. Delegated to the `bug-fixer` agent, which is what the entry's exhaustive trace made possible.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 621, section "Done", position 59 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
