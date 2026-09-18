---
type: code-module
module: audit
topic:
  - architecture
  - audit
created: 2026-09-18
modified: 2026-09-18
---

# audit

> Part of [[MOC - System Overview]]. Architecture rationale: [[ADR-153 — Audit and Accountability]].

## Purpose

The audit module owns **the append-only accountability log: one table answering
who acted, on what, in which brand, and when** — deliberately separate from the
domain history the product needs in order to function. It exists to make three
things possible that do not fall out of domain logs however complete they are: a
"what has this operator done" screen, a SIEM export, and a single place to point
a reviewer or DPO. It is the **first slice** of ADR-153 — sign-in, role
grants/revocations, user deactivation, brand creation, duplication — and it says
so: exports/bulk reads (point 4) and aggregated authentication failures (point 6)
are named as out of scope rather than silently assumed.

## Key files
- `backend/app/audit/service.py` (136) — the action vocabulary, `record`, `record_from_request`, two read helpers
- `backend/app/audit/db_models.py` (79) — `AuditEventDB`; mostly docstring, explaining the no-FK choice
- `backend/scripts/migrate_0009_audit_log.sql` (91) — the Postgres path, with a verification query that asserts **zero foreign keys**

## Public surface
**Service** (`audit/service.py`):
- `record(db, action, *, actor_type, actor_id, subject_type, subject_id, brand_id, detail, commit=True)` — `service.py:46`. Appends one entry; **never raises**; returns `None` on failure.
- `record_from_request(request, db, action, **kwargs)` — `service.py:94`. Same, pulling actor and brand off `request.state`.
- `events_for_subject(db, subject_type, subject_id, limit=50)` — `service.py:107`
- `events_by_actor(db, actor_id, actor_type, limit=50)` — `service.py:123`

**Actions** (`service.py:28-38`): `user.signed_in`, role granted/revoked, user deactivated/reactivated, `brand.created`, `campaign.duplicated`, `content.duplicated`. **Actor types** (`:41-43`): `user`, and `integration` — declared for [[auth]]'s machine principals, nothing writes it yet.

**Routes:** *none.* `backend/main.py:139-140` imports the model purely for metadata registration, and says so in a comment.

## Data model
*One table.*
- **`audit_events`** (`AuditEventDB`, `db_models.py:6`) — `actor_type`, `actor_id`, `action`, `subject_type`, `subject_id`, `brand_id`, `detail` (JSON), `created_at`. Two composite indexes: `(actor_type, actor_id, created_at)` and `(subject_type, subject_id, created_at)`.
- **Zero foreign keys, deliberately** — the migration asserts it (`migrate_0009_audit_log.sql:81-87`). There is no `updated_at`, no `status`, and no mutable field of any kind.

## Depends on →
- Nothing but `app.database.Base`. It does **not** import [[auth]], brands, or any domain module — actor and brand arrive as plain ints, and `record_from_request` takes `request` untyped to avoid even a FastAPI import.

## Depended on by →
- [[auth]] — 5 write sites in `auth/router.py` (sign-in, deactivate, grant, revoke, brand created)
- [[frontend]] — 2 write sites (`router.py:1383` campaign duplicated, `:2158` content duplicated)

## Invariants & decisions
- **Append-only is enforced by convention and absence, not by the database.** There is no trigger, no `REVOKE UPDATE`, no immutability check. What enforces it is that the table has **no field that would invite an update** — no status, no `updated_at` — and the service exposes only `record`; there is no `update_event` or `delete_event` anywhere. `db_models.py:24-26`: "An audit entry that can be edited is not evidence." **Treat this as discipline, not a guarantee.**
- **No foreign keys, deliberately** (`db_models.py:16-22`). An accountability entry must outlive what it references. A FK would either block a recipient erasure or cascade it, and both destroy the record. Actor and subject are type+id, resolved on read and **allowed to dangle**.
- **Fail-open on write, loudly** (`service.py:58-91`). `record` swallows every exception, logs at error, rolls back, returns `None`. The reasoning: a failure that rolls back a role grant because its log entry would not write is worse than an incomplete log — and it is the failure mode that gets audit logging switched off in production.
- **`commit=True` by default, `flush()` as the alternative** (`service.py:80-83`), so an audit write can join a caller's transaction when the caller wants atomicity.
- **A null actor is recorded honestly rather than attributed** — with access control off, nobody is signed in.
- **Written from routes, never from services** (`service.py:3-9`). The route knows who is acting; a service takes a session, not a request. Threading an actor through every write signature was considered and rejected — while `brand_id` *was* threaded that way, because a brand is a property of the data and an actor is a property of the request.
- **The cost of that is stated, not discovered** (`service.py:11-15`): a service called from anywhere but a route is not audited. Scripts, scheduled jobs and machine callers all bypass it. Named as the first thing to revisit.
- **Failed sign-ins are deliberately NOT logged** (`auth/router.py:142-146`) — ADR-153 point 6 makes them an aggregate, because a row per failed attempt is a write-amplification target an unauthenticated attacker controls. [[auth]] holds that aggregate instead.
- **The log replaces a `copied_from_id` column, deliberately** (`service.py:34-37`): "where did this come from?" is answered from events so the answer cannot go stale when the source is renamed, re-pointed or deleted — the same reasoning as ADR-163 computing consent from events rather than storing a status.
- **`brand.created` records the brand it created**, not the brand the actor was in, or every brand creation would read as an event in brand 1. **`campaign.duplicated` belongs to the target brand**, with the source in `detail`, so the log reads correctly from either end.
- **Role revocation captures the grant's detail before revoking** (`auth/router.py:340-350`) — otherwise the row it describes is already gone.
- **Reads tie-break on `id DESC` after `created_at DESC`** — several events can land in the same instant.
- **Nothing is backfilled, and the migration says why** (`migrate_0009_audit_log.sql:88-90`): inventing entries for actions nobody recorded would fabricate exactly the evidence the table exists to hold.

## ⚠️ Change-impact — if you touch this, also check…
- **Append-only stops holding the moment anyone adds a mutable column or a helper that writes an existing row.** Nothing in the DB or the test suite will catch it. This is the module's most fragile invariant.
- **The swallow-everything `except` at `service.py:85` hides schema drift.** Add a column without running the migration on Postgres and every audit write fails silently into a log line — the app keeps working, the log just stops filling.
- **`record(..., commit=False)` plus a failure rolls back the caller's transaction** (`service.py:88`) — `record` cannot distinguish its own work from the caller's.
- **New write sites must go in routes.** An `audit.record` in a service means either threading a request into the domain layer or logging an action with no actor.
- **`action` is a plain VARCHAR** — adding one is a constant, no migration. Correspondingly **typos are invisible**: nothing validates that a written action is one of the constants.
- **`detail` is unvalidated JSON** with a policy nothing enforces (internal identifiers only, never contact details — `db_models.py:64-68`). A call site passing a recipient's email would be an ADR-153/ADR-154 violation no test catches.
- **No retention or pruning exists**, in tension with [[ADR-154 — Erasure and Retention]]: the table grows without bound, with five indexes on a write-mostly table.
- **Nothing reads it back in production yet.** Both read helpers are exercised only by tests; there is no route, no template, no export. ADR-153 point 1's operator screen is *enabled* but not built — the write side landed first, deliberately.
- **Brand filtering is a read-side change only** (`brand_id` is already captured), but sign-in and deactivation rows are `NULL` forever, so a brand filter cannot be a plain `WHERE brand_id = ?` without dropping those events.
- **`record_from_request` reads `request.state` via `getattr` with a `None` default** — a middleware rename turns every entry's actor into `NULL` silently rather than raising.
