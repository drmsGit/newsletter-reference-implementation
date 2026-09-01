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

> **Status: interview CLOSED 2026-08-07 — all five clusters, 25/25 questions
> answered.** Every question carries a **Resolution** line. Next step is writing
> the ADRs (expected ~160 block); no code changes before then.

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

### Cluster 2 — Execution shapes  ✅ CLOSED 2026-08-07
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
9. ✅ Does the platform own frequency capping across channels, or is that per
   channel? (Relevant the moment a recipient is reachable three ways.)
   **Resolution (2026-08-07): the platform owns it, because nothing else can** —
   per-channel capping is structurally incapable of the thing that matters, since
   each channel would faithfully cap itself at three and the recipient would get
   nine. Only the platform sees across channels, and it already holds the data.
   **Volume capping is NOT in the POC (user)** — an advanced feature. **The
   *concept* should be explained in the playbook**, which is the right home for a
   capability an adopter will need before we build it.
   **Cross-channel repetition is NOT suppressed — the blanket rule proposed in
   the interview was wrong and the user corrected it.** *"A person that gets a
   topic as a newsletter might be allowed to get it via push as well — for example
   as a reminder because the email wasn't engaged with."* That is not an accident
   to prevent, it is one of the more valuable things omni-channel enables.
   **So the mechanism is audience composition, not a cap.** "Push the topic to
   people who received the email variant and did not click within 48 hours" is an
   **audience rule**, expressible as an `AudienceRuleBlockDB` predicate over prior
   deliveries and engagement — which is exactly the parked **engagement-driven
   audiences** item in `docs/backlog.md` (use case 2, gated behind the automation
   workstream). Cross-channel follow-up therefore needs *that* item, not a
   frequency feature.
   **What remains a genuine risk is the *accidental* overlap** — two variants of
   one campaign planned to overlapping audiences with no deliberate intent.
   Handled by **surfacing the fact at variant plan time** ("380 of these 500
   already received the email variant"), never by blocking, since the manager may
   want exactly that. **Note this does not contradict Q4:** Q4 removed a
   *campaign-level* warning because no campaign-level send event exists; this is
   at variant plan time, which is a real moment.
   **Delegated channels are a partial exception, to declare rather than pretend:**
   for paid social the platform controls *inclusion in the audience*, not delivery
   frequency — the ad platform decides impressions.
   **Numbers belong to the company, the mechanism to us** — same split as
   retention periods and the AI spend cap.
   **Concrete gap found while checking:** `DeliveryExecutionDB` has `created_at`
   (written at *plan* time) and `updated_at` (bumped by any later status change)
   but **no `sent_at`**. Any capping or overlap check needs "when did this
   actually go out", and `updated_at` does not reliably mean that. The same
   missing timestamp weakens the open P1 send-status work.
10. ✅ Letter specifically: batch-file handoff to a letter shop rather than
    per-message API — does that fit `send()`, or is it a third shape?
    **Resolution (2026-08-07): not a third interface. Letter uses the addressed
    interface, and `finalize()` stays in the contract as designed.** Batch versus
    per-message is a **provider capability**, not a channel property — some letter
    services take a per-message API call, others want a CSV plus a PDF bundle over
    SFTP, and that is a difference *between vendors of one channel*, which is
    exactly the Q8 discriminator. The platform still calls `send()` per recipient;
    a batch adapter buffers and flushes on `finalize()`. Per-message providers
    implement it as a no-op — a small ceremony everyone pays so one case works,
    against a third interface that would be 90% identical.
    **Status semantics come from Q7, not from a new shape:** a batch yields one
    result for the handoff, not per recipient, so executions carry `submitted`
    until — *if* — the shop reports back, with optional later reconciliation.
    So the prep's third execution shape dissolves into an existing one; **two
    interfaces, not three.**
    **Scope (user): letter is an advanced feature and highly provider-dependent.**
    The POC should **show that it is possible**, not ship an integration — a real
    letter-shop connection will be heavily customised per company. The deliverable
    is a **library article**: *"if you need batch instead of per message, here is
    how"*, the same posture as the swap-send-provider and webhook guides. In the
    POC that means the interface supports it and a **mock batch provider**
    demonstrates the flush path, which Q6's "every interface ships a mock" rule
    already requires.

### Cluster 3 — Rendering & modules  ✅ CLOSED 2026-08-07
11. ✅ What replaces `subject` / `preheader` — channel-typed JSON on the variant, or
    a per-channel side table?
    **Resolution (2026-08-07): neither — the variant holds no channel fields at
    all. Subject and preheader become module fields, declared in a manifest.**
    Q1 put the authoring contract in the module manifest and Q8 confirmed fields
    and limits live there; subject and preheader are simply *fields of an email*.
    So they move into the composition — a `header` module for email whose
    manifest declares them, at position 0 — exactly as push's single module
    declares `title`/`body`/`image`/`link`. Nothing on `VariantDB` is
    channel-shaped.
    **Both offered options were rejected for the same reason:** typed JSON on the
    variant and a per-channel side table are each a *second* place where channel
    fields live, beside the manifests — and the failure mode is the familiar one,
    where one gets updated and the other does not.
    **Three things it buys.** **Overrides work unchanged** — the override layer
    edits module fields, so a personalised subject line comes free instead of
    needing its own mechanism, which it cannot have today because subject is not a
    module field. **Mode A generalises without a special case** — "suggest subject
    & preheader" currently reaches into variant columns; as module fields the same
    task shape covers a push title or a letter salutation
    ([[ADR-141 — In-App Assistive AI Actions]]). And **no third pattern** to keep
    in step.
    **Honest costs:** a migration moving two columns into module data; the send
    path reads `variant.subject` directly today and would read from the
    composition instead — the same code the code review's P1-04 finding already
    says needs rework; and "what is the subject of this variant" becomes a lookup
    rather than a column, which matters for list views and sorting.
12. ✅ Renderer registry: what is the contract, and what does a renderer receive?
    **Resolution (2026-08-07): `render(composition, merge_context) -> Artifact`,
    receiving fully resolved content.** Decision slots resolved, overrides
    applied, content versions pinned *before* the renderer sees anything — **it
    formats, it never decides**. Keeps editorial and personalisation logic in the
    decision layer where it stays explainable, matches Q1's finding that a push
    renderer fills fields and has no layout job, and is
    [[ADR-060 — Rendering as Independent Layer]] taken seriously.
    **The return type is the crux:** email returns HTML, push a field dict, letter
    a PDF, social creative fields plus media — so the contract cannot be `-> str`.
    It returns an **`Artifact`**: media type, payload, size, and a **content hash,
    carried from the start** (user). The hash is not decoration — it is what the
    code review's P1-04 finding asks for, an immutable per-delivery package a
    provider request can be traced back to, so that *"snapshot reviewed"* actually
    proves *"content sent"*. This is also where the prep's `html_* → artifact_* +
    media type` rename lands.
    **Registry keyed by channel, auto-registering** — the `decision/strategies/`
    idiom and the Q3 "drop a file" standard.
    **One renderer per channel, not per provider.** The artifact belongs to the
    channel; the provider transmits it. A push artifact is the same whether FCM or
    OneSignal carries it, which keeps the Q8 split intact and means swapping
    vendor never changes what gets rendered.
    **Email note:** MJML compilation stays in the frontend layer per
    [[ADR-131 — Email Module Templates Use MJML as Source Format]], so the email
    renderer assembles already-compiled module HTML and inlines CSS — it does not
    gain a compiler.
13. ✅ What does [[ADR-063 — Rendering Parity Over Rendering Implementation]] mean
    across channels, where parity between an email and a letter is not even
    definable?
    **Resolution (2026-08-07): the question dissolves — ADR-063 was never a
    cross-channel claim.** Reread to check rather than assumed: its parity is
    between **preview, final rendering and snapshot** — three *render contexts* of
    one thing, permitting browser-friendly markup in the builder and nested tables
    in the final email so long as they represent the same intended output. That is
    a **within-channel** guarantee and it generalises unchanged: for push, a mock
    notification card in the UI versus a JSON payload; for letter, an on-screen
    preview versus a print-ready PDF.
    **Cross-channel sameness was not lost, it was rejected in Q1** — per-channel
    variants exist precisely because a social ad is not a squeezed newsletter. So
    "parity between an email and a letter" was never a goal.
    **What improves, and what honestly does not:** the Q12 content hash makes the
    **snapshot ↔ sent** half checkable for the first time, which is exactly the
    code review's P1-04 gap. But **preview ↔ final stays a testing concern**,
    because ADR-063 deliberately permits different implementations there, so those
    artifacts differ by design and their hashes will not match. Worth stating
    rather than overclaiming what the hash buys.
    **Change needed: wording only.** "The same intended newsletter output" becomes
    "the same intended channel artifact" — an amendment, not a superseding
    decision.
14. ✅ Do module manifests gain a channel dimension, or does each channel get its
    own module namespace?
    **Resolution (2026-08-07): both, plus an assertion.** Directory per channel
    (`modules/email/`, `modules/push/`) **and** the channel declared in the
    manifest, with the loader failing at startup if they disagree.
    **Namespace** because name collisions are real — "hero" is natural in email,
    letter and social, and flat organisation just re-implements namespacing in
    filenames. It also makes "drop a file" literal and keeps a designer working on
    email from scrolling past push modules. **Declaration** because a manifest
    read on its own should say what it is for; location-only makes the file
    meaningless outside its directory, which bites in review, docs and error
    messages. **The assertion matters more than either:** a misfiled manifest
    would otherwise surface as a manager being offered a module that cannot
    render. Same fail-closed idiom as unmapped write routes and the webhook
    secret.
    **Renames:** `app/email_modules/` → `app/modules/`, `storage/email_modules/`
    → `storage/modules/email/`, registry loads per channel.
    [[ADR-131 — Email Module Templates Use MJML as Source Format]] stays intact —
    MJML remains the *email* module format, not the module system's format.
    **The user's question — does any channel but email actually need modules? —
    checks out in the opposite direction, which strengthens the decision.** Push
    is flat, but a **letter is genuinely compositional** (salutation, body
    sections, offer block, footer — a printed piece resembles a newsletter), and
    **carousel social ads** are several ordered cards each with image, headline and
    link. So composition is not an email peculiarity; **push is the exception**.
    Channel-neutral wording and per-channel splitting is therefore the scalable
    choice, and the `max_modules` channel fact from Q1 already spans the range —
    push declares 1, email and letter unbounded — with no special-casing.
15. ✅ Snapshot: one artifact per execution, or can one execution carry several
    (e.g. letter PDF + a print-ready address file)? Touches [[ADR-062 — Snapshot Stores Final Render State]] and [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]].
    **Resolution (2026-08-07): a set of artifacts, each with a role, plus a
    package hash over the set.** `render()` returns a collection — push returns
    one, email two, letter a PDF plus its address manifest — with roles such as
    `body_html`, `body_text`, `address_manifest`, `creative_image`.
    **Email already needs this today**, which is what settles it: `multipart/
    alternative` — an HTML body *and* a plain-text alternative — is twenty-year-old
    standard practice that spam filters penalise the absence of. "One artifact per
    execution" was a constraint being lived with, not a simplification chosen.
    **The hash covers the set, not a member.** Hashing only the HTML would leave
    the plain-text part unverified, and the two will eventually diverge.
    **This is [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]] landing where it always pointed** — it already separates snapshot
    state from the recipient delivery artifact, and this gives the second half a
    shape. It is also exactly the two-artifact framing the code review recommends
    for P1-04: an approval snapshot, and an immutable per-delivery package the
    provider request traces back to.
    **Costs:** every renderer returns a collection even with one thing to give,
    and [[ADR-062 — Snapshot Stores Final Render State]] needs its wording
    generalised from a single render to a package — the same amendment ADR-063
    needs from Q13.

### Cluster 4 — Identity, consent & permission  ✅ CLOSED 2026-08-07
16. ✅ Consent as rows per `(recipient, channel, purpose, status, source, timestamp)`
    — confirm the shape. *Lean: rows, not columns — the same idiom already used
    for roles in the security base.*
    **Resolution (2026-08-07): rows, append-only events, latest-wins per
    `(recipient, channel, purpose)`.** Columns were never viable — five channels
    × three purposes is fifteen of them, none extensible without a migration, and
    a column cannot carry the *source* and *timestamp* that make consent provable.
    **Events rather than mutable current state**, for reasons already settled
    elsewhere: [[ADR-154 — Erasure and Retention]] requires consent proof to
    survive an erasure, and a mutable status overwrites exactly the history
    needed to defend a UWG §7 complaint; and the signal layer already made this
    choice, dropping the mutable `RecipientPreferenceDB` running total in favour
    of append-only contributions computed on read ([[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]). Consent is
    cheaper than signals — no decay, just latest-row-wins on an indexed query.
    **The user's addition, and it removes an obligation rather than adding one:**
    the readable **current state lives in the CRM anyway** — that is where
    customer service looks — so this platform does not need to be the
    human-facing consent store. *"For our purposes we can use latest."* Consistent
    with [[ADR-120 — CRM as Customer Source of Truth]] and
    [[ADR-126 — Maintain Local Recipient Projection]]: the CRM owns the readable
    truth, we hold the operational event log.
    **Replaces `RecipientDB.consent_status`**, the single column the consent gate
    is built on in `resolve_audience` and `execute_decision_slot`. That schema
    change was already logged as a known cost when consent split by *purpose* in
    the security chapter; adding the channel dimension now means it lands once.
    **Left to Q19:** `ConsentSyncLogDB` already exists as an append-only sync log
    beside the mutable column. If consent becomes an event log, the two need
    reconciling — same table, or does the sync log stay separate as the record of
    *CRM conversations* rather than *consent facts*?
17. ✅ Addressability per channel: where do device tokens, postal addresses, handles
    and hashed identifiers live? Extends [[ADR-121 — Minimal Recipient Model]].
    **Resolution (2026-08-07): one addressability table, rows plus a JSON value —
    "here's all contact points possible per recipient", whatever the type**
    (user). Three things force it off `RecipientDB`: **cardinality** (one email,
    but many push tokens — phone, tablet, reinstalled app), **lifecycle** (tokens
    expire and APNs reports dead ones, so a status you can mark invalid beats a
    value you overwrite), and **structure** (a postal address is street/postcode/
    city/country, not a string). `value` as JSON matches the idiom already used by
    `ContentRecordDB.content`, `module_data` and `app_config.value`.
    **Hashed identifiers are NOT stored** (agreed): `SHA256(normalised email)` is
    computed when the audience is assembled. Storing it adds nothing already held
    and creates a second copy of the person to find at erasure time. It is a
    derivation step in the delegated adapter, not addressability.
    **OPEN sub-problem the user raised, and it has no answer yet: selection when
    a recipient has several rows for one channel.** *"If a person had more than 1
    address we'd need to think of a 'what address to take' process."* The
    semantics differ per channel — **push fans out** to every valid token (all
    the person's devices buzz), while **letter, SMS and email pick one**. So this
    is *fan-out vs pick-one*, which is true of the channel whatever the vendor,
    making it a **second channel-level fact** alongside module cardinality from
    Q1 — both are "how many". For pick-one, the minimal answer is a primary flag
    per `(recipient, channel)` with most-recently-verified as fallback; not
    decided here. **Barely bites today**: email has one address in practice and
    push fans out, so it only becomes real with letter or multi-email.
    **Reinforces scope (user): another reason to keep letter out of the POC**, or
    out entirely.
    **Two consequences to name rather than discover:**
    [[ADR-121 — Minimal Recipient Model]] assumes one address and needs
    revisiting — the model stays minimal, addresses just move out of it, but the
    ADR says otherwise on its face. And **erasure reaches these rows**: they are
    identity data, so they go with the identity under
    [[ADR-154 — Erasure and Retention]], not with the id-keyed activity that
    survives — easy to overlook precisely because they sit in a different table,
    the same trap that made signals easy to miss there.
18. ✅ Is "may I transfer your hashed identifier to an ad platform" a consent
    *purpose*, a separate consent *type*, or out of scope for the platform?
    **Resolution (2026-08-07): a purpose.** `(recipient, paid_social, transfer)`
    sits alongside `(recipient, paid_social, marketing)` as an independent grant
    in the Q16 grid — no new machinery.
    **Why not fold it into the channel**, the tempting simplification since paid
    social is impossible without the upload: it breaks on an ordinary case,
    **suppression uploads**. Companies routinely push a customer list to Meta in
    order to *exclude* those people from acquisition ads — a transfer with no
    marketing to them at all, arguably in their interest. If transfer were
    implied by channel consent, that case could not be expressed without claiming
    a marketing consent nobody gave.
    **Why not a separate consent type:** it would mean a second consent mechanism
    beside Q16's, with its own storage and its own gate — the kind that later gets
    checked in one place and forgotten in the other.
    **Why not out of scope:** the platform is the thing *performing* the transfer.
    Shipping the capability while disowning permission for it leaves an adopter
    with no way to comply.
    Consistent with [[ADR-144 — AI Data and Model Governance]]: we do not make the
    legal determination, we make the model granular enough that the adopter can
    encode whatever their counsel says. Whether a German DPA accepts a given basis
    for Custom Audiences is their lawyer's question; ours is whether the answer is
    **expressible**.
19. ✅ How does CRM consent sync carry per-channel state? (`ConsentSyncLogDB` today
    syncs a single status.)
    **Resolution (2026-08-07): two separate tables, because they record different
    kinds of fact.** **Consent events** record what the *person* permitted,
    whatever the source — CRM sync, a signup form, an unsubscribe click, an
    import. **The sync log** records what happened in a *conversation with the
    CRM*: it ran, it failed, it found drift. Merging them would put failed sync
    attempts into somebody's consent history, and a sync that errored is not a
    consent change. A sync that does change something writes to **both** — an
    event with `source = crm`, and a sync-log entry saying the run applied N
    changes. Q16's `source` field is what links them without a second mechanism.
    **Mapping lives in the sync adapter, per deployment**, because every CRM
    differs — same posture as the provider layer, and the same reasoning the
    inbound-adapter backlog item already uses in preferring "simple to adjust to
    your provider" over "one contract that auto-fits everything".
    **The principle the user set here, and it reaches well past this question:**
    *"We don't say that a company doesn't have to make changes to external
    systems to prepare data — so we can say: if you want this, your CRM system has
    to do this."* A company wanting several channels **must capture consent per
    channel**, and will adjust its CRM to match. So the platform does **not** build
    inference or elaborate mapping to compensate for a CRM that cannot express
    per-channel consent; it states the requirement. Consistent with
    [[ADR-120 — CRM as Customer Source of Truth]] and
    [[ADR-104 — Audience Ownership Stays Outside Provider]], and it settles a whole
    class of future questions of the form "should we infer X because their system
    lacks it?" — no.
    **Consequence:** a single-flag CRM maps to `(email, marketing)` and reasonably
    to other addressed channels, but says nothing about uploading someone to an ad
    platform. That grant is **absent until captured**, never inferred, and the UI
    shows it missing rather than assumed — safe by construction, and the adopter
    goes and gets the consent.
    **Drift grows with it:** `GET /recipients/consent/drift` compares one status
    today; per-channel consent makes drift per `(channel, purpose)` — in sync on
    email marketing, adrift on social transfer.
20. ✅ Does the send-time consent gate become per-channel, and what happens when a
    campaign spans channels with different consent coverage?
    **Resolution (2026-08-07): yes, per `(channel, purpose)` — and the second half
    dissolves.** A *variant* is planned and sent, not a campaign (Q4), so there is
    no moment at which a campaign "spans channels" at send time. Each variant
    resolves its own audience against its own channel's consent; the push audience
    simply comes out smaller. Not a condition to handle — that is the answer.
    **The gate becomes an ordered stack**, run immediately before handing to the
    provider (and at **audience assembly** instead for delegated channels, which
    have no per-recipient send moment):
    **(1) addressability** — a valid, non-expired address for this channel;
    **(2) consent** — a grant for this `(channel, purpose)`;
    **(3) suppression** — hard bounce, complaint, manual blocklist;
    **(4) frequency** — post-POC, concept documented in the playbook (Q9).
    **The stack must record WHY each recipient was excluded, not merely exclude
    them.** That is the real lesson of the open P0: the consent guard *did* fire,
    and a bare `except ValueError` threw the reason away, so a compliance defect
    read as a rendering behaviour. A stack that silently drops people reproduces
    that failure one layer up. Typed exceptions plus a recorded exclusion reason
    make "why didn't Anna get this?" answerable — which
    [[ADR-085 — Decision Resolution Should Be Optionally Explainable]] already
    promises for decisions and [[ADR-153 — Audit and Accountability]] is the home
    for. **This is the shape the P0 fix should be built in**, which was the reason
    for running Cluster 4 before fixing it.
    **ORDER IS A PERFORMANCE DECISION AND MUST BE WRITTEN DOWN (user).** All four
    stages are ANDed, so order never changes *correctness* — only how many rows
    reach the later, more expensive stages (frequency needs history). The user's
    instinct that consent-first reduces processed records **is right for email and
    probably wrong for push**: for email everyone has an address and some opted
    out, so consent is the selective filter; for push few people have a live token
    at all while most who installed granted permission, so addressability is. So
    **most-selective-first is channel-dependent** — do not hardcode one order as
    universal. Belongs in the performance-notes document with a trigger threshold.
    **Implementation note that gets both properties:** express each stage as a
    **set operation, not a per-recipient loop**. The set excluded by a stage is
    `input − output`, recordable in bulk, so per-stage attribution survives without
    the N+1 pattern the send path is already flagged for (code review P2-04), and
    the query planner handles ordering within a stage.

### Cluster 5 — Feedback & signals  CLOSED 2026-08-07
21. ✅ Which channels return per-recipient events, which return aggregate — and how
    is that declared rather than assumed?
    **Resolution (2026-08-07): declared per PROVIDER, never per channel — and
    the user's reason is the stronger one.** *"Technology will change and a social
    media platform might allow per-recipient feedback in the future."* Encoding
    "social = aggregate" anywhere would bake in a vendor limitation with a shelf
    life. This closes a loop: it is the same argument that made the Q8 rejection
    of a channel-level capability file correct.
    **Enforced at ingestion, because a declaration nothing checks is decoration.**
    A provider that declared aggregate-only attempting to write a per-recipient
    event is refused and fails loudly. That guard is also **Q22's protection** —
    aggregate leaking into per-recipient signals is an enforcement gap, not a
    discipline problem, and closing it here closes it structurally.
    **Two destinations, and this is the load-bearing split (user).**
    **Per-recipient events → the signal layer → decisions.** That is what signals
    are *for*.
    **Aggregate results → analytics.** A human-read view, not a decision input:
    *"if a company wants to use numbers from the socials or letters it's more an
    analytical look instead of signals that can be used in the decision
    algorithm."* Aggregate data is therefore **not discarded** — it simply lives
    in reporting rather than the decision path, and **is never interpolated onto
    individual recipients**.
    **Feedback source ≠ provider.** Q7 established that for blind channels the
    return path is the adopter's **own domain** — a tracked link in a letter or an
    ad firing back with our identifier from their site. A letter-shop adapter
    declaring "no feedback" is accurate about *itself* while per-recipient
    engagement still arrives by another route. So **any channel can have
    per-recipient feedback if the adopter instruments their own site**; it is just
    not the provider's to give. A better line for the playbook than "letters have
    no feedback".
    **Direction, explicitly NOT phase 1 (user):** eventually aggregate results
    should inform decisions at **segment level** — using how a social post
    performed to shape the next one. That is genuinely valuable and genuinely
    different from per-recipient signals; parked.
22. ✅ **How is aggregate feedback kept out of the per-recipient signal layer?**
    Attributing segment numbers to individuals would corrupt the decision layer's
    auditability.
    **Resolution (2026-08-07): a separate table with its own grain — explicitly
    NOT the engagement event table with `recipient_id` made nullable.**
    That is the same reasoning that made dropping organic social a simplification:
    a nullable recipient column leaves campaign-level and per-recipient facts
    sharing a table with incompatible meanings. Every consumer would then have to
    remember `WHERE recipient_id IS NOT NULL` — the signal layer, attribution,
    every report — and one omission means segment numbers are read as a person's
    behaviour, silently. **The corruption would arrive through the schema rather
    than through carelessness**, so the schema is where it gets prevented.
    Keyed by what aggregate data is actually about:
    `(send_instance or audience, creative/variant, metric, value, period)`.
    **The signal layer then cannot physically read it** — Q22's guarantee becomes
    structural rather than a rule to follow, the same property typed interfaces
    bought in Q6.
    **SCOPE (user): aggregate ingestion and display are NOT POC.** *"We need to
    cut down features and this might be easy to move into a future phase."*
    Prepared in the POC only if trivial, otherwise explained in the library.
    **The deliverable here is the recorded constraint, not code** — it costs
    nothing now and stops phase 2 taking the nullable-column shortcut.
    **Fifth deferral in this interview, and they form a coherent phase-2 set:**
    volume capping (Q9), letter integration (Q10), cross-channel follow-up
    audiences (Q9), aggregate ingestion/display (Q22), aggregate-informed segment
    decisions (Q21).
23. ✅ What does [[ADR-103 — Provider Events Are Normalized Into Internal Events]]
    normalisation mean when an event has no recipient?
    **Resolution (2026-08-07): it does not — a thing with no recipient is not an
    event in ADR-103's sense. It is a metric.** Internal events are per-recipient
    by construction: they carry a recipient, feed signals and attribute to
    content. Something reported per audience-and-creative over a period has a
    different grain, a different table (Q22) and a different consumer. **Calling
    both "events" is what pushes toward the nullable column already ruled out —
    the noun does the damage before the schema does.**
    So **ADR-103 needs only a scope clarification**: it governs per-recipient
    events. Metrics have their own path, not built.
    **The rule to state in the ADR, because it is the part that gets forgotten:
    an event without a recipient is refused at ingestion, not stored with a
    null.** Together with the Q21 declaration check, that is what makes Q22's
    separation hold at runtime rather than only in the schema.
    **Example of why the distinction pays:** "audience synced, 340 of 500 matched"
    is genuinely useful to a manager and genuinely meaningless attributed to
    anyone.
    **Returned letters — an exception NOT to design around (user).** "Address
    doesn't exist" is per-recipient, but it is unlike an email or push
    non-deliverable in two ways: it arrives **days later** as an asynchronous
    event rather than an API response to the send, and whether it arrives **at
    all** depends both on the provider offering it and on there being an API path
    rather than a physical box of returned mail. It would likely need its own
    reconciliation process. **Do not over-design it** — doubly deferred, since
    letter is already out of POC scope (Q10). The bounce vocabulary can absorb it
    if and when a provider reports it.
24. ✅ Is the conversion-API path (adopter's own site fires back with their
    identifier) in scope for the POC, or a documented extension point?
    **Resolution (2026-08-07): documented extension point — consistent with the
    existing backlog decision** that conversions are a pluggable contribution
    type whose ingest path is per-deployment, delivering "the extension point plus
    one worked example when a real adopter needs it". Omni-channel does not change
    the answer, it raises the stakes: for delegated and blind channels this is the
    **only** per-recipient feedback path there is.
    **The mechanism largely exists.** A conversion callback is structurally what
    `POST /provider/webhooks/resend` already does — an external system posting an
    event carrying an identifier. What is missing is **machine authentication**
    (already P0) and a **documented event contract**. So it arrives close to free
    once machine auth lands, rather than needing its own build.
    **Conversions are per-recipient events under ADR-103** and feed signals
    normally, even though they arrive from the adopter's system rather than a
    provider — the one case where a blind channel produces a first-class signal.
    **But a conversion is NOT a click with a different name (user):** it carries
    *what* converted, not only *that* it did, and structuring that depends
    entirely on the business — products, PDF downloads, bookings.
    **Boundary: the platform records THAT it converted; WHAT belongs to the CRM or
    DWH.** Modelling "what" means modelling every adopter's business, which is
    unbounded and is already assigned elsewhere by
    [[ADR-120 — CRM as Customer Source of Truth]] and
    [[ADR-124 — DWH Is Recommended but Not Mandatory]]. At most an **opaque
    external reference** the adopter's own system resolves. Same posture as Q19:
    if they want product-level conversion analysis, that is their DWH's job.
    **Minimum that holds (user): "clicked this and bought *anything*"** — enough
    for signals, since it yields the content, its categories, and a heavier
    contribution weight than a click.
    **Trap named:** a conversion *value* looks like one nullable number but drags
    **currency, net-versus-gross and refunds** behind it — a refunded conversion
    arguably has to be reversed. So the honest minimum is the boolean; value
    belongs with the analytics phase.
25. ✅ Does the signal layer need a channel dimension — is a click in email the same
    signal as a tap in push? Touches [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]].
    **Resolution (2026-08-07): yes — an explicit `channel` column on
    `SignalContributionDB`. It does not change the topic score.** One append-only
    log read along two axes: **topic affinity** (sum over categories, ignoring
    channel — unchanged; interest in hiking is interest in hiking wherever it was
    clicked) and **channel affinity** (sum over channels, ignoring category —
    new). The second is what makes Q2's forward consequence possible at all: the
    decision layer cannot choose a channel per recipient without knowing which
    channels that person engages with.
    **Two alternatives the user raised, both checked and rejected on evidence.**
    **(a) Extend `contribution_type` values** (`click_email`, `tap_push`): crosses
    two orthogonal facts into one enum — five types x five channels is 25 values —
    and it breaks channel weighting, which wants a **grid**, not a flat list.
    ADR-132 configures half-lives per contribution type, so it would also produce
    25 half-lives where two independent axes are wanted.
    **(b) Derive channel from `event_id`**: the path exists but is **five joins** —
    contribution to event to execution to send instance to snapshot to variant —
    on every read, in a layer designed around compute-on-read. Worse, `event_id`
    is **nullable** (manual declared preferences have no event), so channel
    returns unknowable rather than not-applicable; and **ADR-132 prunes**, keeping
    only a bounded operational window locally with history in the DWH — so if
    executions are pruned on a different schedule than contributions, **old
    contributions lose their channel retroactively**, degrading silently over
    exactly the period worth analysing. A denormalised column is immune to all
    three.
    **Weights: extend the settings grid by channel, and it is the company's call
    whether to weigh channels differently, not ours (user)** — consistent with
    "numbers belong to the company, mechanism to us" (Q9). Default equal until
    there is data; a push tap is lower-friction than an email click and arguably
    signals less, but that is a guess without evidence.
    **Note the two affinities decay differently.** Topic interests shift over
    months; "never opens email, always taps push" is a stabler fact. ADR-132
    already makes half-lives configurable per type, so this needs no new
    mechanism.

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
