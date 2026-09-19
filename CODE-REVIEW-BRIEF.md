# Code review brief — Newsletter Blueprint backend

**Prepared 2026-09-19.** Read this before reviewing. It is short, and it will
save you from reporting a dozen deliberate decisions as defects.

## What this is

A vendor-neutral **reference architecture** for email and omni-channel
marketing systems, published as a playbook plus a starter package. A FastAPI
modular monolith with a server-side Jinja UI, Postgres, and 86 architecture
decision records in `docs/architecture/ADR/`. It is not a product; the
*decisions* are the deliverable, and the code exists to prove they work.

That framing matters for review: **"this is unusual" is only a finding if it is
also wrong.** Much of what looks unusual is argued at length in an ADR, and
where it is, the docstring usually names the record.

## What to review

**The diff since the last external review (2026-08-07): 149 commits, 155 files,
~25,700 insertions.** In rough order of how much a second pair of eyes is worth:

1. **`backend/app/approvals/`** — a week old, written in one stretch, and it
   *executes real sends* on approval. Least-reviewed, highest blast radius.
2. **`backend/app/auth/dependencies.py`** — the machine/person guard. The check
   ordering here was wrong once already (an integration with no grant could
   have minted a held send); assume it can be wrong again.
3. **Brand isolation** — `brand_id` is a `WHERE` clause with no structural
   backstop, and three list functions default it to *every brand*. Leak paths
   are the thing to hunt.
4. **The JSON API surface added this week** — session sign-in, builder edits,
   audience rule blocks, the delivery cron seam.
5. **`backend/app/recipients/consent.py`** — the send-time exclusion stack. A
   defect here is a compliance defect.

## Deliberate — please do not report these as defects

Each is argued in an ADR or a docstring. Disagree if you like, but as a
*design* comment, not a bug:

| Thing | Why |
|---|---|
| No Alembic; hand-written SQL + `create_all` | Migrations are meant to be *read*; 17 numbered files beat a generated chain |
| No foreign keys on `audit_events` | An accountability entry must outlive what it references |
| `audit.record()` swallows every exception | A failed *log write* must not roll back the action it records |
| Unsalted sha256 in `hash_secret` | 256-bit CSPRNG secrets; nothing to brute-force **(the six-digit login code is a known exception and is logged)** |
| Mock provider / mock AI as defaults | Nothing commercial may be required to run this (ADR-171) |
| `blocked_reason` is advisory, not enforced | The action refuses itself; the UI hint is a courtesy |
| Prefix-matching policy table, first match wins | One legible policy that refuses unclassified writes, vs decorators that fail open |
| Consent computed from events, not stored | ADR-163: a status you can overwrite beats nothing |
| Postgres-specific features | ADR/testing.md: SQLite silently changes behaviour, so portability is explicitly not claimed |
| No per-recipient state for lifecycle cycles | ADR-169: the anchor is a date, so position is computed |
| Approve has no API route | Deliberate, and **already being changed** — see below |

## Already known — no need to re-find

**21 items were logged on 2026-09-19** from an internal review. The sharpest,
so you do not spend time on them:

- The sign-in **timing** oracle (a known address makes a synchronous provider
  call before its 303; an unknown one returns after a SELECT). Launch gate 4b
  is reopened for it.
- `brand_id=None` meaning *every brand* on three list functions.
- `permissions_for(brand_id=None)` meaning the union across every brand.
- `recipients.consent` being platform-level although `consent_events.brand_id`
  is now NOT NULL — so a Manager on brand A can write brand B's consent row.
- `delete_brand` guards five tables; there are seven NOT NULL brand FKs.
- `record_auth_failure` buckets on an attacker-supplied `key_id`.
- The session resolving 4–5 times per request, each with a write and commit.
- No `REVOKE UPDATE` on the audit table — append-only is discipline, not a
  guarantee.
- `sending_brand_id` returns `int | None` into parameters typed `int`; it fails
  closed only because SQLAlchemy renders `== None` as `IS NULL`.

Full text with reasoning: `docs/backlog.md`, Bugs section.

## What would be most valuable

Things **nobody decided** — which is where the last external review earned its
keep, by finding a bare `except ValueError` that swallowed a consent guard and
turned a compliance defect into a rendering behaviour.

Specifically: guards that do not guard, two checks that mask each other (this
codebase has found six such pairs and expects more), a path where an error is
reported as success, anywhere a permission is checked against one thing and a
row written against another, and concurrency on the send and approval paths.

## Ground rules

- **Verify against the code before reporting.** This project's backlog records
  that every finding from the 2026-08-07 review was checked before being
  logged, and that rule is why that review was useful rather than a pile of
  plausible-sounding bugs.
- Cite `file:line`.
- Say whether a finding is *reachable today* or *reachable after a plausible
  change*. Both are worth having; conflating them is not.

## Running it

Tests: `cd backend && venv/bin/python -m pytest tests/ -q` — **567 passing**,
against an isolated test database the suite creates and seeds itself
(`backend/tests/conftest.py`). It refuses to run against the development
database.
