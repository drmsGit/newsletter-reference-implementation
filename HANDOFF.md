# HANDOFF — Newsletter Blueprint

**Last updated:** 2026-09-13 · **Branch:** `main` · **Gates 2, 4 and 4b closed; gate 3 is the last P0**

The account migration this file was originally written for (2026-09-04) is
**done** — sessions now run on the business account, and nothing is left
stranded on the old one. What follows is the current state.

---

## ▶️ Paste this into a fresh session

```
Continue work on the Newsletter Blueprint at
/Users/diedeslembrouck/Projects/newsletter-reference-implementation — a
vendor-neutral reference architecture for email marketing systems (FastAPI
modular monolith + server-side Jinja UI), published as a playbook + starter
package.

READ FIRST (in order):
1. HANDOFF.md (repo root) — current state and the open queue.
2. CLAUDE.md (repo root) — project rules. ADR discipline is strict: required
   sections, status-in-two-places, never edit an Accepted ADR's Decision
   (supersede or append a dated addendum), never renumber. Highest ADR is 165.
3. docs/playbook-strategy.md §5 (Decision Log — read the 2026-09-12 and
   2026-09-13 entries),
   docs/backlog.md, docs/business/ (BRIEF, POSITIONING, LAUNCH-GATES,
   ASSUMPTIONS, BETA-SCOPE).
4. .claude/agent-memory/backlog-sequencer/ — the dependency graph and
   cost-of-delay classification. Refine it, don't rebuild it.
5. Your own memory entry "Newsletter Blueprint". Trust but verify any
   file:line claim against current code — several in the docs were wrong.

WORKING STYLE:
- State, before touching any file: which files change, what the change does,
  which ADR governs it (by number, or "none"), and what could break.
- Architecture decisions are ADRs in the repo, written BEFORE implementing.
  Business-side decisions go in docs/business/decisions/, not ADRs.
- One question at a time in interview/review passes; I decide each, nothing
  is written into an ADR until I've made the call.
- Use the project's own subagents in .claude/agents/ — adr-author for ADRs and
  addenda, backlog-sequencer for queue work, bug-fixer for a named 🔴 bug whose
  entry states its own fix (runs in a worktree; invoke with isolation:
  "worktree"), code-slimmer, adr-drift, positioning-critic, assumption-scanner. They are NOT selectable as
  subagent_type in the desktop app: launch general-purpose and tell it to read
  .claude/agents/<name>.md and follow that persona, restating hard constraints
  (e.g. backlog-sequencer must never edit docs/backlog.md).
- Never read all ADRs into the main session — delegate the sweep.
- Run the test suite from backend/, not the repo root.

Do NOT touch the 14 Needs-ADR items unless I ask — they were deliberately
left open across multiple review passes.
```

---

## Current state (2026-09-13)

### Omni-channel — designed and accepted; the consent half is built

**ADR-160–164** accepted 2026-09-12, and **ADR-165** written to supersede
**ADR-001** — the repository's **first supersession ever**. Seven dated addenda
were written to ADR-021/062/063/101/103/121/122, plus an eighth to ADR-163
recording four questions the implementation surfaced. Three decisions the
interview left open are closed (unlicensed-channel disable via a settings row;
address-pick via an optional `is_primary` flag with most-recently-verified
fallback; ADR-001's fate).

**Decided 2026-09-12:** the consent/addressability migration lands **before**
the Gate-2 P0 fix, so the P0 is built once, in ADR-163 §8's shape. Split into
two phases:

* **Phase A — consent. ✅ COMPLETE** (2026-09-13), and **launch gates 2 and 4b
  are closed**: the P0 send-time consent gate is built in ADR-163 §7's ordered-stack
  shape (`app/delivery/exclusion.py`), recording *why* each recipient was
  excluded, and the P1 beside it (a send reporting `sent` when every delivery
  failed) is fixed in the same function. Consent is append-only
  events keyed `(recipient, channel, purpose)`, latest wins.
  `recipients.consent_status` **is gone**, from the model and the database.
  All three gates read events. `ConsentDenied` (a `ValueError` subclass)
  replaces the bare `ValueError` at the decisioning gate. Drift is
  **directional** — `platform_ahead` means relay outward, `crm_ahead` means
  re-run the sync. The send path resolves its address from addressability, the
  webhook scopes opt-outs to the execution's channel/purpose, and dedupe runs
  on the resolved address in one bulk query.
* **Phase B — email → addressability. ✅ COMPLETE** (2026-09-13).
  `RecipientDB.email` is gone. Every display site resolves the address through
  `resolve_email(s)` or projects via `to_recipient(s)`. `to_recipients` is the
  bulk path — use it for any list, since the per-record form issues two queries
  each.

### Gate 4 — sign-in is guarded end to end (2026-09-13)

Three things landed, in this order: enforcement **defaults to ON**; CSRF covers
all 62 forms through one router-level dependency beside `enforce_policy`,
failing closed; and requesting a sign-in code is **rate limited per address and
per IP** (ADR-151 §2), five per address per 15 minutes and twenty per client per
hour, counted in `login_code_requests` rows.

A throttled request answers with the **same neutral 303** as every other
outcome, and **refusals are not counted** — counting them would let an attacker
hold a real person's address over the limit indefinitely, turning a mail-volume
control into a denial of sign-in. Both identifiers are stored hashed.

**Known limit:** behind a reverse proxy every visitor shares one per-IP bucket
unless `TRUST_PROXY_HEADERS=true`. Off by default, because an attacker who can
set `X-Forwarded-For` would otherwise get a fresh rate-limit identity per
request — a limit that is too broad fails safely, one that does not exist does
not.

### Database state: migrations 0001a–0005 applied

Both `scripts/migrate_0001a_consent_expand.sql` and
`scripts/migrate_0001b_consent_contract.sql` **have been applied** to the local
dev database. `consent_events` and `recipient_addresses` exist and are
populated (41 recipients → 41 events, 41 addresses), `delivery_executions` has
`channel` + `purpose`, and neither `recipients.consent_status` nor `recipients.email` exists any more.
`delivery_executions` also has `exclusion_reason`, and `send_instances` has
`sent_count` / `failed_count` / `excluded_count`. `migrate_0005` adds
`login_code_requests` — the sign-in rate-limit counter — and has been applied.
It was rehearsed twice on a scratch database first, and the schema it builds is
identical to the one `create_all()` produces.

Both scripts are idempotent and were rehearsed against a restored copy before
being applied: expand→contract clean, both re-runnable, contract-without-expand
refused, and a recipient inserted between the two runs correctly refused rather
than silently losing its consent state. `migrate_0001b` guards rather than
trusts — it will not drop anything unless every recipient already has a consent
event and an address.

**"Address" means the email address stored as a row, nothing postal**, and a
recipient is never required to have one — the guard only asks for an address
where the old email column had a value, and a recipient without one is simply
unreachable on that channel rather than rejected.

There is **no Alembic and no migration runner**. Decided 2026-09-12: schema
change is hand-written, numbered, idempotent DDL in `backend/scripts/`.
`Base.metadata.create_all()` only ever creates missing tables.

### Tests

207 green. **Run from `backend/`** — `test_auth_policy.py` opens a file by
relative path and fails from the repo root (pre-existing, not a regression).

`tests/test_consent_gates.py` is new and load-bearing: before it, the suite
stayed green whether the consent gates were intact or deleted. Every test in it
was mutation-verified — removing a gate fails only that gate's tests.

---

## Open queue

1. **Accept (or amend) ADR-150–154.** All five are still **Proposed**, in both
   places. The security base is built against them and two launch gates were
   closed by implementing them, so the code and the record disagree about how
   settled this is. Gate 3 needs them: a machine-auth ADR builds on ADR-150's
   access model and ADR-153's "the actor may be a system or an integration",
   and building on a proposal is what makes a cluster expensive to change.
   Found 2026-09-13 by the gate-3 ADR sweep; it was in nobody's queue.

2. **Gate 3 — inbound machine authentication (P0).** The interview **happened
   on 2026-09-13** and **[[ADR-166 — Inbound Machine Callers Are Authenticated
   Principals]] is written** — status **Proposed**, awaiting your acceptance.
   Written by `adr-author`; wikilinks verified (69 of 70 mentions, the one
   exception a protected verbatim quotation), every target resolves.

   **Before implementation can start, four things are unspecified** — the ADR
   flags each as such rather than inventing an answer:

   - **The concrete key list for the vocabulary split. This one blocks.**
     `permissions.py`'s own rule is that a key names a code path, so the list
     cannot be settled apart from the guards it creates.
   - **What "unattended" is scoped to.** Decided for real sends; consent writes,
     bulk recipient reads and credential changes are unstated.
   - **Rotation overlap** — may an integration hold two live credentials at
     once? Without it every rotation is a small outage for the caller; with it,
     revocation semantics need stating.
   - **Brand selection on inbound calls.** A human picks the brand from
     navigation context (ADR-150 §2); a machine has none. Sits directly under
     decision 7's derivation.

   **Also pending:** the **ADR-150 amendment** for the finer permission
   vocabulary. `adr-author` supplied the text and deliberately did not apply it
   — ADR-150 is Proposed, so it is a direct edit to point 5 or a dated addendum,
   and that is your call. The text is in the agent's report.

   **And check before building decision 5:** its safe default ("machine sends
   land in ADR-142's approval surface") needs that approval surface to exist. If
   it does not yet, the default has nothing to fall back to.

   The six decisions, for reference:

   1. **A machine caller is a principal inside ADR-150**, not a parallel
      authorization system — it holds permission rows in the same table a user
      does, brand-scoped, and resolves to an ADR-153 actor. A company wanting a
      cleaner separation may build one; the reference build does not. Issued as
      **key + secret pairs** so systems are distinguishable.
   2. **The permission vocabulary gets finer keys, for humans and machines
      alike.** The nine in `app/auth/permissions.py` are too coarse for this
      feature's own example — pinning a recipient lives under
      `audiences.manage`, which also deletes groups. An **amendment to ADR-150**
      (still Proposed), not a supersession.
   3. **An integration owns its credentials**, and the *integration* is the
      durable audit actor — so history stays continuous across a rotation and
      still reads "n8n triggered this send" a year later.
   4. **`integrations.manage` gates issuance, any holder may hold it.** A
      credential is **independent of its creator**: deactivating a user does
      *not* revoke keys they issued, because the key belongs to the integration.
      **Known gap, accepted deliberately:** ADR-151 pt.5 calls deactivation "the
      whole offboarding control" and this is a hole in that story.
   5. **Unattended real sends are configurable per integration, defaulting to
      requiring approval** — a machine send lands in ADR-142's approval surface
      unless that integration is deliberately flagged otherwise.
   6. **`POST /provider/events` is kept and locked**, not removed. Two inbound
      mechanisms coexist on purpose: platform-issued credentials for systems the
      adopter controls, provider signature verification for providers, who
      cannot hold a credential the platform issued. ADR-164 pt.7 plans the
      conversion callback on exactly that endpoint's shape.

   **Scale of the hole being closed:** 69 unguarded JSON routes, 36 of them
   state-changing — including `POST /delivery/send-instances/{id}/send` (fires
   real mail), `POST /recipients/{external_id}/consent` (writes the compliance
   record), `GET /recipients/` (dumps PII) and `POST /insight/events`.
3. **Gate 1 — the positioning statement.** Still the named blocker on public
   beta, and unchanged by any of this: rule 2 was tested on 2026-09-12 and
   held, so omni-channel stays out of the headline claim until a second channel
   actually sends.

## Known-stale or wrong claims to distrust

The 2026-09-12 sequencer pass found the docs assert things that are not true.
Corrected already, but the lesson stands — **verify before trusting a status
claim in this repo**:

- The roadmap's ✅ marks are **asserted, not audited**. One item the backlog
  listed as open (the category picker) was already built; two Done items are
  reversed by the new ADRs.
- `requirements.txt` said `httpx2` while all code imports `httpx`. Fixed —
  note `httpx2` is a real package (Pydantic's successor), so `pip install`
  *succeeded* and failed later at import.
- The claim that `database.py`'s engine-at-import made four test modules
  uncollectable was **wrong** — I put it in LAUNCH-GATES.md on trust and had to
  correct it. The tests collect fine; three of them need a live seeded Postgres,
  which is the isolated-test-DB design item.
- The 11-broken-wikilink count is disputed; re-run `adr-drift` rather than
  citing either number.

## Positioning gate

Public beta is blocked on the positioning statement, not on features.
**Tested 2026-09-12 and it held:** omni-channel being designed-and-accepted does
**not** clear POSITIONING.md's rule 2 ("no claim that cannot be demonstrated in
the repo today"), because only email is built. The channel-neutral sharpening
stays out of the headline claim until a second channel actually sends.

One P0 defect still blocks public exposure — gate 3. See `docs/business/LAUNCH-GATES.md`.

*Git remote: `github.com/drmsGit/newsletter-reference-implementation`.*
