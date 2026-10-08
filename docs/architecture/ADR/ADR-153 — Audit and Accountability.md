---
type: adr
status: accepted
topic:
  - architecture
  - security
  - governance
  - privacy
created: 2026-08-02
modified: 2026-10-08
source:
  - "Security Chapter design interview, Part 2 (playbook-strategy.md Decision Log, 2026-08-02)"
depends_on:
  - "[[ADR-150 — Tenancy and Access Model]]"
  - "[[ADR-151 — Authentication and Sessions]]"
  - "[[ADR-054 — Use Internal Recipient Identifiers]]"
enables:
  - "[[ADR-154 — Erasure and Retention]]"
---

## Status
Accepted

## Context

[[ADR-150 — Tenancy and Access Model]] describes the external agency operator as *"distinguished by accountability, not capability."* That sentence is only true if the accountability exists — and today it cannot, because there are no users to attribute anything to.

The platform already keeps several append-only records: AI runs with their prompt version and cost, content overrides with the system's original recommendation, consent sync logs, and delivery history. These were built for product reasons, and each answers "what happened" within its own domain. None of them answers "who asked, and from where," because until now there was only ever one operator.

[[ADR-142 — Autonomous Workflows and the Automation Boundary]] adds a further requirement: machine-initiated actions must land in the same action history as human ones.

## Decision

**1. One append-only audit log for actor-attributed events, alongside the existing domain records.**
The domain logs remain what they are — history the product needs to function. The audit log serves a different purpose: **accountability**. It records who acted, on what, when, and from where.

The resulting overlap is accepted deliberately. It buys one screen answering "what has this operator done," one export a company can ship to its SIEM, and one place a reviewer or DPO can be pointed at — none of which a set of domain-specific logs provides, however complete each is individually.

**2. It also holds events that have no domain record at all.**
Login success and failure, role assignment and removal, user deactivation, and credential changes ([[ADR-152 — Secret and Credential Handling]]) have no natural home elsewhere. Without this log they are simply not recorded.

**3. The actor may be a system or an integration, not only a person.**
ADR-142 requires machine-initiated actions in the same history, so the actor is modelled as *some* authenticated principal from the start. Building this in now costs nothing; retrofitting it when Mode B lands means revisiting every write path a second time.

**4. Scope: writes, plus exports and bulk reads — not individual page views.**
Writes are the obvious floor. Reads of personal data matter too — an external operator paging through the recipient list leaves no trace under a writes-only policy, and that is exactly the party a controller wants visibility on — but logging every read is expensive and buries the signal in traffic.

The line is drawn at **actions that move personal data out of the system or pull it in volume**: exports, downloads, bulk queries. Those are the exfiltration-shaped actions, which is the actual risk. Ordinary navigation is not logged.

**5. Entries reference internal identifiers, never contact details.**
An audit entry records *recipient 45*, not *anna@example.com*. Stated here rather than only in [[ADR-154 — Erasure and Retention]] because it is a constraint on how this log is written, not merely a consequence of it.

Note the asymmetry this creates, which is deliberate: an entry attributing an action to an **operator** references that operator and survives the erasure of any *recipient*. Entries that reference an erased **recipient** follow whatever erasure depth the company has chosen (ADR-154). So "which operator exported the list, and when" is durable, while "which people were in that export" may not be.

**6. Failed authentication attempts are aggregated, not recorded one by one.**
An unauthenticated attacker can generate failed logins at will, so a log that writes a row per attempt is a write-amplification target — an attacker could fill the disk, or bury real events under noise, without ever holding a credential. Failures are therefore counted and summarised per address and per source over a window, with the aggregate recorded rather than each attempt. Successful logins are recorded individually, since those require a credential and are the ones accountability actually turns on.

## Consequences

### Positive
- The agency-operator model in ADR-150 becomes enforceable rather than aspirational.
- A company gets one artefact to hand an auditor, and one export for a SIEM.
- Security-relevant events that currently vanish (failed logins, role grants, credential changes) become visible.
- Mode B arrives into a history that already accommodates non-human actors.
- Operator accountability survives an erasure request, because of point 5 — the person can go while the record that someone exported their data remains.
- The log cannot be flooded by an unauthenticated attacker.

### Negative
- The same event is recorded twice in some cases, in the domain log and the audit log. Storage is cheap; the reasoning cost of "which log is authoritative for what" is the real price, and it is paid by stating the split clearly (history versus accountability).
- An append-only log grows without bound and needs a retention policy of its own — which interacts with, and is deliberately not settled by, the open data-lifecycle item.
- Writes-plus-exports still leaves ordinary reads unlogged, so "who looked at this recipient" is answerable only when they exported. This is a knowing gap, chosen over an unusable volume of noise.
- Every write path needs to carry an actor, which is a change to code written when no actor existed.

## Notes

- The audit log is **not** a replacement for the existing domain records and must not be allowed to become one. `AIRunDB`, `ContentOverrideDB`, `ConsentEventDB` and delivery history remain the authoritative account of *what* happened; the audit log is authoritative for *who*. Corrected 2026-09-14: `ConsentSyncLogDB` is **not** that record for consent. Since [[ADR-163 — Per-Channel Consent and Addressability]] it deliberately carries no consent values — it records only that a CRM sync ran, failed, or applied N changes, and drift is computed from the event log (`backend/app/recipients/db_models.py`). The authoritative consent record is the append-only `ConsentEventDB`, which this record did not previously name.
- **Implementation status, 2026-09-19:** **the first slice is built, and it is the administrative half.** `backend/app/audit/` holds `AuditEventDB` and a service exposing `record` / `record_from_request` plus two read helpers, created by `backend/scripts/migrate_0009_audit_log.sql` — whose verification query asserts **zero foreign keys**, because an accountability entry must outlive what it references (point 5). Eight actions are recorded: sign-in, role granted/revoked, user deactivated/reactivated, `brand.created`, `campaign.duplicated`, `content.duplicated`. **What points 1–6 still owe:** no send, no consent write and no AI run is logged; there is no export and no bulk read (point 4); point 1's operator screen is *enabled* by the composite indexes and the read helpers but not built, and **nothing in production reads the table back**; point 6's aggregated authentication-failure record now exists for machine callers only (`integration_auth_failures`), and failed human sign-ins are still deliberately unlogged. `ACTOR_INTEGRATION` is defined and **nothing writes it**, so no row has yet named an integration as its actor — the half of [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] point 3 that remains owed. Amended 2026-09-19: `backend/app/approvals/service.py` writes audit entries **from a service with an explicit actor**, departing from this record's written-from-routes convention on the grounds that an expiry has no request behind it at all, and adding a third actor type, `ACTOR_SYSTEM`.
- **Implementation status, 2026-09-14 (superseded by the note above):** **Nothing in this record is built.** There is no audit table anywhere in `backend/` — no `__tablename__` across `backend/app/*/db_models.py` is an audit log — so points 1 through 6 have no implementation. The only actor field in the system is `ContentVersionDB.created_by`, free text typed into a form (`backend/app/content/db_models.py`, `backend/app/frontend/router.py`). Point 6's aggregated authentication-failure record does not exist either: `LoginCodeRequestDB` is a rate-limit counter over hashed address and client, and its own docstring calls it "a counter, not an audit trail".
- Retention of the audit log itself is out of scope here. It plausibly outlives the data it describes — see [[ADR-154 — Erasure and Retention]] for why that is coherent rather than contradictory.
- Aggregating failed logins (point 6) trades forensic detail for resilience: an investigator sees "41 failures against this address in this window," not each attempt. That is the right trade for a log whose value is accountability rather than intrusion detection; a company wanting per-attempt telemetry should ship it to a SIEM, which is the tool for it.

## Addendum 2026-10-01 — an entry is written where the actor is known

Prompted by task-23, from Interview Prep - Channels (Audit B-Q4), and decided by
the user on 2026-10-01. Points 1–6 stand; what changes is where an entry is
written, and how strictly the route-side writer reads its actor.

**The written-from-routes convention had stopped holding, and nothing restated
it.** The module docstring of `backend/app/audit/service.py` opened with
*"Written from routes, not from services."* The route knows the actor —
`request.state.current_user`, resolved once by middleware — and a service takes
a session, not a request. Threading an actor through every write signature was
rejected: a brand is a property of the data, and is threaded, rightly; an actor
is a property of the request. The docstring named its own cost — *"a service
called from somewhere other than a route is not audited"* — and called it the
first thing to revisit when it did not hold.

**Approvals is where it did not hold.** The 2026-09-19 implementation note above
records that `backend/app/approvals/service.py` writes entries from a service
with an explicit actor, and adds `ACTOR_SYSTEM`. Two of its events have no route
behind them. `approval.requested` belongs to a machine refused inside a
dependency: the guard raised `ApprovalRequired` before any route handler ran,
and the handler in `backend/main.py` creates the held request
([[ADR-142 — Autonomous Workflows and the Automation Boundary]] §4).
`approval.expired` has no request at all — the expiry sweep writes it. Approval
decisions are written by the service with the approver passed in. One module was
therefore a documented exception rather than a stated pattern.

**1. An entry is written where the actor is known, and never where it would have
to be guessed.** A route writes it from the request, through
`record_from_request`. A service writes it — with the actor passed explicitly —
only when no request carries the actor:

- an event with no request at all, such as a sweep or a scheduled job, written
  as `ACTOR_SYSTEM`;
- an event whose actor was resolved before any route handler ran, such as a
  machine's held request, written as the integration
  ([[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]);
- a decision whose actor the service is handed, such as the approver.

This states as a pattern what approvals did as an exception. The route
convention stays the default, and the reasoning against threading actors
through domain signatures stands.

**2. The cost that remains, stated.** A service called from a script or job that
passes no actor is still not audited. Writing such an event requires an
explicit actor; nothing infers one.

**3. `record_from_request` reads the middleware's attributes strictly.** It read
`current_user` and `current_brand` through `getattr(..., None)`. The middleware
`attach_current_user` in `backend/main.py` sets both on every request —
`current_user` is None when nobody is signed in — so the default was never
needed. What it did do was let a renamed middleware attribute turn every actor
into NULL silently: fail-open in the one field this table exists for. Both are
now read without a default, so a renamed attribute raises at the first audited
request instead of writing NULL actors forever. `working_brand_id` keeps its
default, because it is legitimately absent on the Jinja plane: only the JSON
guard sets it.

**What this costs.** A request that somehow bypasses the middleware now raises
on an audited write rather than writing an actorless row. That is intended —
loud beats silently wrong. The scripts-and-jobs gap of point 2 is named here,
not closed.

## Addendum 2026-10-08 — What an audit entry may say, enforced where it is written

Prompted by task-52, from [[Interview Prep - Channels, Audit]] B-Q5, and
decided by the user in chat on 2026-10-08, one question at a time. Points 1–6
stand. B-Q5 found three things about `audit_events` that were stated but
unproven, because nothing reads the table back. Two are now enforced where an
entry is written. The third is settled before the first reader is built.

**What was found on 2026-10-08.**

- All 39 action names stored on dev were known constants. But nothing stopped
  a typo, and the names lived in three places: `backend/app/audit/service.py`;
  the approval lifecycle constants in `backend/app/approvals/service.py`; and
  two plain strings in approval actions, `"send.fired"` and
  `"ai.suggestion_applied"`.
- Two kinds of entry put a person's email address into `detail`. That breaks
  point 5, and [[ADR-154 — Erasure and Retention]] point 3.
  `variant.unfenced` copied the fence holder's label. `content.ready_unmarked`
  copied who had marked the record ready.
- Sign-ins (`user.signed_in`) and settings changes (`settings.changed`) are
  written with no brand, as point 2 intends.

**1. One vocabulary, and an unknown action is refused at write time.** Every
action name is a constant in `backend/app/audit/service.py`. The approval names
and the two plain strings move there. `record` refuses a name outside the
vocabulary. A typo is a programming error, so the suite fails on the first test
that writes it. This fits the split `record` already keeps: it never raises for
a database failure, and a bug in the calling code raises like any bug. A
test-only scan was rejected, because a dynamically built name slips past it.

**2. A `detail` holding an email-shaped value is refused at write time.** Point
5 becomes a check, not only a policy.

- The two leaking entries carry what identifies the actor internally instead,
  or drop the label.
- Phone numbers are not checked. They are too varied to detect reliably, and
  nothing writes one.
- A future legitimate company address, such as a sender address in a setting,
  must be exempted deliberately, key by key. Without an exemption the check
  fails closed.
- **Authored copy is exempt.** This is the first key-by-key exemption, and it
  is for copy, not for a company address. The user decided it on 2026-10-08,
  while task-52 was being built. Variant and campaign names, content titles
  and a variant's envelope (subject, preheader) are copied into audit details.
  Copy can legitimately mention an address ("Reply to hello@brand.test"). As
  first built, a save whose copy held an address would have failed with a 500.
  The exemption is an explicit, named set of top-level detail keys in
  `backend/app/audit/service.py`: `COPY_KEYS = {"name", "title", "envelope"}`.
  Top level only: a `name` nested deeper is not copy by that fact alone, and is
  still checked. Every other key still fails closed. Two other options were
  offered and not chosen: logging only which envelope fields changed, which
  keeps less evidence of what the subject said; and staying strict, so copy
  could never contain an address.
- Entries already stored keep what they say. The audit log is not rewritten.

**3. A brand filter includes entries with no brand.** Filtering one actor's
history by brand returns that brand's entries plus the brand-less ones:
sign-ins and platform settings. They belong to the person, not to a brand. A
plain `brand_id = X` would silently hide exactly the entries point 2 says have
no other home. This is built as the one tested way to filter `events_by_actor`
by brand, for the operator screen of point 1, which is not built yet. Showing
brand-less entries only in an all-brands view was rejected.

**Not decided here.** Retention, and the count of indexes on this write-mostly
table. Both stay with the general data-lifecycle decision (task-136), as the
interview said.

**Consequences.**

- **Positive.** A typo or a leaked address fails the first test that writes it.
  The operator screen inherits a correct brand filter.
- **Negative.** An audit write can now fail a request. On an untested path, a
  bad name fails in use rather than writing a silent typo; that cost is
  accepted. The email check is a pattern and catches email addresses only. A
  company address needs an explicit exemption.
  An address someone types into copy stays in the log; that cost is accepted.

Built the same day, under task-52. Nothing here changes the Decision section
above.

## Related ADRs

### Depends On
- [[ADR-150 — Tenancy and Access Model]]
- [[ADR-151 — Authentication and Sessions]]
- [[ADR-054 — Use Internal Recipient Identifiers]]

### Enables
- [[ADR-154 — Erasure and Retention]]
