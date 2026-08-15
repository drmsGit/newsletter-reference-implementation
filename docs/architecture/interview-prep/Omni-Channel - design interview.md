---
type: interview-prep
topic:
  - architecture
  - delivery
  - channels
  - design
created: 2026-08-12
status: open
---

> **Status (2026-08-12): idea captured, interview deferred by the user.**
> **Update — interview STARTED 2026-08-07 (see Cluster 1 resolutions below).**
> Everything not marked with a **Resolution** line is still undecided. No code
> changes until the clusters that govern them are closed.

# Omni-Channel — design interview (forward-looking)

Like [[AI Layer - design interview]], this file gathers the **decisions needed
before writing ADRs**, rather than reviewing implemented code.

## Why this came up

Email alone is not enough. The architecture is named and shaped for newsletters,
but the real requirement is **content management and orchestration for any
communication channel an adopter can reach through an API** — a letter shop, a
push service, a messaging platform, a paid-social ad account. Not all of it at
once, and not all of it in the POC. The question is whether the *structure* can
absorb new channels cheaply, or whether each one is a fight.

Market read behind it (user, 2026-08-12): most customers do **not** do
omni-channel today, and the reason is that it is too complex in the typical SaaS
platforms — not that they don't want it. That makes it the sharpest expression of
**pillar 3** (off-the-shelf platforms don't fit the team's workflow), and the
capability model means an adopter could connect a *local* letter shop or a
regional messaging service — the long tail no SaaS vendor will ever integrate.
For the Mittelstand segment that is a stronger differentiator than anything
currently in the business briefing.

Concrete targets named: plan a **social post / paid social campaign**, plan a
**letter** instead of an email, plan a **push notification** instead of an email.

---

## Established up front (settled 2026-08-12 — don't re-litigate)

1. **Per-channel variants under a shared campaign.** Not one neutral composition
   that each channel renders its own way. A social ad is genuinely not the same
   artifact as a newsletter, and forcing one composition to serve both produces
   lowest-common-denominator content.
2. **Channel selection is the manager's choice, never forced.** They create a
   campaign, create a variant, select a channel, prepare that channel. A campaign
   is not required to cover every channel.
3. **Organic / broadcast social is out of scope.** The interest is in
   **personalised paid social** — build a target group, hand it to
   Meta/TikTok/etc., have it delivered one-to-one. Organic posting reaches the
   whole audience and is not what companies are buying.
4. **Direction of travel: smaller and smaller groups.** Long-term the platform
   should make it easy to target small groups, down to one-to-one, on every
   channel where that is technically possible.
5. **The shared core stays shared.** Content, decision, audience, signal and
   override layers are not channel-specific and must not become so.

### Why point 3 matters structurally

Dropping organic removes the worst break. A broadcast post has **no recipient** —
which would have forced `DeliveryExecutionDB.recipient_id` to become nullable and
left campaign-level and per-recipient sends sharing an execution table with
incompatible meanings. Paid social with custom audiences is still *addressed*,
merely **delegated**. The execution model survives intact.

---

## Where the architecture already stands

Roughly **80% is already channel-neutral**, and that is a consequence of existing
decisions rather than luck.

### Neutral today — no change expected

| Layer | Why it already generalises |
|---|---|
| Content | `ContentRecordDB.content` is JSON + categories + versions (`content/db_models.py:6`). [[ADR-012 — Content Records Represent Communication Units]] defines a record as a *reusable communication unit*, deliberately **not** "an email". |
| Decision | Slots, strategies, candidate filters and `DecisionResolutionDB` resolve **content records**. Nothing in the layer knows what an email is. |
| Signals | `(recipient × category × contribution)` with decay-on-read ([[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]). Neutral in shape; only the *vocabulary* (click, open) is email-derived. |
| Audience | `AudienceGroupDB` + rule blocks + members (`audience/db_models.py:6`). [[ADR-052 — Delivery Layer Supports Multiple Audience Resolution Modes]] already blesses references, queries and explicit lists. |
| Override, composition tree | `ModuleInstanceDB` is a generic `(module_type, position, content_record_id, decision_slot_id, module_data)` structure. |

[[ADR-022 — Delivery Type Is Independent From Composition]] already separates
delivery type from composition, and [[ADR-100 — Provider Layer as Send and Feedback Adapter]] / [[ADR-101 — Provider Capabilities Are Explicit]] already make
the provider a capability-declaring adapter. The seams exist.

### Email-bound — five places, all in a thin band at the outbound end

1. **The provider contract.** `send(recipient_email, subject, html) -> SendResult`
   (`delivery/providers/base.py:15`). Three email concepts as positional
   arguments. A letter has no subject; a paid-social audience has no single
   address.
2. **`VariantDB.subject` / `VariantDB.preheader`** as first-class columns
   (`campaigns/db_models.py:32`).
3. **Rendering is HTML-only.** `render_variant_html()`, and the snapshot schema
   says so in its column names: `html_storage_type`, `html_location`, `html_size`
   (`snapshots/db_models.py:12`). `render_context` is already neutral.
4. **`email_modules`** — the module registry is named and shaped for MJML→HTML
   ([[ADR-131 — Email Module Templates Use MJML as Source Format]]).
5. **Consent is a single column** and `email` is the only address
   (`recipients/db_models.py:11`, `:20`).

Individually all small. This is a restructure of one band, not a rewrite — **if
it happens before more surface is built on the email assumptions.**

---

## Three execution shapes

| Shape | Channels | Who controls delivery | Personalisation granularity | Feedback |
|---|---|---|---|---|
| **Addressed** | email, push, SMS, WhatsApp, letter | Platform — one artifact per recipient, handed to the provider with an address | Per recipient | Per recipient |
| **Audience-delegated** | paid social (Meta, TikTok, …) | **Ad platform** — platform supplies an audience membership list + creative(s); the platform decides timing, frequency, often which creative | Per segment | Aggregate (see below) |
| ~~Broadcast~~ | ~~organic social~~ | — | — | — |

Audience-delegated needs a **different verb, not a different `send()`** — roughly
`sync_audience(group, identifiers)` plus `attach_creative(audience, artifact)`.
Personalisation moves from per-recipient to per-segment: *N* audiences × *N*
creatives, with the decision layer running at segment level. That is still real
personalisation, and it is the distinction the strategy registry already draws
between `top_score` and `recipient_top_score`.

### Constraints on audience-delegated (design around these, don't discover them)

- **Identifiers go one-way.** Hashed email/phone is uploaded; the platform never
  reports back who matched.
- **Match rates are partial.** An audience of 500 reaches materially fewer.
- **Minimum audience sizes are enforced by the ad platforms.** This directly
  limits *Established #4*: one-to-one works on email, push, SMS and letter; it
  **does not work on paid social**, where small audiences are throttled or
  refused. A channel should be able to *declare* its minimum addressable-group
  size as a capability (extending [[ADR-101 — Provider Capabilities Are Explicit]]) so the UI warns instead of the send failing silently.
- **Feedback is aggregate — this is the honest answer to "how do we get
  interaction back?"** At person level, mostly you don't. Impressions, clicks and
  conversions arrive per audience+creative and **must not** be attributed down to
  individuals — doing so would corrupt the per-recipient signal layer, which is
  precisely the thing that makes the decision layer trustworthy. The one real
  per-recipient path is the **adopter's own site**: a conversion pixel/API firing
  back with their identifier.
- **Consent is sharper than for email.** Uploading a customer list to an ad
  platform is a transfer to a third party, and German DPAs have taken a
  restrictive line on exactly this (the Bavarian authority's Facebook Custom
  Audiences decision is the usual reference — **verify current status with
  counsel; not settled from our side**). Architecturally: consent is not merely
  per-channel but **per-channel-and-purpose** — "may I email you" ≠ "may I upload
  your hashed address to an ad platform." This fits the [[ADR-144 — AI Data and Model Governance]] stance: we don't make the legal determination, we make the
  model granular enough that the adopter can encode whatever their counsel says.

---

## Sketch of the restructure (not decided — input to the interview)

- **`DeliveryProvider` → `ChannelProvider`**, with `send(target, payload)` where
  target is channel-resolved (address / device token / postal address / handle /
  hashed-list) and payload is the channel's artifact. Generalise the ADR-101
  capability declaration from email capabilities to **channel** capabilities: max
  payload length, rich media, scheduling, per-recipient personalisation,
  execution shape, minimum group size, feedback events emitted.
- **Renderer registry keyed by channel**, using the same auto-registering plugin
  idiom as `decision/strategies/` — the pattern already trusted and already
  pointed at in the playbook.
- **Channel on the variant.** Consistent with [[ADR-021 — Variants Are Human Created Versions]]: an email version and a push version are both deliberate,
  reviewable versions, so no new concept is introduced and campaign coverage is
  derived. **Known cost:** variant then carries two meanings at once (A/B version
  *and* channel expression), which gets awkward at "Push A / Push B". The
  alternative — a channel-plan level between campaign and variant — makes "what
  channels is this campaign on" first-class at the price of a new concept. **Open
  fork, Cluster 1.**
- **Snapshot `html_*` → `artifact_*` + media type.** Rename plus migration.
- **`email_modules` → `modules`**, with channel in the manifest; MJML becomes the
  *email renderer*, not the module system.
- **Coverage, not constraint.** A campaign shows which channels have a prepared
  variant and warns at send time; it never blocks. Same idiom already chosen for
  system mail — *allow it, default safely, warn loudly*. Forcing every channel
  would be pillar 3's own failure mode: the platform imposing a workflow.

---

## Ripple effects to weigh when scheduling this

- **Overlaps the open P0 consent bug.** The P0 (a recipient can be mailed after
  opting out when the audience was frozen) lives in the same code path that
  per-channel consent would restructure. Running Cluster 4 **before** fixing the
  P0 means fixing it once, in the right shape, instead of twice.
- **The React/Node frontend has not started.** Doing this first lets the manager
  UI be designed against channel-shaped variants from day one, instead of
  retrofitting a second codebase. This is the strongest timing argument.
- **Mode A generalises cleanly.** "Suggest subject & preheader" becomes "suggest
  the channel's headline fields" — push title, social hook, letter subject — but
  only if the variant model gets there first ([[ADR-141 — In-App Assistive AI Actions]]).
- **Naming.** [[ADR-001 — Newsletter Architecture Boundaries]] scopes the core to
  "newsletter-specific responsibilities". If channels generalise, that ADR needs
  revisiting — likely a superseding boundary ADR rather than an edit.
- **Consent model.** [[ADR-122 — Minimal Consent Model Required]] and [[ADR-121 — Minimal Recipient Model]] both assume one address and one consent state.

---

## Planned interview — five clusters

Expected to produce roughly a **160-block** of ADRs. Nothing here is answered
yet; `Lean:` marks where a steer already exists from the 2026-08-12 conversation.

### Cluster 1 — Channel model & composition  ✅ CLOSED 2026-08-07
1. ✅ **Is channel a contract enforced at authoring time, or a transformation
   applied at rendering time?** Does picking "push" restrict the manager to
   push-legal modules and a short payload, or does the variant stay a free
   composition that the channel renderer degrades as best it can? *Email went the
   first way via MJML — does that generalise?*
   **Resolution (2026-08-07): a contract at authoring time.** Email modules stay
   email-only. A manager who writes 600 characters and learns at send time that
   push truncated to 178 has been failed by the tool, and authoring-time
   constraints make "ready on push" a checkable fact rather than a hope.
   **Established with it:** push carries **no HTML** — APNs, FCM and Web Push all
   take structured fields (`title`, `body`, `image`, link) inside a ~4 KB budget,
   and the receiving OS does all rendering, so a push renderer fills fields and
   has no layout job. **A push is one message, not a composition**, so the module
   tree needs nothing new: one `ModuleInstanceDB` of type `push` at position 0,
   pointing at a content record *or a decision slot* (which is how personalised
   push comes free). The channel declares **max one module** as an ADR-101
   capability rather than the composition code special-casing it.
   **Channel readiness is a property of the content record** — "each record can
   be pushed as long as it is prepared for the push channel" (user). Push fields
   are **separate and required**, never derived from email fields: deriving a
   40-character push title from a 60-character email headline at render time *is*
   the rendering-time transformation this question rejected. Consequences that
   fall out: decision slots filter candidates to channel-ready records through
   the existing `candidate_filter_fields`, so the engine can never pick content a
   channel cannot carry; the override layer needs no change; and the only real
   cost — more fields to author — is precisely what Mode A removes, since
   "suggest the push headline from this record" is the same shape as
   suggest-subject, with the confirmed value **stored as a real field** rather
   than derived at send time.
2. ✅ Channel on the variant, or a channel-plan level between campaign and variant?
   *Lean: on the variant.*
   **Resolution (2026-08-07): a `channel` attribute on the variant.** A campaign
   ("Hiking") carries one or more email variants, push variants, paid-social
   variants. The rejected alternative — a channel-plan level between campaign and
   variant — would have made "which channels is this campaign running on" *stored
   intent* rather than derived, and given channel-level settings (a different
   send time for push than email) a home; not worth a new concept in the model,
   the UI and the playbook. Consistent with [[ADR-021 — Variants Are Human Created Versions]]: a push version is a deliberate human-created version.
   **Known cost accepted:** a variant now carries two meanings at once, A/B
   version *and* channel expression, which reads awkwardly at "Push A / Push B".
   Judged a **display** concern — the UI groups by channel — not a model one.
   **The principle behind the rejection, and it outranks the mechanics (user,
   2026-08-07):** *"it's not about the channel, it's about the topic — the channel
   is just what the recipient might like best."* A mid-layer that groups by
   channel would encode "we organise our work by channel" into the model, which
   is pillar 3's own failure mode: the platform imposing a workflow. The campaign
   is the **topic**; the channel is a delivery preference, not a structural
   division of the work. Grouping is therefore UX.
   **Forward consequence to watch (not decided):** if the channel is "what the
   recipient might like best", then channel selection is eventually a *decision*
   — the engine choosing per recipient which channel, and therefore which
   variant, they receive. That would make channel preference a signal dimension.
   Relevant to Clusters 2 and 5; do not design it away here.
3. ✅ What does "registering a channel" mean concretely — config, a manifest, a
   provider adapter, or all three?
   **Resolution (2026-08-07): a channel manifest plus a provider adapter — two
   files, no config step.** The manifest *is the channel* (fields and their
   limits, max modules, execution shape, capabilities) and is true for everyone;
   the adapter *is the vendor* (APNs, FCM, OneSignal) — the same split
   [[ADR-100 — Provider Layer as Send and Feedback Adapter]] already draws, so a
   company can change vendor without changing what "push" means. No separate
   registry or settings row: decision strategies already auto-register from a
   dropped `.py`, email modules from `name.json` + `name.html`, and a third
   pattern needing registration in several places is the one that eventually gets
   registered in two.
   **The criterion this serves, in the user's words (2026-08-07):** *"a framework
   that enables a company to get basic functions rather in a weekend than in half
   a year — even if they miss the good stuff, they get a feeling of fast
   output."* **Time-to-first-output beats completeness**, and that should settle
   later arguments about how much a manifest must declare: if a requirement slows
   the weekend path, it is optional or it is defaulted.
   **Loose end:** whether a deployment can *disable* a channel it is not licensed
   for without deleting files. Governance, same shape as ADR-140's kill switch and
   the governed model list, where availability is code and selection is a
   setting. Not decided.
4. ✅ Campaign coverage: derived view, or stored intent ("this campaign is meant to
   run on email + push")? *Lean: warn, never block.*
   **Resolution (2026-08-07): derived, and purely descriptive. No stored intent,
   and — correcting the lean — no coverage warning either.** Coverage is just
   what exists: email + push variants means the campaign is email/push; only a
   social variant means it is social. Stored intent is *"unnecessary
   bureaucracy"* (user) — a manager will think "this is meant for push", but they
   need to get **past** that thought, not file it. It would also put channel back
   into the campaign's structure through the side door, against Q2's principle,
   and create a drift class where intent and reality disagree with nobody
   clearing the stale state.
   **The lean was superseded because its premise was wrong.** *"A **variant** is
   planned and sent, not the campaign"* (user) — there is no campaign schedule
   that launches every variant in it. Each variant is planned and sent
   separately, which the code already reflects: a `SendInstanceDB` hangs off a
   snapshot of one variant. So there is no campaign-level send event at which to
   warn that "push has no variant", and nothing to warn about — nobody asked to
   send push. A manager (or AI) launches a variant when they want that channel.
   **Consequence for Cluster 2 Q9, and it sharpens it:** because variants are
   planned and sent independently, **nothing currently prevents a recipient
   receiving both the email and the push variant of the same campaign.**
   Cross-channel frequency capping is therefore not a refinement — it is the only
   thing standing between this model and double-contacting people.
   **Also reinforces the Q2 forward consequence:** *"in the end they want AI more
   involved and it will select the one most suitable"* — i.e. the channel/variant
   choice becomes a decision-layer output.
5. ✅ Does a variant's channel ever change after creation, or is it fixed at
   creation?
   **Resolution (2026-08-07): fixed at creation.** Fell out of Q2 rather than
   being argued separately — switching an email variant to push would invalidate
   its modules, its content-readiness and its renderer simultaneously. Changing
   channel means creating a new variant.

### Cluster 2 — Execution shapes
6. ✅ How are addressed and audience-delegated modelled — one provider interface
   with optional methods, two interfaces, or a capability flag?
   **Resolution (2026-08-07): as many interfaces as the execution shapes
   genuinely need — two, three, more — never one with optional methods.**
   *"Putting everything in one interface usually means compromises being
   necessary, and that's mostly a lack of comfort"* (user). One interface with
   methods that raise is a capability system whose capabilities are discovered by
   calling and catching, which is the thing [[ADR-101 — Provider Capabilities Are Explicit]] exists to prevent; and a bare capability flag says *whether*
   something is supported, not *what to call*, when the signature is the thing
   that differs.
   **Interfaces are keyed by what the provider needs, not by channel** — the two
   do not map one-to-one. Provisional grouping to start from: **addressed,
   per-message API** (email, push, SMS, WhatsApp — one contract, payload type
   declared by the manifest); **addressed, batch handoff** (letter — a produced
   file handed to a letter shop, a genuinely different verb, see Q10); and
   **audience-delegated** (paid social — `sync_audience` + `attach_creative`).
   Three channels can share one contract; one channel can need its own.
   **Design criterion, and it governs the rest of this cluster (user):** the
   interfaces must be *"quick to create, edit, test and launch"*, and a company is
   expected to adapt them to its own providers — that is not too much to ask of an
   adopter, and it is the same weekend-not-half-a-year standard set in Q3.
   **Concrete consequence of "quick to test": every interface ships a mock
   implementation**, as `MockProvider` and `MockAIProvider` already do. That is
   how the test suite stays runnable without credentials, and the idiom exists
   twice already — make it a rule rather than a habit.
   **Typed contracts also buy the fail-closed property for free:** code that only
   knows how to address recipients cannot be handed a delegated provider, because
   the type does not fit.
7. ✅ What does a `DeliveryExecutionDB` row *mean* for a delegated send, where the
   platform never learns who was reached?
   **Resolution (2026-08-07): the row records a TRANSFER, not a delivery.** Per-
   recipient rows are still created, with a status vocabulary that does not lie:
   `submitted`, meaning "included in the uploaded list", never progressing to
   `sent` / `delivered` / `opened`, none of which are knowable. Match outcomes are
   unknown by construction, so there is no "not matched" state either — the
   honest terminal state is `submitted`.
   **Why keep per-recipient rows at all, when delivery is unknowable — three
   reasons, none of them delivery tracking.** (1) **Uploading a hashed identifier
   to an ad platform is a transfer of that person's data to a third party**, which
   is a processing act needing an Art. 30 record. (2) **Erasure** — when someone
   asks to be forgotten you must know which platforms hold them, or the erasure
   stops at our boundary, the same loophole already flagged for the DWH in
   [[ADR-154 — Erasure and Retention]]. (3) **Consent evidence**, per person, for
   a transfer whose lawful basis is sharper than email's.
   **The same applies to letters** (user): handed off, never confirmed read.
   **Future-proofing (user):** if Meta or another platform later exposes delivery
   tracking, the row is already there to enrich — the state is accepted, not a
   placeholder.
   **Second use, and it is a decision-layer input (user):** transfer records help
   answer *"has this recipient already been given this content?"* — *"we might
   just assume: if transferred, count as has seen."* Recorded explicitly as an
   **assumption**, because match rates are partial: it will suppress content from
   people who never actually saw it. That trade is deliberately conservative on
   repetition (never spam) at the cost of reach (may withhold).
   **Critical boundary on that use:** it feeds **suppression/anti-repetition
   only**, never the signal layer. Inferring *interest* from a transfer would
   fabricate preference data out of an upload — the same corruption Cluster 5 Q22
   guards against from the aggregate side.
   **Engagement can still return, but through our own domain, not the channel
   (user):** a link in the letter or the ad carries our identifier, and the
   adopter's own site fires it back. Generalises to a rule — **for any blind or
   delegated channel the return path is the adopter's property, never the
   platform.**
   **Cost:** status vocabulary now varies by execution shape, so anything
   aggregating statuses must know the shape. Directly touches the open P1 bug
   where a send instance reports `sent` unconditionally — that fix must handle a
   shape whose executions never reach `sent` at all.
8. ✅ Which ADR-101 capabilities become channel capabilities, and which stay
   provider-specific?
   **Resolution (2026-08-07): ALL capabilities live in the provider file. There is
   no channel capability declaration.** [[ADR-101 — Provider Capabilities Are Explicit]] is **extended** from email providers to channel providers — same
   ADR, wider scope, no second system. *"Every channel should allow feedback; if
   it gets one from the provider depends on the provider"* (user), and the letter
   case proves it: whether a returned letter comes back to you is a fact about the
   **letter shop**, not about "letter" — exactly as an ESP relay reports bounces
   while a generic SMTP host does not, within one channel.
   **A channel-level capability file was proposed and rejected.** It would only
   help if kept current with "everything the channel can possibly do", and *"who
   will do this"* (user) — it has **no owner** and goes stale the moment a vendor
   ships something, whereas a provider file describes one thing its author
   actually knows. Duplication across providers is accepted as the cheaper
   failure. The earlier suggestion of channel-as-ceiling / provider-as-actual with
   an intersection rule is **withdrawn** as over-engineering.
   **What is NOT a capability, and does need a home:** the **authoring contract**
   from Q1 exists *before* a provider is chosen — a manager picks a channel, not a
   vendor, and may not have selected one at all. "Push title, 40 characters" comes
   from the OS notification surface, not from APNs vs FCM vs OneSignal. If it
   lived in adapters, "push-ready" would mean *ready for which provider?* and
   swapping vendor could silently change it.
   **It already has a home: the module manifest.** Email does this today —
   `name.json` declares the fields, `name.html` renders them. Push is one module
   type whose manifest declares `title`/`body`/`image`/`link` and their lengths.
   No new file type. So: **provider `.py` = capabilities · module manifest =
   fields and limits · channel = an attribute on the variant plus which manifests
   it accepts.** The only genuinely channel-level fact left is **cardinality**
   ("a push variant has exactly one module").
   **Catalogue readiness is "push fields not empty" — not a length or provider
   check (user).** The catalogue stays independent of provider configuration.
   **Nuance recorded because the fallback reasoning has a hole:** "it will fail and
   we will notice" holds for the **4 KB total payload**, which APNs and FCM reject
   outright, but **not for title/body length** — those are accepted and the
   *device* truncates the display, so nobody is ever told. Hence lengths belong in
   the manifest and are enforced by the **editor as an input constraint**
   (`maxlength`), not as a validation gate and not from `provider.py`.
   **Preferred handling (user, 2026-08-07): a frontend preview showing potential
   truncation**, rather than blocking. Truncation is not a real problem once it
   is *visible* — showing the manager what the notification will actually look
   like solves it without a gate, and matches the "warn, never block" idiom used
   for system mail and channel coverage. Same surface the letter and social
   previews will need.
9. Does the platform own frequency capping across channels, or is that per
   channel? (Relevant the moment a recipient is reachable three ways.)
10. Letter specifically: batch-file handoff to a letter shop rather than
    per-message API — does that fit `send()`, or is it a third shape?

### Cluster 3 — Rendering & modules
11. What replaces `subject` / `preheader` — channel-typed JSON on the variant, or
    a per-channel side table?
12. Renderer registry: what is the contract, and what does a renderer receive?
13. What does [[ADR-063 — Rendering Parity Over Rendering Implementation]] mean
    across channels, where parity between an email and a letter is not even
    definable?
14. Do module manifests gain a channel dimension, or does each channel get its
    own module namespace?
15. Snapshot: one artifact per execution, or can one execution carry several
    (e.g. letter PDF + a print-ready address file)? Touches [[ADR-062 — Snapshot Stores Final Render State]] and [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]].

### Cluster 4 — Identity, consent & permission
16. Consent as rows per `(recipient, channel, purpose, status, source, timestamp)`
    — confirm the shape. *Lean: rows, not columns — the same idiom already used
    for roles in the security base.*
17. Addressability per channel: where do device tokens, postal addresses, handles
    and hashed identifiers live? Extends [[ADR-121 — Minimal Recipient Model]].
18. Is "may I transfer your hashed identifier to an ad platform" a consent
    *purpose*, a separate consent *type*, or out of scope for the platform?
19. How does CRM consent sync carry per-channel state? (`ConsentSyncLogDB` today
    syncs a single status.)
20. Does the send-time consent gate become per-channel, and what happens when a
    campaign spans channels with different consent coverage?

### Cluster 5 — Feedback & signals
21. Which channels return per-recipient events, which return aggregate — and how
    is that declared rather than assumed?
22. **How is aggregate feedback kept out of the per-recipient signal layer?**
    Attributing segment numbers to individuals would corrupt the decision layer's
    auditability.
23. What does [[ADR-103 — Provider Events Are Normalized Into Internal Events]]
    normalisation mean when an event has no recipient?
24. Is the conversion-API path (adopter's own site fires back with their
    identifier) in scope for the POC, or a documented extension point?
25. Does the signal layer need a channel dimension — is a click in email the same
    signal as a tap in push? Touches [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]].

---

## Related

- [[MOC - Interview Prep Baseline]]
- [[AI Layer - design interview]]
- [[MOC - Delivery Architecture]]
- [[MOC - Provider Architecture]]
- [[ADR-002 — API First Architecture]]
- [[ADR-004 — Privacy Operations as a First-Class Architectural Concern]]
- [[ADR-050 — Delivery Layer is Part of the Reference Architecture]]
- [[ADR-051 — Delivery Package Includes More Than HTML]]
- [[ADR-054 — Use Internal Recipient Identifiers]]
- [[ADR-104 — Audience Ownership Stays Outside Provider]]
- [[ADR-105 — Provider-Specific Data Must Not Be Architecture-Critical]]
