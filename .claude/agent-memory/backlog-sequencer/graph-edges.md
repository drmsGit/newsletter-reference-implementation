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

---

# Run 2 — 2026-09-27, after the Manager Workflow and Variant Editor interviews

**Gap numbering used below.** `MW-n` = Manager Workflow interview gap n (1-18,
in its "What Cluster N produced" sections). `VE-n` = Variant Editor gap n (1-30,
same location). **VE has 28 distinct gaps, not 30**: 15 and 20 are the same gap,
16 and 28 are the same gap. Both pairs say "also gap N" in the source.

## Where the new work is recorded (important — it is NOT all in the backlog)

- The **18 MW gaps** are in `docs/backlog.md` **line 90**, compressed into one
  narrative 📋 `[Needs design]` entry. They exist but are not individually
  rankable and do not compete as 🔴 items.
- **8 of the 28 VE gaps** are logged as their own Features/Bugs: VE-1 (L356),
  VE-2 (L362), VE-4+5 (L358), VE-7+8 (L360), VE-9 (L364), VE-16/28 (L390),
  VE-18 (L392), VE-21 (L394). *(The brief for run 2 said six; it is eight.)*
- **The other 20 VE gaps exist only in the interview's cluster tables.**

## New root nodes

- **C2 — the settings surface.** Verified 2026-09-27: `app/settings/` and
  `app/ai/` contain no `router.py`. Nothing upstream of it.
  Downstream: ADR-175 facet administration (an **accepted** ADR that cannot be
  implemented), the asset filename template, per-task model selection, the
  signal-weight grid, spend cap, half-life. Predates both interviews.
- **C8 — planning a send.** `prepare_send_from_audience` has exactly one call
  site and it is the Jinja route. Downstream: the whole send half of the SPA.
  Sibling read gap: send instances reachable only via
  `GET /delivery/snapshots/{id}/send-instances`, no get-by-id.
- **The content-catalogue field model ADR** (VE 1.8, 2.4, 2.8, 2.9, 2.10).
  Unwritten. The widest fan of anything in the repo — see batch M1.

## The M1 chain (content-catalogue field model)

`field-model ADR -> storage/fields.json -> ` VE-3, VE-10, VE-11, VE-13, VE-14,
VE-2 (hero migration), VE-9's `type` descriptor, Feature L176 (content-record
form half hand-written), MW Cluster 2's CONTENT_FIELD_GROUPS maintenance item,
and the client's flat content-field list (already marked ❌).

Evidence: `CONTENT_FIELD_GROUPS` verified at `content/service.py:101`; its
docstring says the manifests are "where it belongs". Duplicate at
`scripts/import_content_csv.py:33-41`. `storage/fields.json` does not exist
(`storage/` holds only `channels`, `modules`, `snapshots`).
**`ContentRecordDB.content` is an unvalidated JSON column**, so no column
migration is needed for values — the only destructive step is VE-2's direction
(existing hero `module_data` must become content records, inventing a title and
brand for each). A wrong key name orphans content silently and nothing catches it.

## Override-integrity chain

- **VE-15/20 (refuse an override on a slot-bound module) -> VE-4/5 (`max_results`).**
  Hard edge, and the direction is counter-intuitive: the *refusal* must land
  before or with the feature. The interview's own reason — "once `max_results`
  works it produces three personalised picks wearing one pinned headline."
  This is a constraint before the feature that makes its race routine.
- **VE-16/28 -> `campaigns/duplication.py`.** Verified: the docstring at
  :143-152 (backlog says :147 — drift) groups content overrides with snapshots
  and send instances as "a record of something that happened". 3.6 reverses it:
  the line belongs *inside* the row (`field_overrides`, `system_content_record_id`,
  `reason` copy; `outcome_delta`, `send_instance_id`, `reverted_at` do not).
- **VE-18 (`outcome_delta`) has no producer AND no experimental design.** A delta
  needs a baseline that was never sent. Needs a holdout, counterfactual or A/B —
  none exists or is specified. This is upstream of the A/B-test Feature, which
  cost-of-delay already has in Decays. Do not treat VE-18 as a code gap.

## Concurrency / audit chain

- **VE-7/8 (advisory lock, L360) -> L142 (`audit_events` three unproven properties).**
  L360 makes the lock "the first real consumer of `audit_events`", and L142's
  three properties are unproven *because nothing reads it back*. Cheaper first
  consumer than the operator screen L142 anticipates: one subject, one lookup,
  no brand filtering — which matters because L142's point (3) is that brand
  filtering *cannot* be a plain `WHERE brand_id = ?` (sign-in and deactivation
  rows carry NULL forever).
- **No schema change needed for optimistic concurrency.** Verified: `updated_at`
  with `onupdate=func.now()` exists on both `VariantDB` (`campaigns/db_models.py:64`)
  and `ModuleInstanceDB` (:83). It is a comparison on write and a 409.
- **VE-22 (version marker on `module_instances`) is NOT the same as VE-7.**
  Interview 4.3b decided the version column is a **marker, not a render pin**.
  Do not collapse them.

## List-route chain (the one that changed status)

- **MW-5 (server-side filtering + pagination on every list route) reprices the
  existing pagination Feature (L242) from a latent scaling note to a blocker**,
  and **invalidates the four built Phase 2 screens** — verified: `frontend/src/screens/`
  contains exactly Content, Campaigns, Audiences, Approvals as list screens.
  Downstream: MW-7 (approvals filters), MW-10 (`GET /campaigns/decision-slots/{id}/resolutions`
  unpaginated on a table measured at 96,040 rows), MW-18 (campaign state view).
  L242 does not record any of this.

## Asset chain

- **Asset subsystem (L364) <-> Needs-ADR "snapshot storage strategy".** The
  backlog entry says "Answer both together" — `SnapshotDB` already carries
  `artifact_storage_type` / `artifact_location` / `artifact_size`, and
  `snapshots/service.py:106` names the open storage question. Assets need
  exactly the medium that ADR-162 §3 left open. One seam, ADR-101 pattern.
- **Asset filename template -> C2.** The design chose "configured at
  implementation" *because* there is no settings router. C2 is therefore a
  soft edge here, not a blocker.
- **Asset deletion -> new Needs-ADR "nothing is ever hard-deleted" (L398)
  -> general data-lifecycle Needs-ADR.** L398's own text says to sequence them
  together: "retention and 'never delete' are the same question from opposite ends."
- **Assets add the platform's only anonymous unauthenticated serving route and
  its only file upload.** Verified: zero `UploadFile` anywhere in `backend/app/`.

## Client-boundary edge nobody has drawn

**L138 (move backend rules out of `frontend/router.py`) is a precondition the
build already walked past.** Its own title says "the precondition for the React
build"; two client phases shipped anyway. `docs/react-migration-inventory.md`:
83 routes = 33 presentation, 27 logic-only, **26 capabilities with no JSON route**.
The three that carry a *rule* rather than a convenience:
the brand boundary on reads exists only there (15 call sites; `get_content_record`
at `content/service.py:44` takes no `brand_id` at all); `channel_available` has
exactly two call sites, both in that file; `_may_decide` is the real per-row
approval gate. File measured 4,415 loc 2026-09-27 (backlog says 4,419 — drift).

## Cycles
Still none between items.
