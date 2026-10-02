---
type: adr
status: accepted
topic:
  - architecture
  - provider
  - signals
  - tracking
  - engagement
created: 2026-10-02
source:
  - "task-45 (code review 2026-08-07, P2-07)"
  - "User direction 2026-09-14: attribution is a provider-capability question"
  - "Decided by the user 2026-10-02"
depends_on:
  - "[[ADR-101 — Provider Capabilities Are Explicit]]"
  - "[[ADR-102 — Rendering Prepares Tracking Metadata]]"
  - "[[ADR-129 — Correlate Provider Events to Delivery Executions]]"
  - "[[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]"
---

## Status
Accepted

## Context

A click or open becomes per-category affinity in the signal layer ([[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]) only if the event carries a content record: the signal layer credits that record's categories. Correlating the event to its Delivery Execution ([[ADR-129 — Correlate Provider Events to Delivery Executions]]) says *which email* was engaged with. It does not say *which content in that email*.

**Today that gap is filled by a guess.** `_primary_content_id_for_delivery` in `backend/app/providers/service.py` (lines 126–165, called at line 187 from `process_provider_webhook_event`) attaches a "primary" content record to every webhook click and open. It takes the recipient's latest personalized decision resolution and, failing that, the variant's first content-bound module. It never looks at which link was clicked. Its own docstring says why: Resend clicks report a URL, not our content id, so it attributes to "what was shown rather than parsing the link", with link-to-content mapping deferred as "a later refinement".

**In a multi-content newsletter that guess is wrong, and nobody can see it.** A click on the fourth item credits the first. Decision slots can resolve several content records ([[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]), and a newsletter with several items is exactly the case the product exists for. So affinity learning is systematically wrong in the case that matters most. Nothing fails while this happens: the profile simply fills with confident, wrong signal. task-45 (code review 2026-08-07, P2-07) raised it.

**Opens are attributed the same way, but the harm there is latent rather than active.** The default open weight is already 0, because Apple Mail Privacy Protection makes opens noise. The guessed content on an open moves no signal today. It would start doing so the moment someone raised the open weight.

**The user's direction of 2026-09-14 framed this as a provider-capability question.** To attribute a click to content, the click must carry the content id back. How that happens depends on the provider: Salesforce uses link names, Selligent uses data-attributes, and others do it differently. That makes it a declared capability in [[ADR-101 — Provider Capabilities Are Explicit]]'s sense. It has the same shape as [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]], which gates provider selection on a capability.

**The carrier is already decided but not built.** [[ADR-102 — Rendering Prepares Tracking Metadata]] decided that rendering generates tracking metadata, which may include `contentId`, and that providers may extend how that metadata is carried. Nothing implements it yet: no rendered link carries a content id today.

**Two narrower answers were considered and set aside, for the reasons the user gave.**
- **Crediting the single content record in a one-item email.** This looks safe but is not. The click may be on a logo, the footer or another non-content link, and crediting the content for it is the same guess made in a smaller space.
- **Treating attribution as mandatory and blocking providers that cannot supply it, as ADR-106 does.** This would be disproportionate. Bounce and complaint feedback is a compliance and reputation duty. Content attribution affects learning quality. A provider that lacks it still sends correctly and still reports engagement for the email.

## Decision

**1. A click or open credits a content record's categories only when the event itself identifies that content.** The event can identify content through a tracked link or a provider attribute that names it. Nothing is guessed. The "primary content" fallback is removed.

**2. An event that cannot be tied to content is still recorded as an engagement event, but credits no category affinity.** It happened, and it counts for the email. The trade is that affinity learns less, but it learns nothing wrong.

**3. An email with exactly one content record gets no exception.** A click there may be on a logo, the footer or another non-content link. It credits nothing unless the link names the content. As a result, click-driven affinity learning pauses entirely until tracked links exist. This is accepted.

**4. Returning a content identifier on a click is a declared provider capability, in [[ADR-101 — Provider Capabilities Are Explicit]]'s sense.** A provider without this capability stays selectable: sends work and clicks count for the email. It simply has no content-level attribution. The provider and settings surface should say so, so the trade-off is visible when a provider is chosen. This differs on purpose from [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]. Bounce and complaint feedback is a compliance duty that gates selection. Attribution is learning quality, and blocking the provider over it would be disproportionate.

**5. Building the carrier is follow-up work, not part of this decision's first implementation.** The carrier has two parts: rendering content ids into tracked links per [[ADR-102 — Rendering Prepares Tracking Metadata]], and mapping a provider's click payload back to the content. The first implementation removes the guess and records unattributed events as point 2 describes. The carrier comes after it.

## Consequences

### Positive
- No wrong signal enters a recipient's profile. Every category contribution from a click traces to content the recipient actually chose.
- The rule fits in one sentence: *a click credits content only when the link names it.* There is no fallback chain to reason about and no special case for one-item emails.
- Declaring the capability makes the provider trade-off visible. An operator choosing a provider can see that it sends correctly but teaches the engine nothing about content, so the gap is no longer hidden.
- The latent harm on opens is closed too. Raising the open weight later can no longer amplify a guess.

### Negative
- **Click learning stops now, before tracked links ship.** Until the carrier in point 5 exists, live webhook clicks are recorded against the email but move no signal. For that period the decision layer learns nothing new from clicks.
- Demo and seed data created with explicit content ids are unaffected. That can make the demo look as if learning still works while live traffic contributes nothing, and anyone reading scores during this period needs to know the difference.
- Web tracking as a fallback attribution path is less reliable (the user's note) and is not designed. If the carrier is delayed, there is no second route to content-level attribution.
- A provider that cannot carry a content id produces less useful engagement data by design. Adopters who choose one get a working send and a learning engine without click-to-content attribution.

## Notes

- **Where the first implementation landed (2026-10-02).** `_primary_content_id_for_delivery` is deleted, and `process_provider_webhook_event` in `backend/app/providers/service.py` attaches nothing. It applies signals only when the event's own data carries `content_record_id`, so an unidentified click is recorded and the signal layer is not called at all. The function had one caller, so its removal reached nowhere else. `backend/tests/test_click_attribution.py` pins both halves: unidentified credits nothing, named credits.
- **Nothing is superseded.** [[ADR-102 — Rendering Prepares Tracking Metadata]] already provides for `contentId` in tracking metadata. This record makes it the *only* source of content attribution and is its first consumer. It does not change ADR-102's Decision.
- **[[ADR-101 — Provider Capabilities Are Explicit]] may want a dated addendum** listing content attribution on click among its optional capabilities, in the pattern of its 2026-09-12 addendum. This record does not make that edit.
- [[ADR-164 — Channel Feedback and Signals]] point 6 names the adopter's own instrumented site as a per-recipient feedback route for blind channels. Such a route would fall under the same rule: it credits content only if it names the content.

## Related ADRs

### Depends On
- [[ADR-101 — Provider Capabilities Are Explicit]]
- [[ADR-102 — Rendering Prepares Tracking Metadata]]
- [[ADR-129 — Correlate Provider Events to Delivery Executions]]
- [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]

### Referenced By
- [[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]]
- [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]]
- [[ADR-164 — Channel Feedback and Signals]]
