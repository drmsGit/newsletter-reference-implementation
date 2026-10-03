---
id: TASK-110
title: >-
  A variant has no optimistic concurrency and no record of who last touched it,
  so two editors silently destroy each other's work.
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 13:57'
updated_date: '2026-10-03 18:01'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 200050
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — a fence for agents, not a courtesy between colleagues. Raised by the user 2026-09-25.** **A variant has no optimistic concurrency and no record of who last touched it, so two editors silently destroy each other's work.** There is no lock, no version column and no conflict detection on `variants` or `module_instances`; the second write wins and the first person is never told. **The version token already exists** — both tables carry `updated_at` with `onupdate=func.now()` — so this is a comparison on write and a 409, not a schema change. **The argument that decides it is about machines**: [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] already makes an agent a first-class caller, and the user expects *"proper ai agents that 'work' parallel in the system […] they need some sort of fence to not start working on something that is edited in that same moment"*. An agent rewriting a variant mid-edit produces the same silent loss, faster and more often. **The design has two layers and an asymmetry:** an *advisory* lock — "blocked by X, last updated HH:MM, unblock" — that **anyone may clear themselves** (a social signal, deliberately not a real lock, so nothing is ever held by someone on holiday), plus optimistic concurrency underneath to catch the case where both click through. **The same lock is advisory for a person and binding for a machine**, because a human clearing a fence exercises judgement an agent does not have. That asymmetry is a new rule about what machine principals may do and **likely owes an ADR**. **Two things it needs that do not exist:** neither table has an `updated_by` (the only actor column nearby is `ContentVersionDB.created_by`), so *"last updated by X"* must be read from `audit_events`; and `actor_id` is an id rather than a name, so initials or *"blocked by Jana"* needs a join the audit layer deliberately avoids per [[ADR-153 — Audit and Accountability]]. **This makes it the first real consumer of `audit_events`** — see the entry above on that table's three unproven properties, all of which are unproven *because nothing reads it back*. It is a cheaper first consumer than the operator screen that entry anticipates: one subject, one lookup, no brand filtering. Presence bubbles and a slim per-campaign history were asked for and explicitly deferred by the user — *"not necessary from the beginning"*.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Scope (user, 2026-10-03): conflict detection only; ADR-180's advisory lock is split into its own task, built with the editor screen that shows it. Token optional (user): a write carrying it is checked, one without behaves as before; the React editor always sends it, the Jinja forms and integrations are unchanged.
1. Mechanism (ADR-180 point 2): the client sends the updated_at it read as an If-Match header; a mismatch answers 409. Header rather than body so PUT, PATCH, DELETE and the body-less move work alike.
2. backend/app/campaigns/service.py: StaleWrite (not a ValueError, so no route turns it into a 400) and one check that re-reads the row FOR UPDATE and compares; update_variant, update_module, delete_module, move_module and update_decision_slot take expected_updated_at. update_variant bumps the variant's updated_at itself, because a subject-only edit changes the header module, not the variant row, and would otherwise leave the token unchanged.
3. backend/app/campaigns/router.py: If-Match on the six routes (variant PUT, module PUT/DELETE/move, slot PUT/PATCH); unparseable -> 400, stale -> 409.
4. Tokens readable where the editor reads: updated_at added to ComposedModule and DecisionSlotListed (the variant already has it).
5. Tests in backend/tests/test_stale_writes.py, mutation-checked; regenerate client types.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 370, section "Features", position 63 in that section (top = do next). The description is the original entry, verbatim.

2026-09-27: [[ADR-180 — A Lock Is Advisory for a Person and Binding for a Machine]] now records the lock policy this task implements.

Ranked 2026-10-03 to the front of the features: slice 4 of [[Campaign Write Surface - final design pass]]. The user chose autosave on blur for the variant editor (D1), which makes this a precondition of the editor screens rather than a follow-up: with autosave a stale save is a normal event.

2026-10-03. Built layer 1 (optimistic concurrency); the advisory lock and 'last updated by' moved to task-254 (user's split). Reproduced first: all 8 new tests in backend/tests/test_stale_writes.py failed. Mutants: check as no-op (7 fail), variant token not moved on a subject-only edit (2), move/delete/PATCH routes not passing the token (1 each). Not covered by a test: the FOR UPDATE re-read in _refuse_stale, which closes the race between two writers passing the check together; it needs two concurrent transactions to prove. Full suite 1168 passed, rc 0; client types regenerated (If-Match header on six routes, updated_at on ComposedModule and DecisionSlotListed), tsc clean, 75 client tests.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Variant, module and slot writes accept If-Match with the updated_at the caller read; a stale one answers 409 and changes nothing, a write without it behaves as before (the Jinja forms and integrations are unchanged). The composition now carries every token the editor needs, and a subject-only edit moves the variant's token. Verified by 8 tests reproduced as failures first and five mutants caught; 1168 backend tests. The advisory lock is task-254.
<!-- SECTION:FINAL_SUMMARY:END -->
