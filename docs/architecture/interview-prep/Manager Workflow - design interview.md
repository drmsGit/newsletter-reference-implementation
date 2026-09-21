---
type: interview-prep
topic:
  - architecture
  - frontend
  - design
created: 2026-09-21
modified: 2026-09-21
status: open
---

> **Status: interview OPEN.** Clustering approved 2026-09-21. All five clusters
> written out — 47 questions, 9 resolved (Cluster 2's authoring half is closed). **No further frontend work before
> Cluster 2 closes**; its questions decide screens that are already built.

# Manager Workflow — design interview (forward-looking)

Like [[Omni-Channel - design interview]] and [[AI Layer - design interview]],
this file gathers the **decisions needed before writing ADRs**, rather than
reviewing implemented code.

## Why this came up

The React client was being built from the API surface. Two phases shipped —
sign-in, the shell, and seven read-only screens — and a third was about to design
the send-planning screen from a service function's signature.

The user stopped it, on 2026-09-20:

> *"I build the backend as the structure how the final results are stored (so any
> screen or call can work) … But no documents show WHAT and WHY I want to do (in
> an operative way) … it feels like you assume a lot and that way I can't review
> if you're adding unnecessary code that bloats the software."*

That is correct, and the repository says so itself. `docs/react-screen-inventory.md`
opens with:

> *"This is an inventory, not a design. It says what exists and what each screen
> needs. It does not say what any of it should look like, how it should be laid
> out, or what should be on one page versus two — those are the design pass's
> questions and this document deliberately leaves them open."*

**The ADRs and the code cannot answer these questions, by design.** The ADRs
record what is possible and what is forbidden; the services record how results
are stored so that any caller can produce them. Neither records what a manager is
trying to accomplish, in what order, or why one arrangement of a screen serves
that better than another.

**The clearest instance.** The user asked how push and email fields are kept from
being mixed up in an authoring form — a workflow question. It was answered by
investigating where field-to-channel knowledge lives in the backend — a
data-modelling question. The investigation was accurate and answered the wrong
thing.

---

## Established up front (don't re-litigate)

**The client.**
- [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] — plain React
  SPA, routing called as a library, types generated from the schema.
- [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]] — session
  cookie, `X-CSRF-Token`, same-origin serving.
- [[ADR-173 — The Manager Client's Runtime Dependencies]] — React Aria for
  behaviour and accessibility, plain CSS for appearance, TanStack Query.
- [[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]] —
  a screen never asks which brand it is in; it asks what it can see.

**Channels and content.**
- [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]].
- [[ADR-160 — Channel Model and Composition]] point 3 — channel readiness is a
  property of the content record; channel fields separate and required, **never
  derived from email fields**.
- [[ADR-161 — Channel Execution Shapes]] point 7 — provider `.py` = capabilities ·
  module manifest = fields and limits · channel = a variant attribute plus which
  manifests it accepts.
- [[ADR-162 — Channel Rendering and Artifacts]] point 1 — the variant holds no
  channel fields; **no second home for channel fields beside the manifests**.
- [[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]].

**Already ruled elsewhere.** [[Omni-Channel - design interview]] Cluster 1
question 2 judged channel grouping *"a **display** concern — the UI groups by
channel — not a model one."* **That** the UI groups by channel is settled; **how**
it groups is question 2.2 below.

**Established 2026-09-21 (user), and it settles a parked conflict.**
> *"There is no case that a content field on a content exists BEFORE there is a
> module/layout. So grouping UI based on the module channels will be fine."*

So content fields never precede the module that renders them, and **the module
manifests are the correct source for grouping**.
[[ADR-161 — Channel Execution Shapes]] point 7 holds as written, and
[[ADR-162 — Channel Rendering and Artifacts]] point 1 is not violated.
**Consequence for the backend:**
`CONTENT_FIELD_GROUPS` (`backend/app/content/service.py:101-108`) should read from
the manifests rather than repeat them — which is precisely what its own docstring
asks for — and the duplicate list in `backend/scripts/import_content_csv.py:33-41`
goes with it. No ADR needed; this implements ADR-161 point 7.
**Not covered by this**: the descriptive/filtering metadata in questions 2.8–2.10,
which is a different concept and remains open.

**Established 2026-09-21 (user) — categories are for affinity, and nothing else.**
> *"CategoryDB and the whole 'categorize content' is ONLY meant for the 'build a
> dynamic affinities profile of each recipient'. Anything that shows up in
> CategoryDB is meant to be used to build this profile (main/sub)."*

Consistent with [[ADR-080 — Human-governed Taxonomy Before AI Selection]], which
makes categories the governed taxonomy for content *selection* and says nothing
about finding anything. Categories are consumed by `insight/signals.py`, both
decision strategies, and audience rules — all machine-facing.

**The requirement this leaves uncovered, and it is a different concept.** A
manager cannot work a flat table of a hundred thousand content records, and the
campaign builder currently offers *"a dropdown with all content record ids"*.
Free-text search helps and is not enough; what is needed is **filtering along the
manager's own way of grouping content** — the user's examples: B2C versus B2B,
IATA destinations or countries or regions, product information versus company
information. *"Only they can decide how they typically group content."*

**The boundary is the load-bearing part.** If such a label can reach the decision
engine it *is* a category and ADR-080 already governs it. If it must never, the
separation has to be structural rather than conventional — nothing stops somebody
reusing `CategoryDB` today, and a manager tagging content "B2B" there would
silently make "B2B" an affinity dimension. Questions 2.8–2.13 are open.

**The screen cut.** Sixteen screens (core loop plus supporting), per the
inventory. Diagnostics and sub-pages are out. Administration is last.

---

## Where the frontend already stands

Built and committed as of 2026-09-21. **The ⚠️ decisions were made by the
implementer, not by anyone who uses this product**, and are in scope to overturn.

| Built | Status |
|---|---|
| Sign-in, two-step code flow | Follows ADR-151 §2's uniform response. Not a workflow question. |
| Shell, brand switcher, sign-out | Switcher hidden when `switchable` is false, per ADR-150 pt 4. |
| ⚠️ **Approvals as the landing screen** | Justified from ADR-169, which is about the *model* of flows, not what a manager opens first. **A guess** — question 1.1. |
| ⚠️ **Table columns on all four lists** | Name/status/updated, chosen by the implementer. No basis — questions 2.1, 3.1. |
| ⚠️ **Campaign rows do not navigate** | Defensible (B11 unbuilt) but a design call — question 3.1. |
| ❌ **Content fields as one flat list** | **Confirmed wrong** by the 2026-09-21 ruling above: grouping follows the module channels. Fix is blocked only on question 2.2's presentation. |
| Approval detail reads `may_decide` | Correct — the rule stays on the server per the inventory. |

Deliveries is **absent**: its read surface is snapshot-scoped only, with no list
route and no get-by-id, so it is unbuildable today. Logged with C8.

---

## Sketch (not decided — input to the interview)

A manager's day looks like *"what needs me?" → "make the thing" → "who gets it?"
→ "send it" → "what happened?"*. The clustering follows that shape and was
**approved 2026-09-21**.

---

## Cluster 1 — The daily loop and the home screen

*What a manager opens this for, what is waiting, and what "done for today" means.*
Screens: **approvals**, **approval detail**, the shell itself.

1. **What does a manager open this client for on an ordinary day, and what is the
   first question they need answered?**
   *Lean, and it is the guess currently shipped: "does anything need me", which is
   why approvals is the landing screen. If the honest answer is "I am working on
   the October newsletter", the landing screen is wrong and the campaign is the
   unit of work.*
2. **Is there a state that means "done for today"?** An empty inbox, a campaign
   reaching a status, or nothing — the work being continuous?
   This decides whether any screen should show a completion signal at all.
3. **What arrives in the approval inbox, and from whom?**
   *Cluster 2 question 6b added a second input type: an integration asserting a
   content record is ready for a channel. That may be high-volume — an agency
   delivering forty records is forty held actions — and could swamp the send
   approvals this inbox was built for. Grouping, filtering or separation may be
   needed; the current single list has none.*
   *Constraint: [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]
   point 3 makes "a person" and "an integration" durably different actors, and the
   inbox shows the type today.* Is that distinction something a manager acts on,
   or noise?
4. **What must a person see before deciding?** The server describes each request
   as label/value `rows`; the client renders them generically. Is a generic
   description enough, or do specific request types need their own presentation?
5. **Do approvals need a comment or a conversation?**
   *Constraint: `PendingActionDB.decision_reason` exists (1000 chars, nullable) and
   is written **at decision time by the decider**. There is nothing for a
   requester to say why, and no thread.* The user named "some approval comments"
   as a want — is that the decider's reason, a requester's note, or a back-and-forth?
6. **After a decision, does the manager need to see what happened?** Approving a
   send fires it. Is the outcome the approver's business, or the sender's?
7. **When a request expires unnoticed, who needs to know?**
   *Constraint: expiry is bookkeeping run by a scheduler; approving already
   refuses an expired request whether or not it ran.* Is a missed approval a
   failure a manager must see, or a non-event?
8. **What is the nav order, and does the landing screen belong in it?**
   Currently Approvals · Campaigns · Content · Audiences, with Approvals also the
   landing screen. Both are the implementer's choice.

---

## Cluster 2 — Authoring content across channels

> **A principle emerged across questions 2, 3, 3b, 4b and 5 rather than being
> asked for, and it should be checked against every remaining screen decision:
> the system reports, the manager decides.** The system does not collapse a
> section because it looks empty, does not infer readiness from filled fields,
> does not un-assert what a person asserted, and does not nag about a gap. It
> makes facts visible — at the moment they bite — and leaves the judgement to the
> person. Where a signal is genuinely load-bearing it becomes a **check at the
> point of action** (question 3b's send-time required-field check), not a nag
> earlier on.


*How one message becomes email and push without the two being mixed up.*
Screens: **content list**, **content detail**, **categories**, **category detail**.

1. ✅ **Is a content record one message expressed in several channels, or is a
   push message a different record from the email message?**
   **Resolution (2026-09-21): one record carries every channel's fields.** The
   beach article is one record with email fields and push fields on it, and the
   work reads *"write the beach article, then give it a push title"*.
   **Established with it:** [[ADR-160 — Channel Model and Composition]] point 3
   holds exactly as written — channel readiness is a property of the record, which
   only parses because one record can be ready for some channels and not others.
   No ADR change. The two alternatives are closed: separate per-channel records
   would have left the "same story" relationship unmodelled, and a parent/child
   structure would have added a level that decision slots, rendering and
   [[ADR-128 — Version Content for Auditability and Restoration]]'s versioning all
   have to learn.
   **Known cost accepted:** a record accumulates every channel's fields, so the
   authoring surface grows with each channel added — which is what makes
   question 2 a real question rather than a styling choice.
2. ✅ **When a manager opens a content record, how are the channel field groups
   presented?**
   **Resolution (2026-09-21): labelled sections, every channel always visible,
   with manual collapse.** Sections down the page, not tabs. A manager may
   collapse some or all of them — *"if a manager quickly needs to get to the last
   section"* — and that is the only thing that ever collapses one.
   **Established with it, and it is the part that generalises: collapse is a
   navigation aid the manager controls, never a state the system infers.**
   Explicitly **no auto-collapse on empty**. The system does not get to decide a
   channel is irrelevant because it currently has no values, and hiding emptiness
   is how a record comes to look finished when it is not. Tabs were rejected for
   the same reason — they put "push is empty" behind a click.
   **Known cost accepted:** the page grows with every channel added, which manual
   collapse mitigates rather than solves.
   **Rider, still open:** field order within a group is currently **JSON insertion
   order** — an accident of how the record was written. The manifest declares an
   order; using it is the obvious fix but has not been decided.
3. ✅ **What makes a content record "ready for push", and who needs to know?**
   **Resolution (2026-09-21): asserted by the manager, per channel, like
   publishing.** Filling the fields is not the same as saying the record is ready
   to go out on a channel. A manager marks it deliberately, and the decision
   engine trusts that mark rather than inspecting fields.
   **Established with it:** readiness becomes **explicit per-channel state on the
   content record**, which strengthens [[ADR-160 — Channel Model and Composition]]
   point 3 — readiness was already "a property of the content record", and is now
   a stored property rather than a derived one. It is a **different axis from
   `status`**, which stays the record's own lifecycle (`active`/`inactive`).
   **This makes an ADR-161 rider wrong and it must be corrected rather than
   quietly ignored.** [[ADR-161 — Channel Execution Shapes]] point 7 states
   *"catalogue readiness is 'push fields not empty'"*. That is now false: readiness
   is asserted, not computed. The rider was never implemented, so nothing breaks —
   but the record says something this interview has decided against, and a dated
   addendum is owed.
   **Known cost accepted, and it needs a rule:** the fields and the flag can
   disagree in both directions — filled but never marked, or marked and then a
   required field emptied. Question 3b decides what happens in the second case.
3b. ✅ **When a record is marked ready for a channel and a required field for
   that channel is later emptied, what happens?**
   **Resolution (2026-09-21): warn, keep the mark, and let the send catch it.**
   The manager asserted readiness and the system does not silently overrule them.
   The record shows a warning — *marked ready for Push, but `push_title` is
   empty* — wherever it appears.
   **Established with it:** this is question 2's principle applied
   again — **the system does not infer state on a manager's behalf.** Auto-unmark
   was rejected for exactly the reason auto-collapse was: it undoes a deliberate
   act, and a manager clearing a field to retype it would silently lose the mark.
   **This produces a backend requirement the interview discovered, and it is not
   optional.** "Let the send catch it" presumes something checks, and **nothing
   does**: `resolve_module_variables` defaults a missing field to `""` and
   `ModuleVariable.required` is never enforced at render, so today an empty push
   notification ships to a real device without a single warning. A required-field
   check must exist **before a send fires**, and where it belongs is
   Cluster 5 question 1's pre-flight. Logged as a gap, not a preference.
   **Known cost accepted:** an unresolved warning can travel all the way to the
   send, so the warning alone is not a control — the send-time check is.
4. ✅ **Does a manager fill a channel's fields speculatively, or only once a
   variant on that channel is being composed?**
   **Resolution (2026-09-21): both must work, and the product should favour
   catalogue-first without forcing it.** The user:

   > *"This is 'today' — teams don't have time and think 'campaign first', so they
   > start writing content for that campaign. More sustainable is content is
   > created first and for all channels, so it's easier and faster for human or ai
   > to build campaigns; also does a decision engine demand as much
   > variety/options as possible. Content creation can also easily be outsourced
   > to an agency or to an ai agent."*

   **Established with it, and it is a product principle rather than a screen
   decision: the decision engine's value is proportional to catalogue depth.**
   Campaign-first authoring produces exactly enough content for one campaign,
   which leaves a decision slot with nothing to choose between — the engine
   degrades to a fixed pick and the personalisation the platform exists for
   quietly stops happening. Nothing in the repo says this, and it explains why
   [[ADR-084 — Decision Slots May Resolve One or Multiple Content Records]] and
   the whole decision layer assume a catalogue rather than a campaign's worth of
   content.
   **Consequences for the client.** The **content screen is the primary authoring
   surface** and stays full-featured; the **campaign builder needs an edit-in-place
   path** as an accommodation for how teams actually work today, not as the
   intended route. Neither screen may assume it owns authoring. Whether the
   product should *show* catalogue depth — how much choosable content exists per
   channel — is a new question, 4b.
   **It also answers part of question 6 in advance:** content creation is
   explicitly outsourceable, to an agency or to an AI agent. So the author is not
   necessarily a manager with a session, and may not be a person at all — which
   makes authoring a **machine-plane** concern as well as a screen.
4b. ✅ **Should the product show how deep the catalogue is, and where?**
   **Resolution (2026-09-21): at the decision slot, and silent everywhere else.**
   Show the candidate count where the decision is configured — *"this slot
   resolves against 4 push-ready records"* — because that is the moment a manager
   can see whether there is anything to personalise with. The content screen does
   **not** carry a catalogue-health view; a number there addresses the wrong
   reader at the wrong moment.
   **Established with it:** starvation is now a named failure mode. A slot
   resolving from two candidates is not broken and looks identical on screen to
   one resolving from two hundred — it simply stops personalising. Making the
   count visible at the slot is what turns that from invisible into obvious.
   **This is the second hard gap the interview has found.** The decision module
   exposes exactly two routes — `GET /decision/strategies` and
   `POST /decision/slots/{id}/execute` — and **execute resolves for real and
   writes a `DecisionResolution`**, so it cannot be used as a preview. There is no
   way to ask "how many records would this slot choose between" without causing a
   decision. A **read-only candidate count** is owed, and it belongs with the
   decision slot detail screen in Cluster 3.
   **Two things it needs that now exist because of question 3.** Counting
   "push-ready" candidates requires the per-channel readiness that question 3 made
   explicit state — before that resolution there was nothing to count. And
   [[ADR-160 — Channel Model and Composition]] point 3's promise that slots filter
   candidates to channel-ready records, which `top_score` declares
   `candidate_filter_fields` for but does not implement, finally has something
   concrete to filter on.
   **Open, deliberately:** what counts as "thin". The count alone may be enough
   and a threshold may be the system inferring again — the shape question 2
   rejected.
5. ✅ **A new channel is registered. Several hundred existing records have no
   fields for it. What happens?**
   **Resolution (2026-09-21): a filter — the gap is workable, not nagged about.**
   Those records are simply not ready for the new channel, and a manager can
   filter to "not ready for WhatsApp" when they decide to work on it. No banner,
   no badge, no rollout queue, no progress bar.
   **Established with it:** **per-channel readiness is a filter dimension**, which
   ties question 3's asserted state to the findability work in questions 8–13.
   Those are not two separate features — the filter surface must carry at least
   two kinds of dimension: **system dimensions** (readiness per channel, `status`)
   and **manager dimensions** (whatever questions 8–13 decide tags are). That is a
   constraint on the filter model, and it arrived from a question that was not
   about filtering at all.
   **Sequencing that falls out:** this answer cannot be built before questions
   8–13 are settled, because it is a filter and there is no filtering yet.
   **Known cost accepted:** nothing prompts anyone, so a channel can stay
   thinly-served indefinitely. Accepted because the prompt would be wrong more
   often than right — question 4b already puts the signal where it bites, at the
   decision slot.
6. ✅ **Who authors content, and does authoring need its own permission?**
   **Resolution (2026-09-21): the same people, no new permission — and
   outsourcing goes through the machine plane.** A person who may edit content may
   edit all of its channels; there is no per-channel authoring right and no split
   between writing and governing. An agency or an AI agent authors as an
   **integration**, with its own credential, grants and audit actor.
   **Established with it:** nothing new enters the permission model, and adding a
   channel stays the two files [[ADR-160 — Channel Model and Composition]] point 6
   promises rather than also adding permissions, roles and grants.
   [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] already
   carries this: an integration is a principal in the same access model, with a
   durable audit identity, so "who wrote this push copy" has an answer without a
   new concept. **Assignment and handoff are rejected with it** — the product does
   not gain an ownership or "waiting on" concept.
   **Consequence that is now a requirement, not an option: the content write API
   must be complete enough for an agency to work through it**, because that is the
   stated outsourcing path rather than a hypothetical one. Whatever the authoring
   screen can do, the JSON plane must also do.
6b. ✅ **May an integration mark a record ready for a channel, or is that a
   human act?**
   **Resolution (2026-09-21): an integration may assert it, and the assertion
   routes through the approval inbox.** An agency or AI agent marking a record
   ready creates a held action; a person decides it. A **person** marking a record
   ready is not held — the same shape as firing a send, where a person doing it
   *is* the approval.
   **Established with it:** this reuses [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §4's held-action machinery rather than inventing a review
   concept, and it honours [[ADR-082 — AI May Recommend but Not Publish]] without
   needing an exception — the machine still recommends, the person still publishes.
   **Third backend requirement from this cluster, and it is concrete.** A new
   approvable action is owed in `backend/app/approvals/actions/`, which today holds
   exactly two — `send.fire_send_instance` and `ai.apply_subject_preheader`. It
   needs an `APPROVABLE_ROUTES` entry in `app/auth/policy.py` too: that table is
   **fail-closed by omission**, so without one a machine asserting readiness gets a
   hard 403 rather than a hold.
   **Known cost accepted, and it lands on Cluster 1:** the approvals inbox gains a
   second, potentially high-volume input. Content review could swamp the send
   approvals the inbox was built for. **Cluster 1 questions 1, 3 and 8 must be
   answered knowing this** — an inbox carrying both "approve this send" and
   "forty records are ready for review" may need grouping, filtering, or a
   separation the current single list does not have.
   **It does validate one thing already built:** the approval detail screen renders
   the server's `rows` generically rather than knowing action types. A second
   action type arriving is exactly the case that design was for.

### Finding content at scale — questions 8–14

*Possibly its own cluster.* These share a surface with the questions above and
nothing else: they are about **finding** a record, not authoring one, and they
reach into Cluster 3's campaign builder and arguably Cluster 4's audience list.
Split them out if that reads better — the clustering is still yours to change.

8. ✅ **Is the manager's grouping one flat pool of tags, or several named
   dimensions?**
   **Resolution (2026-09-21): named dimensions, each with its own values.** The
   adopter declares the axes they think in — *Audience: B2C · B2B*, *Destination:
   Lisbon · Porto*, *Type: product · company* — and filtering composes across
   them: "Audience is B2B **and** Destination is Lisbon". A flat tag pool was
   rejected: it cannot express "which destination?", and nothing stops `lisbon`,
   `Lisbon` and `LIS` coexisting.
   **Established with it, and it settles a constraint from question 5: system
   dimensions and manager dimensions share one model.** Readiness-per-channel and
   `status` are further axes rather than a separate filtering mechanism, so there
   is one filter surface and one way to think about it.
   **Known cost accepted:** somebody must declare the dimensions before anybody
   can tag, which is question 9.
   **Rider, deliberately not assumed:** values are **flat within a dimension** —
   the nested option was not taken. The IATA example *was* hierarchical, and the
   two reconcile if Region, Country and Destination are modelled as three
   dimensions rather than one nested one. **The tradeoff that creates:** a record
   tagged `Destination: Lisbon` does not automatically satisfy `Country: Portugal`
   unless it carries that too, so either the tagger repeats themselves or
   something derives the broader value. Worth deciding before this is built;
   flagged rather than resolved.
9. ✅ **Who declares the dimensions and their values, and is the vocabulary
   shared or personal?**
   **Resolution (2026-09-21): shared and governed — an administrator declares
   them.** Dimensions and their values are set up deliberately and everyone sees
   the same ones. Personal saved views were rejected, and correctly: they would
   have made an agency's tagging invisible to everyone else, which breaks the
   outsourcing path question 6 established.
   **This answers the backend-or-frontend question definitively: it is a backend
   feature.** A new model is owed — dimensions, their values, and the links from
   content records to values — plus lifecycle rules the flat-tag option was
   rejected for needing anyway: renaming a value, merging two, retiring one, and
   what happens to tagged content when a value is deleted.
   **It needs an administration surface that does not exist.** Declaring
   dimensions belongs in Settings, and Settings is **gap C2** — there is no
   `app/settings/router.py` and no `app/ai/router.py`, so the entire settings
   surface is UI-only. This work now has a dependency on closing that gap.
   **Known cost accepted:** setup before value. An adopter gets nothing from this
   until somebody has declared the axes they think in.
9b. **Are dimensions global, or per brand?**
   *Raised by question 9, and there is precedent pointing both ways.*
   [[ADR-150 — Tenancy and Access Model]]'s 2026-09-15 addendum makes categories
   deliberately **unbranded** — `CategoryDB` carries no `brand_id`, and the policy
   table states the reasoning: *"Content is per-brand; what a category MEANS is
   not."*
   That argument is about **affinity semantics** and does not carry to
   **findability**. Two brands share what "Beach" means as an interest; they do
   not share how they file their work.
   **Resolution (2026-09-21): per brand — with a named consequence for
   duplication.** The user: *"Best would be per brand, but this means duplicating
   campaigns/content is only possible if they have shared values or the
   duplication wizard allows reassignment."*
   **Established with it:** an airline brand's axes (Destination, Cabin) and a
   hotel brand's (Property, Season) have no reason to be one list, and forcing a
   shared vocabulary would couple brands [[ADR-150 — Tenancy and Access Model]]
   otherwise keeps apart. This **departs from the category precedent
   deliberately**, so the addendum that made categories unbranded needs a sentence
   saying why findability differs from affinity — the reason being that a category
   carries meaning about a *recipient*, while a dimension carries meaning about
   *how a team works*.
   **The duplication consequence is real, and the mechanism for it already
   exists.** Cross-brand duplication is a built feature, not a hypothetical:
   `duplicate_campaign` (`backend/app/campaigns/duplication.py:127`) takes
   `source_brand_id` and `target_brand_id`, exposes a `crossed_brands()`
   predicate, and runs two modes — `KEEP` within a brand, where modules reference
   the same records, and `COPY` across brands, where records must be duplicated
   because a record carries one `brand_id`. Per-brand dimensions mean a copied
   record's tags may name values the target brand does not have.
   **That is the same shape the duplication result already handles:** it reports
   *"places a brand-specific URL came across verbatim, as readable labels"* — a
   list of things that crossed and need a human look. Unresolvable dimension
   values belong in exactly that list, so **the duplication wizard allows
   reassignment** rather than refusing the copy or silently dropping the tags.
   **Known cost accepted:** a multi-brand adopter redeclares common axes per
   brand, and a cross-brand copy gains a reassignment step.
10. ✅ **How many content records, realistically?**
    **Resolution (2026-09-21): it varies, and the product must not assume.**
    A reference architecture is copied by adopters of very different sizes, so the
    API paginates and filters server-side regardless — including for the adopter
    who will never need it.
    **Fourth backend requirement from this cluster, and the broadest.** Every list
    route the client uses calls `.all()` with no limit, offset or filter
    (`content/service.py:219-235` and its equivalents). Pagination and server-side
    filtering become a **precondition for these screens existing**, not an
    optimisation — and every dimension filter, readiness filter and search from
    questions 8–9 is a query parameter the backend must accept. **This shapes the
    API before the screens are built**, which is Phase 0's lesson again: schema
    changes are cheap before a typed client exists and expensive afterwards.
    **It reprices an existing backlog item.** `.all()` with no pagination is
    logged as **P3-02** from the 2026-08-07 review, scoped there as latent scaling
    in a `performance-notes.md` that was never created. At this posture it is not
    a performance note — it is a blocker on the core workflow, and it applies to
    campaigns, audiences, recipients and approvals as well as content.
    **It also invalidates part of what is already built.** Phase 2's four list
    screens fetch everything and render it. They will need server-side filtering
    and paging, which is the cost of having built them before this interview ran.
    **Known cost accepted:** an adopter with two hundred records pays for
    machinery they do not need. Accepted because the alternative is that somebody
    hits a wall silently, having copied an architecture that looked fine.
11. **What should the campaign content picker be, instead of a dropdown of every
    id?** Search, filtered browse, recently used, or narrowed to what the module
    or decision slot can actually accept?
    *This is the same requirement as question 3.5 and they should be answered
    together — it is the harder of the two surfaces, because the manager is
    mid-composition and not browsing.*
12. **Does the same grouping apply to anything other than content?** Campaigns
    and audience groups have the same findability problem at scale. If one scheme
    serves all three it is a platform concept; if content-only, it lives in the
    content module.
13. **What is this called?**
    *Constraint: "category" is taken by ADR-080's governed taxonomy, and this
    repo's vocabulary should not carry one word for two concepts.* The user's
    suggestion is **tags**. Labels, facets and keywords are the alternatives, and
    the word chosen ends up in the API, the UI and the playbook.
14. **Is "in feedback loop / waiting for feedback" one of these, or a lifecycle?**
    *Constraint: `status` on a content record is already a lifecycle, constrained
    to `active`/`inactive` (`content/service.py:85`).* A lifecycle implies
    transitions and who may make them; a tag does not. The original example named
    both in one breath, and they may not be the same thing.

---

## Cluster 3 — Composing a campaign

*What gets assembled, in what order, and what campaign detail is actually for.*
Screens: **campaigns list**, **campaign detail** (inventory B11), **decisions**,
**decision slot detail**.

1. **What is a manager looking for in the campaign list, and what should a row
   click do?** Currently rows show name/status/updated and do not navigate.
2. **What is the unit of work — the campaign, or a variant?**
   *Constraint: [[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]]
   makes a flow a sequence of variants, and a variant carries both "A/B version"
   and "channel expression".* If the variant is the unit, campaign detail
   is an index rather than a workspace.
3. **Campaign detail is the largest derived-state screen in the product
   (inventory B11). What must be visible at once, and what can be a click away?**
   The derived state is: overrideability, module limits from the channel manifest,
   audience counts per channel, and providers filtered by channel. All of it is
   presentation the client computes for itself.
4. **In what order does a manager build a variant?** Pick channel → add modules →
   fill them? Or find content first and compose around it?
   *Constraint: channel is fixed at variant creation and has no setter.*
5. **How does a manager find the right content record while composing?**
   *Answered together with questions 2.8–2.13, not separately.* The picker is a
   dropdown of every content record id today, which the user names as not working
   past a few hundred records. This is the harder of the two surfaces: the
   manager is mid-composition, not browsing, and may only want content the module
   or slot can actually accept.
6. **When does a manager reach for a decision slot instead of fixed content?**
   Is personalisation a deliberate act per slot, or the default for some module
   types?
7. **What does a manager need to see about how a slot resolved?**
   *Constraint: [[ADR-085 — Decision Resolution Should Be Optionally Explainable]]
   makes explainability optional.* Is the explanation something a manager reads
   routinely, or only when something looks wrong?
8. **Duplicating a campaign — when is it used, and what should it carry?**
   The inventory treats it as a dialog rather than a screen.

---

## Cluster 4 — Choosing who receives it

*How a manager decides the audience, and what they must verify before trusting it.*
Screens: **audience groups**, **audience detail**, **recipients**,
**recipient detail**.

1. **How does a manager arrive at an audience?** From scratch, by copying a
   previous one, or from criteria the system suggests?
2. **Rule blocks or explicit members — which is the normal case, and which is the
   exception?** Both exist. The screens should not present them as equals if the
   work does not.
3. **What must a manager verify before trusting an audience?** A count, a sample
   of who is in it, or the rules restated in prose?
4. **The resolved count differs per channel, and the manager may not expect that.**
   *Constraint: `resolve_audience` is consent-gated and channel-dependent, so the
   same group yields different recipients for email and push.* Does a manager need
   to see exclusions and why, or only the final number?
5. **Recipients are a projection of a CRM, not a CRM.** What does a manager
   legitimately do on this screen that is not done in the source system?
   *Constraint: [[ADR-120 — CRM as Customer Source of Truth]] and
   [[ADR-126 — Maintain Local Recipient Projection]].*
6. **What does a manager need from the consent grid?**
   *Constraint: consent is per `(brand, channel, purpose)`; `Recipient.email` and
   `email_consent_status` are the flattened email cell of each.* Is this a
   read-only fact, a support-request surface, or something a manager edits?
7. **When and why does a manager press Recalculate?** Is it routine, or does it
   exist because something went wrong?

---

## Cluster 5 — Planning, checking and firing a send

*What a manager confirms before real mail leaves, and what they watch afterwards.*
Screens: **deliveries**, **delivery detail**.

1. **What does a manager confirm before real mail leaves?**
   *Cluster 2 question 3b landed a hard requirement here: a record can be marked
   ready for a channel while a required field for it is empty, and nothing
   currently checks — `ModuleVariable.required` is never enforced at render, so an
   empty push ships silently. A required-field check before firing is owed, and
   this is where it belongs.*
   The pre-flight list is the screen's whole reason to exist, and nothing records
   it. Snapshot, audience count, provider, from-address, schedule — all of them,
   or a subset with the rest available?
2. **Is `freeze` versus `rerun` a manager's choice, or a deployment default?**
   *Constraint: freeze fixes the recipients now; rerun re-resolves immediately
   before firing.* If it is a choice, it needs explaining at the moment it is
   made; if a default, it belongs in settings and not on this screen.
3. **Does a manager schedule sends, or fire them?** Both exist. Which is the
   normal path decides whether the screen leads with a date or a button.
4. **What question does the deliveries list answer?** What is scheduled, what went
   out, what failed — or all three in one list with a filter?
5. **What does a manager watch during and after a send?**
   *Constraint: `SendInstanceDB` carries `sent_count`, `failed_count` and
   `excluded_count`; the `SendInstance` response model exposes **none of them**.*
   What is watched determines what the read routes must return.
6. **A send that fails partway — what does the manager do?** Retry the failures,
   start again, or is it the operator's problem rather than the manager's?
7. **Where does a test send belong?** The inventory calls send-test a diagnostic
   for the deployment docs. *If a manager sends a test to themselves before every
   real send, that is wrong and it is part of the pre-flight.*
8. **When is the approval gate on a send actually used?**
   *Constraint: [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §4;
   `send.fire_send_instance` is the only approvable action, and a person firing a
   send **is** the approval.* Is the gate for machines only, or do people route
   sends to a colleague too?

---

## Related

- [[Omni-Channel - design interview]] — the model this document copies, and the
  source of the "UI groups by channel" ruling
- [[AI Layer - design interview]] — the first document in this genre
- `docs/react-screen-inventory.md` — what each screen needs from the API, and the
  statement that the design questions are deliberately left open
- [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]]
- [[ADR-160 — Channel Model and Composition]]
- [[ADR-161 — Channel Execution Shapes]]
- [[ADR-162 — Channel Rendering and Artifacts]]
- [[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]]
