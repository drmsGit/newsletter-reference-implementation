---
type: adr
status: proposed
topic:
  - architecture
  - security
  - governance
  - privacy
created: 2026-08-02
modified: 2026-08-02
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
Proposed

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

- The audit log is **not** a replacement for the existing domain records and must not be allowed to become one. `AIRunDB`, `ContentOverrideDB`, `ConsentSyncLogDB` and delivery history remain the authoritative account of *what* happened; the audit log is authoritative for *who*.
- Retention of the audit log itself is out of scope here. It plausibly outlives the data it describes — see [[ADR-154 — Erasure and Retention]] for why that is coherent rather than contradictory.
- Aggregating failed logins (point 6) trades forensic detail for resilience: an investigator sees "41 failures against this address in this window," not each attempt. That is the right trade for a log whose value is accountability rather than intrusion detection; a company wanting per-attempt telemetry should ship it to a SIEM, which is the tool for it.

## Related ADRs

### Depends On
- [[ADR-150 — Tenancy and Access Model]]
- [[ADR-151 — Authentication and Sessions]]
- [[ADR-054 — Use Internal Recipient Identifiers]]

### Enables
- [[ADR-154 — Erasure and Retention]]
