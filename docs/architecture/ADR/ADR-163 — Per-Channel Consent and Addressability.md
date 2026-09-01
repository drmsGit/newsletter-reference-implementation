---
type: adr
status: proposed
topic:
  - architecture
  - channels
  - consent
  - privacy
  - data-model
created: 2026-09-01
modified: 2026-09-01
source:
  - "Omni-Channel design interview (interview-prep, closed 2026-09-01), Cluster 4 / Q16–Q20"
depends_on:
  - "[[ADR-004 — Privacy Operations as a First-Class Architectural Concern]]"
  - "[[ADR-120 — CRM as Customer Source of Truth]]"
  - "[[ADR-121 — Minimal Recipient Model]]"
  - "[[ADR-122 — Minimal Consent Model Required]]"
  - "[[ADR-154 — Erasure and Retention]]"
  - "[[ADR-160 — Channel Model and Composition]]"
  - "[[ADR-161 — Channel Execution Shapes]]"
---

## Status
Proposed

## Context

Consent is a single column today and `email` is the only address a recipient has. [[ADR-121 — Minimal Recipient Model]] lists one email and one consent status as minimum fields; [[ADR-122 — Minimal Consent Model Required]] distinguishes marketing from transactional communication and nothing else. Both assume one address and one consent state, which is exactly what a second channel breaks.

Consent for a delegated channel is also sharper than for email. Uploading a customer list to an ad platform is a **transfer to a third party**, and German supervisory authorities have taken a restrictive line on precisely this — the Bavarian authority's Facebook Custom Audiences decision being the usual reference. The current status of that line is a question for an adopter's counsel and is not settled from our side. The architectural obligation is the one [[ADR-144 — AI Data and Model Governance]] already states: we do not make the legal determination, we make the model granular enough that the adopter can encode whatever their counsel says.

There is a timing argument as well. The open P0 defect — a recipient can be mailed after opting out when the audience was frozen — lives in the same send-time gate that per-channel consent restructures. Designing this before fixing it means fixing it once, in the right shape.

## Decision

**1. Consent is append-only events, latest-wins per `(recipient, channel, purpose)`.**
Columns were never viable: five channels × three purposes is fifteen of them, none extensible without a migration, and a column cannot carry the **source** and **timestamp** that make consent provable. Events rather than mutable current state, for reasons already settled elsewhere: [[ADR-154 — Erasure and Retention]] requires consent proof to survive an erasure, and a mutable status overwrites exactly the history needed to defend a UWG §7 complaint; and the signal layer already made this choice, dropping the mutable `RecipientPreferenceDB` running total in favour of append-only contributions computed on read ([[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]). Consent is cheaper than signals — no decay, just latest-row-wins on an indexed query.

This removes an obligation rather than adding one: **the readable current state lives in the CRM anyway**, which is where customer service looks, so this platform does not need to be the human-facing consent store. For our purposes, latest is enough. Consistent with [[ADR-120 — CRM as Customer Source of Truth]] and [[ADR-126 — Maintain Local Recipient Projection]] — the CRM owns the readable truth, we hold the operational event log.

This **replaces `RecipientDB.consent_status`**, the single column the consent gate is built on in `resolve_audience` and `execute_decision_slot`. That schema change was already logged as a known cost when consent split by *purpose* in the security chapter; adding the channel dimension now means it lands once.

**2. Addressability is one table — rows plus a JSON `value` — holding every contact point a recipient has, whatever its type.**
Three things force it off `RecipientDB`. **Cardinality**: one email, but many push tokens — phone, tablet, a reinstalled app. **Lifecycle**: tokens expire and APNs reports dead ones, so a status you can mark invalid beats a value you overwrite. **Structure**: a postal address is street / postcode / city / country, not a string. A JSON `value` matches the idiom already used by `ContentRecordDB.content`, `module_data` and `app_config.value`.

**Hashed identifiers are not stored.** `SHA256(normalised email)` is computed when the audience is assembled. Storing it adds nothing already held and creates a second copy of the person to find at erasure time. It is a derivation step inside the delegated adapter, not addressability.

**3. Transfer to an ad platform is a consent *purpose*.**
`(recipient, paid_social, transfer)` sits alongside `(recipient, paid_social, marketing)` as an independent grant in the point 1 grid — no new machinery.

Folding transfer into the channel was the tempting simplification, since paid social is impossible without the upload, and it **breaks on an ordinary case: suppression uploads.** Companies routinely push a customer list to Meta in order to *exclude* those people from acquisition ads — a transfer with no marketing to them at all, arguably in their interest. If transfer were implied by channel consent, that case could not be expressed without claiming a marketing consent nobody gave. A **separate consent type** was rejected because it means a second consent mechanism beside point 1, with its own storage and its own gate — the kind that later gets checked in one place and forgotten in the other. **Out of scope** was rejected because the platform is the thing *performing* the transfer; shipping the capability while disowning permission for it leaves an adopter with no way to comply.

**4. Consent events and the CRM sync log stay two separate tables, because they record different kinds of fact.**
**Consent events** record what the *person* permitted, whatever the source — CRM sync, a signup form, an unsubscribe click, an import. **The sync log** records what happened in a *conversation with the CRM*: it ran, it failed, it found drift. Merging them would put failed sync attempts into somebody's consent history, and a sync that errored is not a consent change. A sync that does change something writes to **both** — an event with `source = crm`, and a sync-log entry saying the run applied N changes. The `source` field from point 1 links them without a second mechanism. Mapping lives in the **sync adapter, per deployment**, because every CRM differs — the same posture as the provider layer, and the same reasoning the inbound-adapter backlog item already uses in preferring "simple to adjust to your provider" over "one contract that auto-fits everything".

**5. The platform states the per-channel consent requirement; it does not infer around a CRM that cannot express it.**
A company that wants several channels **must capture consent per channel**, and will adjust its CRM to match — we already expect companies to prepare data in their own systems. So the platform builds no inference and no elaborate mapping to compensate. This settles a whole class of future questions of the form "should we infer X because their system lacks it?" — no. Consistent with [[ADR-120 — CRM as Customer Source of Truth]] and [[ADR-104 — Audience Ownership Stays Outside Provider]].

The consequence is stated rather than hidden: a single-flag CRM maps to `(email, marketing)` and reasonably to other addressed channels, but says nothing about uploading someone to an ad platform. **That grant is absent until captured, never inferred**, and the UI shows it missing rather than assumed — safe by construction, and the adopter goes and gets the consent. Drift grows with it: `GET /recipients/consent/drift` compares one status today, and becomes drift per `(channel, purpose)` — in sync on email marketing, adrift on social transfer.

**6. The send-time gate is per `(channel, purpose)`, and the cross-channel campaign question dissolves.**
A *variant* is planned and sent, not a campaign ([[ADR-160 — Channel Model and Composition]]), so there is no moment at which a campaign "spans channels" at send time. Each variant resolves its own audience against its own channel's consent, and the push audience simply comes out smaller. That is not a condition to handle — it is the answer.

**7. The gate is an ordered stack, run immediately before handing to the provider — and at audience assembly instead for delegated channels, which have no per-recipient send moment.**

1. **Addressability** — a valid, non-expired address for this channel.
2. **Consent** — a grant for this `(channel, purpose)`.
3. **Suppression** — hard bounce, complaint, manual blocklist.
4. **Frequency** — post-POC; the concept is documented in the playbook ([[ADR-161 — Channel Execution Shapes]]).

**8. The stack must record WHY each recipient was excluded, not merely exclude them.**
That is the real lesson of the open P0: the consent guard *did* fire, and a bare `except ValueError` threw the reason away, so a compliance defect read as a rendering behaviour. A stack that silently drops people reproduces that failure one layer up. Typed exceptions plus a recorded exclusion reason make "why didn't Anna get this?" answerable — which [[ADR-085 — Decision Resolution Should Be Optionally Explainable]] already promises for decisions and [[ADR-153 — Audit and Accountability]] is the home for. **This is the shape the P0 fix should be built in**, which was the reason for settling this cluster before fixing it.

**9. The order of the stack is a performance decision, not a correctness one, and it must be written down as such.**
All four stages are ANDed, so order never changes the outcome — only how many rows reach the later, more expensive stages, and frequency needs history. The intuition that consent-first reduces processed records is **right for email and probably wrong for push**: for email everyone has an address and some opted out, so consent is the selective filter; for push few people have a live token at all while most who installed granted permission, so addressability is. **Most-selective-first is channel-dependent** — do not hardcode one order as universal. It belongs in the performance-notes document with a trigger threshold.

**10. Each stage is expressed as a set operation, not a per-recipient loop.**
The set excluded by a stage is `input − output`, recordable in bulk, so per-stage attribution from point 8 survives without the N+1 pattern the send path is already flagged for (code review P2-04), and the query planner handles ordering within a stage.

## Consequences

### Positive
- Consent is provable, not merely current: source and timestamp survive, and proof survives an erasure in the minimised form [[ADR-154 — Erasure and Retention]] retains.
- New channels and new purposes cost a row, not a migration.
- Suppression uploads — a transfer with no marketing — are expressible, which folding transfer into channel consent would have made impossible without claiming a consent nobody gave.
- A recipient can hold many push tokens and a structured postal address without `RecipientDB` growing a column per channel.
- Nothing about a person's permissions is ever inferred. A missing grant shows as missing.
- One consent mechanism, one gate. There is no second consent path to check in one place and forget in the other.
- The exclusion stack turns "why didn't this person get it?" into a recorded answer, which is the property the open P0 defect proved was absent.
- Expressing stages as set operations gives per-stage attribution *and* avoids the N+1 already flagged on the send path.

### Negative
- **`RecipientDB.consent_status` goes away**, and with it the single-column gate in `resolve_audience` and `execute_decision_slot`. This is a schema migration touching the most safety-critical path in the system.
- Reading "is this person consented" becomes a query over an event log rather than a column read, and is only tolerable because the human-readable current state is the CRM's job, not ours.
- Two tables now describe consent-adjacent history — events and the sync log — and someone will eventually ask why. The answer has to be documented, not assumed obvious.
- An adopter whose CRM cannot express per-channel consent is told to change their CRM. Some will read that as a missing feature; it is a deliberate refusal to invent permissions.
- **Selection when a recipient has several addresses for one channel is unresolved.** See Notes.
- The stack's ordering is left channel-dependent and unhardcoded, which is correct but means there is no single answer to "what order does it run in".
- Addressability rows are identity data and sit in a table of their own, which makes them easy to overlook at erasure time — the same trap that made signals easy to miss.

## Notes

- **Open sub-problem, deliberately not decided here: which address to use when a recipient has several rows for one channel.** The semantics differ per channel — **push fans out** to every valid token, so all of the person's devices buzz, while **letter, SMS and email pick one**. That makes *fan-out vs pick-one* a **second channel-level fact**, alongside module cardinality from [[ADR-160 — Channel Model and Composition]]; both are "how many". For pick-one the minimal answer is a primary flag per `(recipient, channel)` with most-recently-verified as fallback, but that was not decided. It barely bites today — email has one address in practice and push fans out — and it only becomes real with letter or multi-email. It is a further reason to keep letter out of the POC.
- **Erasure reaches the addressability rows.** They are identity data, so they go with the identity under [[ADR-154 — Erasure and Retention]], not with the id-keyed activity that survives.
- **Amendments other records need, not made here.** [[ADR-121 — Minimal Recipient Model]] lists `email` and `consent status` among minimum recipient fields; the model stays minimal but both move out of it, so the record says otherwise on its face and needs a dated addendum. [[ADR-122 — Minimal Consent Model Required]] distinguishes only marketing from transactional and needs the `(channel, purpose)` grid — an amendment, not a superseding decision, and it composes with the consent purpose-split already recorded as a proposed amendment in [[ADR-150 — Tenancy and Access Model]]'s notes.
- Whether a German supervisory authority accepts a given lawful basis for Custom Audiences is an adopter's counsel's question. Ours is only whether the answer is **expressible**.

## Related ADRs

### Depends On
- [[ADR-004 — Privacy Operations as a First-Class Architectural Concern]]
- [[ADR-120 — CRM as Customer Source of Truth]]
- [[ADR-121 — Minimal Recipient Model]]
- [[ADR-122 — Minimal Consent Model Required]]
- [[ADR-154 — Erasure and Retention]]
- [[ADR-160 — Channel Model and Composition]]
- [[ADR-161 — Channel Execution Shapes]]

### Referenced By
- [[ADR-052 — Delivery Layer Supports Multiple Audience Resolution Modes]]
- [[ADR-054 — Use Internal Recipient Identifiers]]
- [[ADR-085 — Decision Resolution Should Be Optionally Explainable]]
- [[ADR-104 — Audience Ownership Stays Outside Provider]]
- [[ADR-126 — Maintain Local Recipient Projection]]
- [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]
- [[ADR-144 — AI Data and Model Governance]]
- [[ADR-150 — Tenancy and Access Model]]
- [[ADR-153 — Audit and Accountability]]
