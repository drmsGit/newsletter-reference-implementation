---
type: adr
status: proposed
topic:
  - architecture
  - channels
  - campaign
  - variant
  - composition
created: 2026-09-01
modified: 2026-09-01
source:
  - "Omni-Channel design interview (interview-prep, closed 2026-09-01), Cluster 1 / Q1–Q5"
depends_on:
  - "[[ADR-012 — Content Records Represent Communication Units]]"
  - "[[ADR-021 — Variants Are Human Created Versions]]"
  - "[[ADR-022 — Delivery Type Is Independent From Composition]]"
  - "[[ADR-031 — Newsletter Composition Stores Structure Not Content]]"
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
enables:
  - "[[ADR-161 — Channel Execution Shapes]]"
  - "[[ADR-162 — Channel Rendering and Artifacts]]"
  - "[[ADR-163 — Per-Channel Consent and Addressability]]"
  - "[[ADR-164 — Channel Feedback and Signals]]"
---

## Status
Proposed

## Context

The architecture is named and shaped for newsletters, but the requirement it actually serves is content management and orchestration for **any channel an adopter can reach through an API** — a letter shop, a push service, a messaging platform, a paid-social ad account. Roughly 80% of the system already generalises, and that is a consequence of earlier decisions rather than luck: [[ADR-012 — Content Records Represent Communication Units]] defines a record as a reusable communication unit and deliberately not "an email", the decision layer resolves content records without knowing what an email is, and [[ADR-022 — Delivery Type Is Independent From Composition]] already separates delivery type from composition. What is email-bound sits in a thin band at the outbound end.

Five things were settled before the interview opened and are not re-argued here. **Per-channel variants under a shared campaign** — not one neutral composition each channel renders its own way, because a social ad is genuinely not the same artifact as a newsletter and forcing one composition to serve both produces lowest-common-denominator content. **Channel selection is the manager's choice, never forced**; a campaign is not required to cover every channel. **Organic / broadcast social is out of scope** — the interest is personalised paid social, which is still *addressed*, merely delegated. **The direction of travel is smaller and smaller groups**, down to one-to-one wherever that is technically possible. And **the shared core stays shared**: content, decision, audience, signal and override layers are not channel-specific and must not become so.

This ADR fixes the model layer — what a channel *is* to a campaign, a variant and a composition. The execution, rendering, consent and feedback consequences are carried by [[ADR-161 — Channel Execution Shapes]], [[ADR-162 — Channel Rendering and Artifacts]], [[ADR-163 — Per-Channel Consent and Addressability]] and [[ADR-164 — Channel Feedback and Signals]].

## Decision

**1. Channel is a contract enforced at authoring time, not a transformation applied at rendering time.**
Picking "push" restricts the manager to push-legal modules and a push-sized payload. The rejected alternative — a free composition that each channel renderer degrades as best it can — fails the manager at the worst possible moment: someone who writes 600 characters and learns at send time that push truncated to 178 has been failed by the tool. Authoring-time constraints also make "ready on push" a **checkable fact rather than a hope**. Email modules stay email-only; this is the path email already took through MJML ([[ADR-131 — Email Module Templates Use MJML as Source Format]]) and it generalises.

**2. Push carries no HTML, and a push is one message rather than a composition.**
APNs, FCM and Web Push all take structured fields (`title`, `body`, `image`, link) inside a roughly 4 KB budget, and the receiving OS does all rendering — a push renderer fills fields and has no layout job. The module tree therefore needs nothing new: one `ModuleInstanceDB` of type `push` at position 0, pointing at a content record **or a decision slot**, which is how personalised push comes free. The channel declares **max one module** as a declared capability rather than the composition code special-casing push.

**3. Channel readiness is a property of the content record, and channel fields are separate and required — never derived from email fields.**
Each record can be pushed as long as it is prepared for the push channel. Deriving a 40-character push title from a 60-character email headline at render time *is* the rendering-time transformation point 1 rejects. Two consequences fall out and are ruled in here: decision slots filter candidates to channel-ready records through the existing `candidate_filter_fields`, so the engine can never select content a channel cannot carry ([[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]); and the override layer needs no change. The only real cost is more fields to author, which is precisely what Mode A removes — "suggest the push headline from this record" is the same task shape as suggest-subject ([[ADR-141 — In-App Assistive AI Actions]]), with the **confirmed value stored as a real field** rather than derived at send time.

**4. Channel is an attribute on the variant.**
A campaign ("Hiking") carries one or more email variants, push variants, paid-social variants. This is consistent with [[ADR-021 — Variants Are Human Created Versions]]: a push version is a deliberate, reviewable, human-created version, so no new concept is introduced and campaign coverage is derived rather than stored.

The rejected alternative was a **channel-plan level between campaign and variant**. It would have made "which channels is this campaign running on" stored intent rather than derived, and given channel-level settings — a different send time for push than for email — a home. That is not worth a new concept in the model, the UI and the playbook. The principle behind the rejection outranks the mechanics: *it is not about the channel, it is about the topic — the channel is just what the recipient might like best.* A mid-layer that groups by channel encodes "we organise our work by channel" into the model, which is the platform imposing a workflow. **The campaign is the topic; the channel is a delivery preference, not a structural division of the work.** Grouping by channel is therefore UX.

**5. A variant's channel is fixed at creation.**
This fell out of point 4 rather than being argued separately: switching an email variant to push would invalidate its modules, its content-readiness and its renderer simultaneously. Changing channel means creating a new variant.

**6. Registering a channel means a channel manifest plus a provider adapter — two files, no config step.**
The manifest *is the channel*; the adapter *is the vendor* (APNs, FCM, OneSignal). That is the same split [[ADR-100 — Provider Layer as Send and Feedback Adapter]] already draws, so a company can change vendor without changing what "push" means. There is no separate registry and no settings row: decision strategies already auto-register from a dropped `.py` and email modules from `name.json` + `name.html`, and a third pattern that needs registering in several places is the one that eventually gets registered in two.

The criterion this serves, and it should settle later arguments about how much a manifest must declare: **time-to-first-output beats completeness** — a framework that gets a company basic functions in a weekend rather than half a year. If a requirement slows the weekend path, it is optional or it is defaulted. ([[ADR-161 — Channel Execution Shapes]] narrows what the manifest holds: capabilities live in the provider file, fields and limits in the module manifest, leaving cardinality as the channel-level fact.)

**7. Campaign coverage is derived and purely descriptive — no stored intent, and no coverage warning either.**
Coverage is just what exists: email + push variants means the campaign is email/push; only a social variant means it is social. Stored intent is unnecessary bureaucracy — a manager will think "this is meant for push", but they need to get *past* that thought, not file it. It would also put channel back into the campaign's structure through the side door, against point 4, and create a drift class where intent and reality disagree with nobody clearing the stale state.

The pre-interview lean was "warn, never block". **It is superseded because its premise was wrong: a variant is planned and sent, not a campaign.** There is no campaign schedule that launches every variant in it — a `SendInstanceDB` hangs off a snapshot of one variant ([[ADR-095 — Use Send Instances for Technical Execution Tracking]]). So there is no campaign-level send event at which to warn that "push has no variant", and nothing to warn about: nobody asked to send push.

## Consequences

### Positive
- Channel absorbs into the existing model with **no new level** between campaign and variant, and no change to the composition tree, the override layer or the decision layer.
- "Ready on push" is a checkable fact at authoring time rather than something discovered at send time by a truncated notification.
- Personalised push is free: a push module may point at a decision slot exactly as an email module does.
- Content that a channel cannot carry can never be selected by the engine, because the existing `candidate_filter_fields` mechanism already expresses the filter.
- The campaign stays the topic. The model does not encode a channel-shaped way of working, which keeps it usable by teams that organise differently.
- Registering a channel is two files, consistent with the auto-registration idiom already trusted for strategies and modules.

### Negative
- **A variant now carries two meanings at once** — A/B version *and* channel expression — which reads awkwardly at "Push A / Push B". Accepted as a **display** concern to be solved by grouping in the UI, not a model one.
- Channel-level settings, such as a different send time for push than for email, have no home. That was the channel-plan layer's one genuine advantage and it is given up deliberately.
- More fields to author per content record, mitigated but not removed by Mode A suggestions.
- Because variants are planned and sent independently, **nothing in this ADR prevents a recipient receiving both the email and the push variant of the same campaign.** That is left to [[ADR-161 — Channel Execution Shapes]], where it is deliberately handled as audience composition rather than suppression.
- A variant whose channel turns out to be wrong is thrown away and re-created rather than switched.

## Notes

- **Forward consequence, explicitly not decided here.** If the channel is "what the recipient might like best", channel selection eventually becomes a *decision* — the engine choosing per recipient which channel, and therefore which variant, they receive, with the AI selecting the most suitable. That requires channel to be a signal dimension, which [[ADR-164 — Channel Feedback and Signals]] provides. It is named so it is not designed away, not scheduled.
- **Loose end from the registration decision:** whether a deployment can *disable* a channel it is not licensed for without deleting files. It is governance of the same shape as [[ADR-140 — AI Capability Layer]]'s kill switch and governed model list, where availability is code and selection is a setting. Not decided.
- **Amendments other records need — none of them made here.** [[ADR-021 — Variants Are Human Created Versions]] does not anticipate a variant carrying a channel and would benefit from a dated addendum recording the second meaning and that it is a display concern. [[ADR-001 — Newsletter Architecture Boundaries]] scopes the core to "newsletter-specific responsibilities", which no longer describes the intended scope; **no resolution in this interview decided what to do about it**, so it is flagged rather than answered.
- Nothing in this ADR supersedes an accepted record. What point 7 supersedes is a *lean* recorded in the interview prep and in the playbook decision log (entry 16, 2026-08-12), not a decision in force.

## Related ADRs

### Depends On
- [[ADR-012 — Content Records Represent Communication Units]]
- [[ADR-021 — Variants Are Human Created Versions]]
- [[ADR-022 — Delivery Type Is Independent From Composition]]
- [[ADR-031 — Newsletter Composition Stores Structure Not Content]]
- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]

### Enables
- [[ADR-161 — Channel Execution Shapes]]
- [[ADR-162 — Channel Rendering and Artifacts]]
- [[ADR-163 — Per-Channel Consent and Addressability]]
- [[ADR-164 — Channel Feedback and Signals]]

### Referenced By
- [[ADR-020 — Campaign Equals Newsletter]]
- [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]
- [[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]
- [[ADR-095 — Use Send Instances for Technical Execution Tracking]]
- [[ADR-131 — Email Module Templates Use MJML as Source Format]]
- [[ADR-140 — AI Capability Layer]]
- [[ADR-141 — In-App Assistive AI Actions]]
