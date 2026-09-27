---
id: TASK-189
title: 'A recipient can be mailed after opting out, when the audience was frozen.'
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
priority: p0
type: bug
ordinal: 505300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — P0, compliance.** **A recipient can be mailed after opting out, when the audience was frozen.** `prepare_send_from_audience()` consent-gates at *plan* time and materialises `DeliveryExecutionDB` rows; in `freeze` mode those rows never change. `send_send_instance()` then never re-checks `RecipientDB.consent_status` before calling the provider (`delivery/service.py:296-433`). **Opt in Monday → send prepared Tuesday → recipient opts out Wednesday → send fires Thursday → they get the email.** The decision layer *does* hold a consent guard, but its `ValueError` is caught by a bare `except ValueError: pass` at `delivery/service.py:383-387` whose own comment reads "or a guard tripped" — so the guard fires and the send continues anyway. **Fix:** an unconditional suppression/consent check immediately before `provider.send()`, independent of resolution mode. Freezing an audience may freeze *targeting*; it must never freeze *permission to contact*. **Fix the root cause with it (was P3-03):** replace the blanket `except ValueError` with typed domain exceptions — `NoDecisionResult`, `ConsentDenied`, `InvalidStrategyConfig` — and suppress only the intentional "no eligible candidate" case. The broad catch is what let a compliance defect hide as a rendering behaviour. Source: code review 2026-08-07 P0-02 + P3-03. **DONE 2026-09-13.** Fixed in the shape [[ADR-163 — Per-Channel Consent and Addressability]] §7/§8 prescribes, not as this entry originally described — the entry predates the ADR and its prescribed fix (re-read `RecipientDB.consent_status` before `provider.send()`) had gone stale, since that column no longer exists. `app/delivery/exclusion.py` now runs an ordered stack (addressability → consent → suppression → frequency) immediately before the send loop **for every resolution mode including freeze**, as set operations (§10), recording *why* each recipient was excluded on `DeliveryExecutionDB.exclusion_reason` with status `excluded` (§8). Stage 3 is named but empty by construction: a bounce is written as a consent event with `source='provider'` so stage 2 catches it, and the suppression data model is still an open Needs-ADR item. Stage 4 (frequency) is post-POC per ADR-161 §8. The root cause is fixed as the entry asked: `ConsentDenied` is re-raised rather than swallowed, and the bare `except ValueError` survives only for the intentional no-candidate case (ADR-086). Closes **launch gate 2**. Three regression tests including send-time consent revocation — the top-ranked missing test from the 2026-08-07 review — all mutation-verified.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 609, section "Done", position 53 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
