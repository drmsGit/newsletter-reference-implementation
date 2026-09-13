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

## Webhook signature verification fails open when the secret is absent (P1 security, `docs/backlog.md` line 35)

- **Run:** 2026-09-13 (run 3). Outcome: `fixed`.
- **Branch:** `worktree-agent-a2c2f99fad20b688e`. Left dirty, not committed.
- **Entry was NOT stale.** `providers/adapters/resend.py:65-72` landed exactly —
  second entry in this file whose line numbers still hold (the other is the
  enumeration-oracle one). Both were written by the 2026-08-07 code review;
  that review's line numbers appear to be reliable, unlike older entries.
- **Fix:** `verify_signature()` now returns `False` (+ `logger.error`) when
  `RESEND_WEBHOOK_SECRET` is unset. Two-line behaviour change; the rest of the
  function was already correct (constant-time compare, header presence check).
- **I deliberately added NO dev-bypass flag.** The entry's directive is "fail
  closed"; the "a development bypass must be a deliberate flag" clause
  constrains any bypass, it does not mandate building one. Adding none is the
  strictly conservative reading and needs no naming decision. **If a future run
  is asked to add the flag, that IS a decision** (name, truthy parsing, scope,
  whether it is per-provider) — refuse it unless the human names the flag.
  Precedent if they do: `AUTH_DEV_SHOW_CODE` (`app/auth/service.py:241`) parses
  `{"1","true","yes"}` after strip+lower.
- **The documented local workflow does NOT depend on the fail-open.**
  `docs/how-to-webhooks-engagement.md` step 2 has you copy a real signing secret
  from the Resend dashboard before step 3 sets it. Checked this before changing
  behaviour — that check is what made the flag unnecessary.
- **Doc updates shipped with it** (three files stated the old behaviour verbatim
  and would have misled an operator into an unexplained 401):
  `docs/how-to-webhooks-engagement.md:66`, `docs/architecture/Code/providers.md:59`,
  `docs/architecture/Code/Flow - Engagement to signal.md:55` and `:77`.
  Rule of thumb: prose that *describes the line you changed* is part of the one
  item; anything else is a drive-by.
- **Test:** `backend/tests/test_provider_webhook_signature.py`, 4 cases, no DB
  and no network — pure `monkeypatch` over `os.environ`. Includes a
  correctly-signed positive case so "always return False" cannot pass.
- **Suite:** 161 pass (157 baseline + 4). No DB rows created.
