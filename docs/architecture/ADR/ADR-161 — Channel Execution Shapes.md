---
type: adr
status: proposed
topic:
  - architecture
  - channels
  - delivery
  - provider
created: 2026-09-01
modified: 2026-09-01
source:
  - "Omni-Channel design interview (interview-prep, closed 2026-09-01), Cluster 2 / Q6–Q10"
depends_on:
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
  - "[[ADR-101 — Provider Capabilities Are Explicit]]"
  - "[[ADR-104 — Audience Ownership Stays Outside Provider]]"
  - "[[ADR-160 — Channel Model and Composition]]"
  - "[[ADR-162 — Channel Rendering and Artifacts]]"
enables:
  - "[[ADR-163 — Per-Channel Consent and Addressability]]"
  - "[[ADR-164 — Channel Feedback and Signals]]"
---

## Status
Proposed

## Context

The provider contract today is `send(recipient_email, subject, html) -> SendResult` — three email concepts as positional arguments. A letter has no subject; a paid-social audience has no single address. [[ADR-160 — Channel Model and Composition]] settles what a channel is to a campaign and a variant; this record settles what a channel is to the outbound end.

Two execution shapes survive the pre-interview scoping. **Addressed** — email, push, SMS, WhatsApp, letter — where the platform produces one artifact per recipient and hands it to a provider with an address, personalises per recipient and gets feedback per recipient. **Audience-delegated** — paid social — where the platform supplies an audience membership list plus creatives and the ad platform decides timing, frequency and often which creative, so personalisation moves to per segment and feedback arrives aggregate. Dropping organic/broadcast social removed the third shape and, with it, the worst structural break: a broadcast post has **no recipient**, which would have forced `DeliveryExecutionDB.recipient_id` to become nullable and left campaign-level and per-recipient sends sharing an execution table with incompatible meanings. Paid social with custom audiences is still addressed, merely **delegated**, so the execution model survives intact.

Three constraints on delegated channels are designed around rather than discovered: identifiers go one-way (hashed identifiers are uploaded, never matched back), match rates are partial, and ad platforms enforce minimum audience sizes — which limits the "smaller and smaller groups" direction to email, push, SMS and letter and not paid social.

## Decision

**1. As many provider interfaces as the execution shapes genuinely need — never one interface with optional methods.**
Putting everything in one interface means compromises, and the compromise here is expensive: one interface with methods that raise is a capability system whose capabilities are discovered by calling and catching, which is the thing [[ADR-101 — Provider Capabilities Are Explicit]] exists to prevent. A bare capability flag was also rejected — it says *whether* something is supported, not *what to call*, when the signature is the thing that differs.

**Interfaces are keyed by what the provider needs, not by channel**, and the two do not map one-to-one: three channels can share one contract and one channel can need its own. As settled, there are **two**: **addressed** (email, push, SMS, WhatsApp and — per point 5 — letter, with the payload type declared by the manifest) and **audience-delegated** (paid social, roughly `sync_audience(group, identifiers)` plus `attach_creative(audience, artifact)`).

Typed contracts also buy the fail-closed property for free: code that only knows how to address recipients cannot be handed a delegated provider, because the type does not fit.

**2. Every interface ships a mock implementation.**
The design criterion for these interfaces is that they be *quick to create, edit, test and launch*, because an adopter is expected to adapt them to their own providers — the same weekend-not-half-a-year standard set in [[ADR-160 — Channel Model and Composition]]. "Quick to test" has a concrete consequence: a mock per interface, as `MockProvider` and `MockAIProvider` already do. The idiom exists twice already; this makes it a rule rather than a habit, and it is what keeps the test suite runnable without credentials.

**3. A delivery execution row for a delegated send records a TRANSFER, not a delivery.**
Per-recipient rows are still created, with a status vocabulary that does not lie: **`submitted`**, meaning "included in the uploaded list", never progressing to `sent` / `delivered` / `opened`, none of which are knowable. Match outcomes are unknown by construction, so there is no "not matched" state either — the honest terminal state is `submitted`.

The rows are kept for three reasons, **none of them delivery tracking**. Uploading a hashed identifier to an ad platform is a **transfer of that person's data to a third party**, a processing act needing an Art. 30 record. **Erasure** requires knowing which platforms hold someone, or the erasure stops at our boundary — the same loophole already flagged for the DWH in [[ADR-154 — Erasure and Retention]]. And **consent evidence**, per person, for a transfer whose lawful basis is sharper than email's. The same applies to letters: handed off, never confirmed read. If a platform later exposes delivery tracking, the row is already there to enrich — `submitted` is an accepted state, not a placeholder.

**4. Transfer records feed suppression only, never the signal layer.**
They answer "has this recipient already been given this content?", on the recorded **assumption** that *if transferred, count as has seen*. Because match rates are partial, that will suppress content from people who never actually saw it — a trade deliberately conservative on repetition (never spam) at the cost of reach (may withhold). The boundary is absolute: inferring *interest* from a transfer would fabricate preference data out of an upload, the same corruption [[ADR-164 — Channel Feedback and Signals]] guards against from the aggregate side.

Engagement can still return, but **through our own domain, not the channel**: a link in the letter or the ad carries our identifier and the adopter's own site fires it back. That generalises to a rule — **for any blind or delegated channel the return path is the adopter's property, never the platform's.**

**5. Letter uses the addressed interface; batch handoff is a provider capability, not a third shape.**
Some letter services take a per-message API call, others want a CSV plus a PDF bundle over SFTP — that is a difference *between vendors of one channel*, which is exactly the discriminator in point 6. The platform still calls `send()` per recipient; a batch adapter buffers and flushes on **`finalize()`**, which stays in the contract as designed. Per-message providers implement `finalize()` as a **no-op** — a small ceremony everyone pays so one case works, against a third interface that would be 90% identical. Status semantics come from point 3, not from a new shape: a batch yields one result for the handoff rather than one per recipient, so executions carry `submitted` until — *if* — the shop reports back, with optional later reconciliation.

**Scope: letter is an advanced feature and highly provider-dependent.** The POC should show that it is *possible*, not ship an integration; a real letter-shop connection will be heavily customised per company. The deliverable is a **library article** — "if you need batch instead of per message, here is how" — the same posture as the swap-send-provider and webhook guides, plus a **mock batch provider** demonstrating the flush path, which point 2 already requires.

**6. All capabilities live in the provider file. There is no channel capability declaration.**
[[ADR-101 — Provider Capabilities Are Explicit]] is **extended** from email providers to channel providers — same ADR, wider scope, no second system. Every channel should allow feedback; whether it *gets* one from the provider depends on the provider. The letter case proves the point: whether a returned letter comes back to you is a fact about the **letter shop**, not about "letter" — exactly as an ESP relay reports bounces while a generic SMTP host does not, within one channel.

A **channel-level capability file was proposed and rejected**. It would only help if kept current with everything the channel can possibly do, and it has **no owner** — it goes stale the moment a vendor ships something, whereas a provider file describes one thing its author actually knows. Duplication across provider files is accepted as the cheaper failure. The earlier suggestion of channel-as-ceiling / provider-as-actual with an intersection rule is **withdrawn as over-engineering**.

**7. The authoring contract is not a capability, and it lives in the module manifest.**
It exists *before* a provider is chosen: a manager picks a channel, not a vendor, and may not have selected one at all. "Push title, 40 characters" comes from the OS notification surface, not from APNs vs FCM vs OneSignal. If it lived in adapters, "push-ready" would mean *ready for which provider?* and swapping vendor could silently change it. Email already puts it in the manifest — `name.json` declares the fields, `name.html` renders them — so push is one module type whose manifest declares `title` / `body` / `image` / `link` and their lengths. No new file type. The settled split is therefore **provider `.py` = capabilities · module manifest = fields and limits · channel = an attribute on the variant plus which manifests it accepts**, leaving **cardinality** ("a push variant has exactly one module") as the only genuinely channel-level fact.

Two riders. **Catalogue readiness is "push fields not empty"** — not a length check and not a provider check, so the content catalogue stays independent of provider configuration. And **lengths are enforced by the editor as an input constraint** (`maxlength`), not as a validation gate and not from `provider.py`, because the "it will fail and we will notice" reasoning has a hole: the **4 KB total payload** is rejected outright by APNs and FCM, but **title and body lengths are accepted and the device truncates the display**, so nobody is ever told. The preferred handling is a **frontend preview showing potential truncation** rather than a block — truncation stops being a problem once it is visible, and this matches the *warn, never block* idiom already chosen for system mail and for campaign coverage. It is the same surface the letter and social previews will need.

**8. The platform owns frequency capping across channels, because nothing else can.**
Per-channel capping is structurally incapable of the thing that matters: each channel would faithfully cap itself at three and the recipient would get nine. Only the platform sees across channels, and it already holds the data. **Volume capping is not in the POC** — it is an advanced feature — but the *concept* is explained in the playbook, which is the right home for a capability an adopter will need before we build it. Numbers belong to the company, the mechanism to us, the same split already used for retention periods and the AI spend cap.

**9. Cross-channel repetition is not suppressed; deliberate follow-up is expressed as audience composition.**
A person who receives a topic as a newsletter may legitimately also receive it via push — as a reminder, because the email was not engaged with. That is not an accident to prevent; it is one of the more valuable things omni-channel enables. So the mechanism is an **audience rule, not a cap**: "push the topic to people who received the email variant and did not click within 48 hours" is an `AudienceRuleBlockDB` predicate over prior deliveries and engagement, which is exactly the parked **engagement-driven audiences** backlog item, gated behind the automation workstream ([[ADR-052 — Delivery Layer Supports Multiple Audience Resolution Modes]]). Cross-channel follow-up needs *that* item, not a frequency feature.

What remains a genuine risk is the **accidental** overlap — two variants of one campaign planned to overlapping audiences with no deliberate intent. It is handled by **surfacing the fact at variant plan time** ("380 of these 500 already received the email variant"), never by blocking, since the manager may want exactly that. This does not contradict [[ADR-160 — Channel Model and Composition]] point 7: that removed a *campaign-level* warning because no campaign-level send event exists; this is at **variant plan time**, which is a real moment. For delegated channels the exception is declared rather than pretended: the platform controls *inclusion in the audience*, not delivery frequency — the ad platform decides impressions.

## Consequences

### Positive
- The wrong provider cannot be handed the wrong work: mismatch is a type error rather than a runtime exception, so the fail-closed property comes from the contract instead of from care.
- `DeliveryExecutionDB.recipient_id` stays non-nullable, and campaign-level facts never share a table with per-recipient ones.
- A delegated send leaves a per-person record adequate for an Art. 30 processing record, for erasure across third parties, and for consent evidence — none of which a "we can't know who was reached, so don't record it" design would have.
- Letter costs one method on an existing interface instead of a third parallel contract.
- Capability declarations describe the configured provider, which is the only thing anyone is in a position to keep accurate. There is no second file to go stale.
- The authoring contract survives a vendor swap, because it never lived in the vendor's adapter.
- Cross-channel follow-up is expressible with machinery already planned, and deliberate repetition is not mistaken for a defect.

### Negative
- **Status vocabulary now varies by execution shape**, so anything aggregating statuses must know the shape. This directly touches the open P1 defect where a send instance reports `sent` unconditionally — that fix must handle a shape whose executions never reach `sent` at all.
- **`finalize()` is a no-op for every per-message provider** — ceremony paid by all adapters so that one case works.
- "If transferred, count as has seen" is a recorded assumption that is *known to be wrong for some people*: partial match rates mean content will be withheld from recipients who never saw it.
- Capabilities are duplicated across provider files, accepted as cheaper than an unowned channel-level file.
- Push title and body limits are enforced only by the editor and made visible by a preview. Anything writing a push outside the editor can still overrun silently, because the device truncates without reporting.
- **`DeliveryExecutionDB` has no `sent_at`.** `created_at` is written at plan time and `updated_at` is bumped by any later status change, so neither reliably answers "when did this actually go out" — which any capping or overlap check needs, and which also weakens the open P1 send-status work.
- Frequency capping is designed but not built, so an adopter who needs it in the POC period does not have it.

## Notes

- **Amendment another record needs, not made here:** [[ADR-101 — Provider Capabilities Are Explicit]] should be **extended in scope** from email providers to channel providers, and should record that batch-versus-per-message handoff and feedback granularity are provider capabilities. It already carries a dated addendum (2026-08-02) establishing that capabilities describe the configured provider instance rather than the protocol, and that is the same argument this record extends — so the appropriate form is a further **dated addendum**, not a superseding decision.
- Provisional groupings named in the interview were narrower than the settled outcome: three interface families were sketched (addressed per-message, addressed batch, audience-delegated) before the letter question collapsed the middle one into the first. Two interfaces, not three.
- The scope narrowing in point 7 supersedes nothing accepted; it narrows the description of a channel manifest given in [[ADR-160 — Channel Model and Composition]] point 6, and both records are written together.
- Deferred to a later phase by explicit decision: **volume capping**, **letter integration**, and **cross-channel follow-up audiences**. Two further deferrals are recorded in [[ADR-164 — Channel Feedback and Signals]].

## Related ADRs

### Depends On
- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]
- [[ADR-101 — Provider Capabilities Are Explicit]]
- [[ADR-104 — Audience Ownership Stays Outside Provider]]
- [[ADR-160 — Channel Model and Composition]]
- [[ADR-162 — Channel Rendering and Artifacts]]

### Enables
- [[ADR-163 — Per-Channel Consent and Addressability]]
- [[ADR-164 — Channel Feedback and Signals]]

### Referenced By
- [[ADR-052 — Delivery Layer Supports Multiple Audience Resolution Modes]]
- [[ADR-053 — Maintain Minimal Delivery Execution History]]
- [[ADR-095 — Use Send Instances for Technical Execution Tracking]]
- [[ADR-105 — Provider-Specific Data Must Not Be Architecture-Critical]]
- [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]
- [[ADR-154 — Erasure and Retention]]
