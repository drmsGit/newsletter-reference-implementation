---
id: TASK-283
title: >-
  Readiness state: a mark per record and channel, machine ready, the migration
  and the routes
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-05 18:10'
updated_date: '2026-10-05 18:13'
labels:
  - backend
dependencies: []
type: feature
ordinal: 200110
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-282 design session (2026-10-05, the user, one question at a time). Recorded in the 2026-10-05 addenda to [[ADR-174 — Channel Readiness Is Asserted, Not Computed]] and [[ADR-179 — What Enters the Catalogue, and What a Machine May Take From It]], and in [[Channel Readiness - final design pass]]. This is the server half: the state, the migration and the routes. Everything else in the readiness work builds on it.

**What exists:** nothing. `ContentRecordDB` (`backend/app/content/db_models.py:6-26`) has no readiness or machine-ready column, and nothing in `backend/app` names either.

**Storage (ADR-174 addendum, point 1).** A table holding one row per (content record, channel) that is marked ready, with who marked it (`actor_label`, as `ContentVersionDB.created_by` does; never from a request body) and when. Unmark deletes the row; the audit log keeps the history. A new channel costs no migration.

**Machine ready (ADR-179 addendum).** A boolean on `content_records`. A new record starts false.

**The migration** (the next number: run `ls backend/scripts/migrate_*` and take the next one). It creates the table and the column, sets machine ready true on every existing record, and marks every **active** existing record ready for **email**, because that is what slots pick today and nothing should go empty. It never marks push. Apply it with `scripts/migrate.py --apply` before any Python edit while the preview backend reloads (memory: the queue-task method).

**Routes:**
- **Mark and unmark a channel** for a record, brand-scoped.
  - A person marks directly.
  - An integration's **unmark** is allowed directly.
  - An integration's **mark** is refused (403) until task-206 adds the approval hold, so nothing goes through unheld. The guard today only ever holds sends (`backend/app/auth/dependencies.py`, around 623-638), which task-206 must address.
- **Set machine ready** on or off: people only, and an integration is refused.
- **Every change is audited.**
- **The record detail** carries per-channel readiness (who, when) plus the warning per marked channel, and machine ready.
  - **The warning is computed on the server,** so the client is given the answer rather than working it out (ADR-177). It fires when the record can fill **no** module of that channel, and says what each kind of module needs. Required fields come from the manifests' `(module, field)` declarations.
- **`GET /content/`** gains a `ready_for` filter, which applies to items and total alike, and per-row `ready_for` (the channels the record is ready for).
- **Validation.** A channel name is checked against the registered channels (`storage/channels/`).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A record can be marked and unmarked ready per channel, recording who and when; a person marks directly, an integration may unmark but its mark is refused until task-206
- [ ] #2 Machine ready can be set on or off by a person only; new records start off; the migration sets existing records on and marks active ones ready for email
- [ ] #3 The record detail carries readiness, its warnings (the record fills no module of the channel) and machine ready; GET /content/ filters and reports ready_for
- [ ] #4 Every change is audited and every route brand-scoped, with tests
<!-- AC:END -->
