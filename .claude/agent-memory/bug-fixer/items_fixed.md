# Backlog items already implemented

Entries here are done in a worktree branch. If the 🔴 entry is still in
`## Bugs`, that is the un-pruned section, not a second occurrence of the bug —
verify against code before re-implementing.

## Settings signal-weight editor inert (P2, "Corrects a Done claim in this file")

- **Run:** 2026-09-13. First ever bug-fixer run. Outcome: `fixed`.
- **Branch:** `worktree-agent-afd52ccdfdbe71252`. Not committed; left dirty for human review.
- **Entry text verified accurate** against the tree — every cited symbol existed
  and the defect was live. Only drift: the entry cites `recipients/service.py:267`
  for the second `record_contribution` caller; it is actually **:437**. Line
  numbers in this file are hints, confirmed.
- **Fix:** `app/insight/service.py` — `apply_event_to_signals` read the
  module-level `CONTRIBUTION_WEIGHTS` dict at `:92`; now lazily imports
  `get_signal_weights(db)` (mirroring `signals._configured_half_lives` at
  `signals.py:57`) and reads with `.get()` + `raise ValueError`. Dropped
  `CONTRIBUTION_WEIGHTS` from the module-level import, which my change made dead.
- **Shipped in the same change** (the entry required it): `app/templates/settings.html`
  help text no longer claims "Changes apply immediately to computed signals" for
  both editors. Weights are frozen into `base_weight` at write time, so a weight
  change affects only future contributions; a half-life change re-scores the
  whole log on read. **That asymmetry is inherent to ADR-132 §1, not a defect** —
  do not "fix" it later.
- **Test:** `tests/test_signals.py::TestConfigAffectsSignals::test_weight_override_reaches_apply_event_to_signals`.
- The Done-archive entry (Config/settings layer, 2026-07-15) **already carries its
  correction note** ("⚠️ Correction 2026-08-21"). Nothing to append there — and
  `docs/backlog.md` is off limits anyway.
