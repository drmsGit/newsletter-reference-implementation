---
name: graph-edges
description: Dependency edges between backlog items, built 2026-09-12 after the omni-channel interview closed. Each edge names its evidence.
metadata:
  type: project
---

Notation: `A -> B` means A blocks or reshapes B. "shapes" = B can be built without A
but gets rebuilt if A lands later.

## Root nodes (nothing upstream of them)

- **Gate 3 — inbound machine authentication (API keys + scopes)**. No upstream at all.
  Downstream: `POST /provider/events` closure (same item); the React SPA track
  (BETA-SCOPE §5: "can't start for real until Gate 3 is built"); Mode B; every JSON
  router added meanwhile.
- **Gate 4b — sign-in code disclosure (P0)**. No upstream.
  `4b -> P1 login-form enumeration oracle` is a hard edge and the backlog states the
  cost: the enumeration fix is **0 loc once 4b is fixed as described**, because both
  come from the same `if code:` branch conflating "dev" with "not delivered".
- **Gate 1 — positioning statement**. No code upstream, but see staleness-watchlist:
  ADR-165 changed what the statement is allowed to claim.
- **`app/database.py` import-time engine + hard-coded password** (3 lines, both defects
  in the same 6-line file). Downstream: clean-container `pytest` (beta DoD #4), the four
  uncollectable test modules, the isolated-test-DB Needs-ADR item.

## The omni-channel chain (ADRs accepted 2026-09-12, nothing built)

- **ADR-163 §7/§8 -> P0 consent defect (Gate 2)**. ADR-163 §8 says so in terms: "This is
  the shape the P0 fix should be built in, which was the reason for settling this cluster
  before fixing it." The ADR is now available, so this edge is *satisfiable today* — it
  is no longer a wait.
- **ADR-163 §1 -> every `RecipientDB.consent_status` reader**. Verified footprint:
  `app/recipients/{models,service,db_models,router}.py`, `app/decision/service.py`,
  `app/audience/service.py`, `app/templates/{recipients,recipient_detail}.html`,
  `scripts/seed_demo_data.py`, `scripts/reset_all_data.sql`. Ten files.
- **ADR-163 §7 stage 3 -> Needs-ADR "suppression + opt-out reason model"**. The P0 fix,
  built as the ordered stack, creates the seam suppression plugs into. Suppression is
  NOT upstream of the P0 fix.
- **ADR-163 §5 -> `detect_consent_drift`** (one status today, becomes per `(channel, purpose)`).
- **ADR-162 §1 -> Done item "Add subject/preheader to CampaignDB/VariantDB"** — reverses it.
  Downstream: `app/ai/tasks/subject_preheader.py`, `app/campaigns/{db_models,models,service}.py`,
  `app/rendering/service.py`, `app/frontend/router.py`, `app/templates/campaign_detail.html`.
- **ADR-162 §1 -> Needs-ADR "Mode-A subject/preheader vs decision-slot content"** and
  -> Feature "recall past AI suggestions". Both currently assume variant columns.
- **ADR-162 §3 -> Needs-ADR "snapshot storage strategy"**: the (1) approval snapshot /
  (2) immutable per-delivery package split the item asked for is now DECIDED, plus a
  package hash. What remains open is the medium only.
- **ADR-162 §3 -> P2 snapshot atomicity bug**: the fix target (`html_location="pending"`)
  is renamed to `artifact_*` by the same change; fixing atomicity first means touching
  `app/snapshots/service.py:105-138` twice.
- **ADR-164 §9 -> `SignalContributionDB`** gains a `channel` column.
- **ADR-164 §10 -> P2 signal-weight editor no-op**. ADR-164 extends the same settings
  weight grid with channel weights. The grid's writes currently reach nothing
  (`insight/service.py:92` reads the module-level `CONTRIBUTION_WEIGHTS`). Extending a
  grid whose writes are inert multiplies the defect. Fix is +3 loc.
- **ADR-161 §3 -> `DeliveryExecutionDB`** (a delegated send records a TRANSFER, not a delivery).
- **ADR-165 -> Gate 1 positioning**: supersedes ADR-001, scope is now formally
  channel-neutral orchestration. Changes the rule-2 test, does not close the gate.

## Delivery-path cluster

- **P0 consent fix and P1 send-status fix are the same function**, `send_send_instance()`
  in `app/delivery/service.py:296-433` (file is 433 loc total). The P1 fix lands on line
  433; the P0 gate goes immediately before `provider.send()`. One context load.
- **P0 root-cause (typed exceptions replacing the bare `except ValueError` at :383-387)
  -> ADR-163 §8's recorded exclusion reasons**. Same edit.
- **Needs-ADR "bulk send batching" -> P1 send-status** (partial): deriving parent status
  from children is also what a batched sender needs; the N+1 shape (code review P2-04)
  is in the same loop. ADR-163 §10 pre-commits the answer to set operations, not loops.

## Verification chain (upstream of confidence in every fix above)

- **`app/database.py` engine-at-import -> the four uncollectable test modules**
  (`test_ai_subject_task`, `test_auth`, `test_overrides`, `test_signals`)
  **-> the six missing tests the 2026-08-07 review ranked**, whose #1 is send-time
  consent revocation — i.e. the regression test for the P0.
- **-> beta definition-of-done #4** ("clean-container `pip install -r requirements.txt
  && pytest` succeeds"). See staleness-watchlist: DoD #4 cannot pass today.

## Frontend chain (scope-dependent, BETA-SCOPE §5)

- `Gate 3 -> React SPA`. `ADR-162 (variant/module shape) -> campaign+variant screens`.
  `ADR-163 (addressability) -> recipient/audience screens`. `Pagination envelope Feature
  -> typed API client` (the client is generated off the OpenAPI schema, so an
  un-enveloped list endpoint is generated wrong once per endpoint).

## Cycles
None found. The one circular dependency in the repo — "suggest audience" reading
resolutions that resolution needs an audience for (Needs-ADR, dynamic decision content ×
audience) — is internal to one item, not a cycle between items, and the running system
masks it.
