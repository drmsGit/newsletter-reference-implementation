# Code review brief — Tarrow

**Prepared 2026-10-09** (replacing the brief of 2026-09-19). Read this before
reviewing. It is short, and it will save you from reporting deliberate
decisions as defects, and from skipping fixes that are worth checking.

## What this is

A vendor-neutral **reference architecture** for newsletter and omni-channel
content orchestration, published as a playbook plus a reference
implementation: a FastAPI modular monolith on Postgres, a React manager client,
and the architecture decision records in `docs/architecture/ADR/`. It is not a
product; the *decisions* are the deliverable, and the code exists to prove they
work. How to run it is in `README.md`.

That framing matters for review: **"this is unusual" is only a finding if it is
also wrong.** Much of what looks unusual is argued in an ADR, and where it is,
the docstring usually names the record.

## What to review

Everything since the last external review (2026-08-07). In rough order of how
much a second pair of eyes is worth:

1. **`backend/app/approvals/`** — the held-action inbox (ADR-142). It *executes
   real sends* on approval, and since October it also holds an integration's
   "ready for this channel" mark for a person. Approve and reject are API
   routes for people only.
2. **`backend/app/auth/dependencies.py` and `backend/app/auth/policy.py`** — the
   person and machine guards (ADR-166). Machines are authenticated principals
   with explicit grants; a write permission also admits reads of its own area,
   through an exact table of routes (`MACHINE_READS`). Check ordering here was
   wrong once already; assume it can be wrong again.
3. **Brand isolation** — the working brand is resolved once and passed into
   every query as a required argument (ADR-172), but it is still a `WHERE`
   clause with no structural backstop such as row-level security. Leak paths
   are the thing to hunt; one is already known (below).
4. **Consent and the send-time exclusion stack** — `backend/app/recipients/consent.py`
   and `backend/app/delivery/exclusion.py`. A defect here is a compliance
   defect.
5. **The JSON API and the React client** (`frontend/`, ADR-170) — the newest
   surface; every screen of the React client goes through it.
6. **Inbound webhooks** — `backend/app/providers/adapters/resend.py`: signature
   check, fail-closed without a secret, and a five-minute window against replay.

## Deliberate — please do not report these as defects

Each is argued in an ADR or a docstring. Disagree if you like, but as a
*design* comment, not a bug:

| Thing | Why |
|---|---|
| No Alembic; hand-written SQL migrations | Migrations are meant to be *read*. A database records which files it has had (`schema_migrations`, ADR-181), and the app refuses to start while one is pending. A fresh database is built from the models instead |
| No foreign keys on `audit_events` | An accountability entry must outlive what it references |
| `audit.record()` swallows a database failure, but raises on a bad entry | A failed *log write* must not roll back the action it records, so the entry is written in a savepoint and only that is undone. An unknown action name or an email address in the detail is a bug in the caller and raises (ADR-153 addendum 2026-10-08) |
| The audit table refuses updates | Append-only is enforced by a database trigger, not by discipline (task-25) |
| Unsalted sha256 in `hash_secret` | 256-bit random secrets; nothing to brute-force. The six-digit sign-in code, the one low-entropy input, uses salted scrypt (`hash_login_code`), checked once on every path so the slow hash is not a timing oracle |
| Mock email and mock AI as defaults | Nothing commercial may be required to run this (ADR-171) |
| `blocked_reason` is advisory, not enforced | The action refuses itself; the UI hint is a courtesy |
| A policy table rather than per-route decorators | One legible table that refuses unclassified writes, versus decorators that fail open; machine reads are listed route by route |
| Consent computed from events, not stored | ADR-163: an event carries the source and timestamp that make consent provable; a column cannot |
| Postgres-specific features | SQLite silently changes behaviour, so portability is not claimed |
| No per-recipient state for lifecycle cycles | ADR-169: the anchor is a date, so position is computed |
| The server-rendered Jinja UI still exists | It is **frozen** by a test (`backend/tests/test_jinja_freeze.py`): no new routes. The React client replaces it; its retirement is not yet scheduled (task-312). Duplication between a Jinja route and a JSON route is expected until then |
| Dependencies installed only from hash-locked files | ADR-189; CI checks that what is installed is what is locked |
| A few SQL strings are built with f-strings | Audited 2026-10-09 (task-237): each interpolates an identifier Postgres cannot bind (a database name from configuration, or one read from the catalogue), never request data. Every value is a bound parameter. The same audit cleared template rendering, `random` and the file-serving paths |

## Already known and open — no need to re-find

From the work queue (`docs/queue/`, read with the `backlog` CLI):

- **No unsubscribe.** There is no unsubscribe or double opt-in route and no
  `List-Unsubscribe` header, and emails carry no footer yet (task-56, task-301).
  The design question that blocked it is settled (ADR-169 point 1); it is not
  built.
- **The consent-drift report ignores brand** — it compares and answers across
  brands (task-307).
- **Nothing is ever erased.** Erasure and retention (ADR-154) are designed, not
  built; `backend/app/privacy/` is empty (task-136, task-117).
- **The AI spend cap is check-then-act**: two concurrent runs can both pass the
  gate (task-124, part c).
- **Known structural debt:** six near-identical plugin registries (task-308),
  concurrency helpers living in `campaigns/` (task-309), approval logic in
  `main.py`'s exception handler (task-310), and `max_results` as dead
  configuration (task-109).
- **No licence has been chosen yet.**

## Recently fixed — please verify

These were known at the last brief and have since been fixed. A second look at
the fix is worth more than a fresh look elsewhere:

| Was | Fixed in |
|---|---|
| The sign-in timing oracle (a known address answered slower) | task-5; launch gate 4b closed 2026-09-29 (ADR-151 addendum) |
| `brand_id=None` meaning *every brand* on list functions; `permissions_for(brand_id=None)` as a union across brands | task-16, task-38; brand is now a required argument (ADR-172) |
| `recipients.consent` platform-level, so one brand's manager could write another brand's consent | task-7 |
| `delete_brand` guarding fewer tables than carry a brand | task-19, task-40 |
| `record_auth_failure` keyed on an attacker-supplied `key_id` | task-33 |
| The session resolved several times per request, each with a write | task-32 |
| Append-only audit by discipline only | task-25 (database trigger) |
| `sending_brand_id` returning `None` into `int` parameters | task-18 |

## What would be most valuable

Things **nobody decided** — which is where the last external review earned its
keep, by finding a bare `except ValueError` that swallowed a consent guard and
turned a compliance defect into a rendering behaviour.

Specifically: guards that do not guard, two checks that mask each other (several
such pairs have been found and more are expected), a path where an error is
reported as success, anywhere a permission is checked against one thing and a
row written against another, and concurrency on the send and approval paths.

## Ground rules

- **Verify against the code before reporting.** Every finding from the
  2026-08-07 review was checked before being logged, and that rule is why that
  review was useful rather than a pile of plausible-sounding bugs.
- Cite `file:line`.
- Say whether a finding is *reachable today* or *reachable after a plausible
  change*. Both are worth having; conflating them is not.

## Running it

See `README.md`. Tests: `cd backend && venv/bin/python -m pytest -q`, against a
test database the suite creates and seeds itself; it refuses to run against the
development database. CI (`.github/workflows/ci.yml`) runs the same suite on
every push.
