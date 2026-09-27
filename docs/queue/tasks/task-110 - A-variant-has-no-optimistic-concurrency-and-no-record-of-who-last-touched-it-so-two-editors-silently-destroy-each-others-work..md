---
id: TASK-110
title: >-
  A variant has no optimistic concurrency and no record of who last touched it,
  so two editors silently destroy each other's work.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-09-27 14:20'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 206300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — a fence for agents, not a courtesy between colleagues. Raised by the user 2026-09-25.** **A variant has no optimistic concurrency and no record of who last touched it, so two editors silently destroy each other's work.** There is no lock, no version column and no conflict detection on `variants` or `module_instances`; the second write wins and the first person is never told. **The version token already exists** — both tables carry `updated_at` with `onupdate=func.now()` — so this is a comparison on write and a 409, not a schema change. **The argument that decides it is about machines**: [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] already makes an agent a first-class caller, and the user expects *"proper ai agents that 'work' parallel in the system […] they need some sort of fence to not start working on something that is edited in that same moment"*. An agent rewriting a variant mid-edit produces the same silent loss, faster and more often. **The design has two layers and an asymmetry:** an *advisory* lock — "blocked by X, last updated HH:MM, unblock" — that **anyone may clear themselves** (a social signal, deliberately not a real lock, so nothing is ever held by someone on holiday), plus optimistic concurrency underneath to catch the case where both click through. **The same lock is advisory for a person and binding for a machine**, because a human clearing a fence exercises judgement an agent does not have. That asymmetry is a new rule about what machine principals may do and **likely owes an ADR**. **Two things it needs that do not exist:** neither table has an `updated_by` (the only actor column nearby is `ContentVersionDB.created_by`), so *"last updated by X"* must be read from `audit_events`; and `actor_id` is an id rather than a name, so initials or *"blocked by Jana"* needs a join the audit layer deliberately avoids per [[ADR-153 — Audit and Accountability]]. **This makes it the first real consumer of `audit_events`** — see the entry above on that table's three unproven properties, all of which are unproven *because nothing reads it back*. It is a cheaper first consumer than the operator screen that entry anticipates: one subject, one lookup, no brand filtering. Presence bubbles and a slim per-campaign history were asked for and explicitly deferred by the user — *"not necessary from the beginning"*.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 370, section "Features", position 63 in that section (top = do next). The description is the original entry, verbatim.

2026-09-27: [[ADR-180 — A Lock Is Advisory for a Person and Binding for a Machine]] now records the lock policy this task implements.
<!-- SECTION:NOTES:END -->
