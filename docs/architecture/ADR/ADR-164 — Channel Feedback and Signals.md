---
type: adr
status: accepted
topic:
  - architecture
  - channels
  - signals
  - analytics
  - provider
created: 2026-09-01
modified: 2026-09-12
source:
  - "Omni-Channel design interview (interview-prep, closed 2026-09-01), Cluster 5 / Q21–Q25"
depends_on:
  - "[[ADR-101 — Provider Capabilities Are Explicit]]"
  - "[[ADR-103 — Provider Events Are Normalized Into Internal Events]]"
  - "[[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]"
  - "[[ADR-160 — Channel Model and Composition]]"
  - "[[ADR-161 — Channel Execution Shapes]]"
---

## Status
Accepted

## Context

The signal layer is neutral in shape — `(recipient × category × contribution)` with decay on read ([[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]) — and only its *vocabulary* is email-derived. What omni-channel changes is not the shape but the supply: some channels return per-recipient events, some return numbers per audience and creative, and some return nothing at all.

The danger is specific. Attributing aggregate numbers down to individuals would fabricate preference data and corrupt the per-recipient signal layer, which is precisely the thing that makes the decision layer trustworthy. [[ADR-161 — Channel Execution Shapes]] already draws the same line from the delegated side, where a transfer record feeds suppression and never signals. This record settles how feedback is declared, where each kind of feedback lands, and what the signal layer needs in order to make [[ADR-160 — Channel Model and Composition]]'s forward consequence — the engine choosing a channel per recipient — possible at all.

## Decision

**1. Feedback granularity is declared per PROVIDER, never per channel.**
Technology changes, and a social platform might allow per-recipient feedback in future. Encoding "social = aggregate" anywhere would bake a vendor limitation into the architecture with a shelf life. This closes a loop: it is the same argument that made the rejection of a channel-level capability file correct in [[ADR-161 — Channel Execution Shapes]], and it extends [[ADR-101 — Provider Capabilities Are Explicit]] rather than adding a second declaration system.

**2. The declaration is enforced at ingestion, because a declaration nothing checks is decoration.**
A provider that declared aggregate-only and attempts to write a per-recipient event is **refused and fails loudly**. That guard is also point 4's protection: aggregate leaking into per-recipient signals is an enforcement gap rather than a discipline problem, and closing it here closes it structurally.

**3. Two destinations, and this is the load-bearing split.**
**Per-recipient events → the signal layer → decisions.** That is what signals are *for*. **Aggregate results → analytics**, a human-read view and not a decision input: if a company wants to use numbers from social or letters, that is an analytical look rather than signals feeding the decision algorithm. Aggregate data is therefore **not discarded** — it lives in reporting rather than the decision path, and **is never interpolated onto individual recipients**.

**4. Aggregate feedback lives in a separate table with its own grain — explicitly not the engagement event table with `recipient_id` made nullable.**
That is the same reasoning that made dropping organic social a simplification: a nullable recipient column leaves campaign-level and per-recipient facts sharing a table with incompatible meanings. Every consumer would then have to remember `WHERE recipient_id IS NOT NULL` — the signal layer, attribution, every report — and one omission means segment numbers are read as a person's behaviour, silently. **The corruption would arrive through the schema rather than through carelessness, so the schema is where it gets prevented.** The table is keyed by what aggregate data is actually about: `(send_instance or audience, creative/variant, metric, value, period)`. The signal layer then **cannot physically read it** — the guarantee becomes structural rather than a rule to follow, the same property typed interfaces bought in [[ADR-161 — Channel Execution Shapes]].

**5. A thing with no recipient is not an event in ADR-103's sense. It is a metric.**
Internal events are per-recipient by construction: they carry a recipient, feed signals and attribute to content. Something reported per audience-and-creative over a period has a different grain, a different table and a different consumer. **Calling both "events" is what pushes toward the nullable column — the noun does the damage before the schema does.** [[ADR-103 — Provider Events Are Normalized Into Internal Events]] therefore needs only a **scope clarification**: it governs per-recipient events. Metrics have their own path, not built. The rule to state because it is the part that gets forgotten: **an event without a recipient is refused at ingestion, not stored with a null.** Together with the point 2 declaration check, that is what makes point 4's separation hold at runtime and not only in the schema. The distinction pays immediately — "audience synced, 340 of 500 matched" is genuinely useful to a manager and genuinely meaningless attributed to anyone.

**6. Feedback source is not the same thing as provider.**
For blind channels the return path is the adopter's **own domain** — a tracked link in a letter or an ad firing back with our identifier from their site ([[ADR-161 — Channel Execution Shapes]]). A letter-shop adapter declaring "no feedback" is accurate about *itself* while per-recipient engagement still arrives by another route. So **any channel can have per-recipient feedback if the adopter instruments their own site**; it is just not the provider's to give. That is a better line for the playbook than "letters have no feedback".

**7. The conversion-API path is a documented extension point, not a POC build.**
Consistent with the existing backlog decision that conversions are a pluggable contribution type whose ingest path is per-deployment, delivering the extension point plus one worked example when a real adopter needs it. Omni-channel does not change the answer, it raises the stakes: for delegated and blind channels this is the **only** per-recipient feedback path there is. The mechanism largely exists — a conversion callback is structurally what `POST /provider/webhooks/resend` already does, an external system posting an event carrying an identifier. What is missing is **machine authentication** (already a P0) and a **documented event contract**, so it arrives close to free once machine auth lands.

Conversions are **per-recipient events** under [[ADR-103 — Provider Events Are Normalized Into Internal Events]] and feed signals normally, even though they arrive from the adopter's system rather than a provider — the one case where a blind channel produces a first-class signal.

**8. The platform records THAT a conversion happened; WHAT converted belongs to the CRM or the DWH.**
A conversion is not a click with a different name: it carries *what* converted, not only *that* it did, and structuring that depends entirely on the business — products, PDF downloads, bookings. Modelling "what" means modelling every adopter's business, which is unbounded and already assigned elsewhere by [[ADR-120 — CRM as Customer Source of Truth]] and [[ADR-124 — DWH Is Recommended but Not Mandatory]]. At most we carry an **opaque external reference** the adopter's own system resolves. The minimum that holds is *"clicked this and bought anything"* — enough for signals, since it yields the content, its categories, and a heavier contribution weight than a click. The trap worth naming: a conversion **value** looks like one nullable number but drags **currency, net-versus-gross and refunds** behind it, and a refunded conversion arguably has to be reversed. The honest minimum is the boolean; value belongs with the analytics phase.

**9. `SignalContributionDB` gains an explicit `channel` column, and it does not change the topic score.**
One append-only log read along two axes: **topic affinity** — sum over categories, ignoring channel, unchanged, because interest in hiking is interest in hiking wherever it was clicked — and **channel affinity** — sum over channels, ignoring category, new. The second is what makes [[ADR-160 — Channel Model and Composition]]'s forward consequence possible at all: the decision layer cannot choose a channel per recipient without knowing which channels that person engages with.

Two alternatives were checked and rejected on evidence. **Extending `contribution_type` values** (`click_email`, `tap_push`) crosses two orthogonal facts into one enum — five types × five channels is 25 values — and it breaks channel weighting, which wants a **grid** rather than a flat list; [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]] configures half-lives per contribution type, so it would also produce 25 half-lives where two independent axes are wanted. **Deriving channel from `event_id`** fails three ways: the path exists but is **five joins** — contribution to event to execution to send instance to snapshot to variant — on every read, in a layer designed around compute-on-read; `event_id` is **nullable**, since manually declared preferences have no event, so channel would return *unknowable* rather than *not applicable*; and ADR-132 **prunes**, keeping a bounded operational window locally with history in the DWH, so if executions are pruned on a different schedule than contributions, **old contributions lose their channel retroactively**, degrading silently over exactly the period worth analysing. A denormalised column is immune to all three.

**10. Channel weights extend the existing settings grid, and whether to weigh channels differently is the company's call.**
Same split as frequency numbers: numbers belong to the company, the mechanism to us. Default equal until there is data — a push tap is lower-friction than an email click and arguably signals less, but that is a guess without evidence. The two affinities also decay differently: topic interests shift over months, while "never opens email, always taps push" is a stabler fact. ADR-132 already makes half-lives configurable per type, so this needs no new mechanism.

## Consequences

### Positive
- A vendor's current limitation is never written into the architecture, so a platform that starts reporting per-recipient events needs a changed provider file and nothing else.
- Aggregate data cannot reach the signal layer, because the signal layer cannot read the table it lives in. The guarantee is structural rather than a rule people must remember.
- Aggregate results are kept and made useful in reporting rather than thrown away to protect the signal layer.
- Calling metrics "metrics" prevents the nullable-recipient column that would otherwise have been the obvious shortcut.
- Blind and delegated channels are not written off as feedback-free; the return path is named and it belongs to the adopter.
- Channel affinity becomes computable, which is the precondition for the engine ever choosing a channel per recipient — and topic scores are untouched while it happens.
- The channel column survives pruning, a nullable `event_id`, and the five joins that deriving it would have cost on every read.

### Negative
- **A denormalised column is the price** of immunity to pruning and joins: channel is written on every contribution and can in principle disagree with the event it came from.
- Two feedback paths now exist, with different tables, different consumers and different grain. Anyone writing a report must know which one they are in.
- Aggregate ingestion is refused rather than degraded when a provider misdeclares itself, so a misconfigured adapter fails loudly at the worst moment — deliberate, but it will look like an outage.
- Conversions record only that something was bought. An adopter who wants product-level analysis is sent to their own DWH.
- Default equal channel weights are a placeholder that nobody has data to tune yet.
- **Aggregate ingestion and display are not built in the POC**, so the analytics half of this decision is a recorded constraint rather than a working feature.

## Notes

- **Scope: aggregate ingestion and display are not POC.** Features are being cut, and this one moves cleanly into a future phase; it is prepared in the POC only if trivial, otherwise explained in the library. **The deliverable here is the recorded constraint, not code** — it costs nothing now and stops phase 2 taking the nullable-column shortcut.
- **Direction, explicitly not phase 1:** aggregate results should eventually inform decisions at **segment level** — using how a social post performed to shape the next one. That is genuinely valuable and genuinely different from per-recipient signals. Parked.
- **The five deferrals from this interview form a coherent phase-2 set:** volume capping, cross-channel follow-up audiences and letter integration (all [[ADR-161 — Channel Execution Shapes]]), aggregate ingestion and display, and aggregate-informed segment decisions.
- **Returned letters are an exception explicitly not designed around.** "Address doesn't exist" is per-recipient, but it is unlike an email or push non-deliverable in two ways: it arrives **days later** as an asynchronous event rather than as an API response to the send, and whether it arrives **at all** depends both on the provider offering it and on there being an API path rather than a physical box of returned mail. It would likely need its own reconciliation process. Doubly deferred, since letter is already out of POC scope; the bounce vocabulary can absorb it if and when a provider reports it.
- **Amendment another record needs, not made here.** [[ADR-103 — Provider Events Are Normalized Into Internal Events]] needs a **scope clarification** stating that it governs per-recipient events and that an event without a recipient is refused at ingestion rather than stored with a null. That is a dated addendum, not a superseding decision.

## Related ADRs

### Depends On
- [[ADR-101 — Provider Capabilities Are Explicit]]
- [[ADR-103 — Provider Events Are Normalized Into Internal Events]]
- [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]
- [[ADR-160 — Channel Model and Composition]]
- [[ADR-161 — Channel Execution Shapes]]

### Referenced By
- [[ADR-055 — Separate Delivery Execution from Engagement Events]]
- [[ADR-056 — Engagement Events as Foundation for Automation]]
- [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]
- [[ADR-110 — Insight Layer Transforms Events Into Signals]]
- [[ADR-111 — Decision Layer Consumes Signals, Not Raw Events]]
- [[ADR-112 — Signals Use Time-Based Decay]]
- [[ADR-113 — Separate Operational and Historical Signals]]
- [[ADR-120 — CRM as Customer Source of Truth]]
- [[ADR-124 — DWH Is Recommended but Not Mandatory]]
- [[ADR-129 — Correlate Provider Events to Delivery Executions]]
