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
> written out — 41 questions, 1 resolved. **No further frontend work before
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

*How one message becomes email and push without the two being mixed up.*
Screens: **content list**, **content detail**, **categories**, **category detail**.

1. **Is a content record one message expressed in several channels, or is a push
   message a different record from the email message?**
   *Constraint: [[ADR-160 — Channel Model and Composition]] point 3 makes channel
   readiness a property of the record. Lean: one record — strengthened by the
   2026-09-21 ruling that fields follow modules.*
   The workflow question: *"write the beach article, then give it a push title"*,
   or *"write the beach email; separately, write the beach push"*?
2. **When a manager opens a content record, what do they see first?**
   Grouping follows the module channels (settled). **The presentation does not:**
   email and push as labelled sections both always visible, tabs one channel at a
   time, or only the channels already filled?
   *Lean: sections rather than tabs, so "push is empty" is visible without a
   click — but that presumes emptiness is something a manager needs to see, which
   is question 3.*
   Field order within a group is currently **JSON insertion order**, an accident
   of how the record was written. Should it follow the manifest's declared order?
3. **What tells a manager a record is ready for push?**
   *Constraint: [[ADR-161 — Channel Execution Shapes]] point 7's rider says
   catalogue readiness is "push fields not empty" — **not implemented anywhere**.*
   Computed and displayed, or asserted by the manager the way `status` is? And is
   "not ready" a warning, a filter, or a neutral fact?
4. **Does a manager fill channel fields speculatively, or only when a variant on
   that channel is being composed?**
   Decides whether the content screen is channel-shaped from the start, or whether
   channel fields are authored from the campaign instead.
5. **When a channel is added later, what happens to existing records?**
   Adding a channel is two files. Several hundred records would have no fields for
   it. A backlog a manager works through, a filter, or invisible until needed?
   *No lean.*
6. **Is the person writing email copy the same person writing push copy?**
   Bears on one screen or two, and on whether channel authoring needs a permission
   — today it has none. If they differ, "push is empty" is a **handoff**, not a
   warning.
7. ✅ **Are categories authored alongside content, or managed separately?**
   **Resolution (2026-09-21): alongside content.** *"Categorizing happens on the
   content, not in the campaign context"* (user). **Established with it:**
   categories stay in this cluster rather than moving to Cluster 3, and the
   category screens are an authoring surface rather than administration.
8. **Is there content metadata that exists only for finding and tracking — not
   for rendering, and explicitly not for affinity?**
   The user named: *"labels about 'is in feedbackloop / Waiting for feedback',
   some approval comments, different producttypes or categories that are not
   interesting for the affinity profile, but is for filtering."*
   *Constraint, and it is the crux: `CategoryDB` exists to feed decision-slot
   candidate filtering — i.e. affinity. Its `type` column is `main`/`sub`, a
   **hierarchy level**, not a purpose, so there is no seam for a non-affinity
   label today.* A label that must **not** influence what the decision engine
   picks is a different concept from a category, and nothing models it.
   Is this a second kind of category, a workflow status on the record, free tags,
   or something else?
9. **Where does that metadata have to be visible, and does it have to persist?**
   The user named two places: finding a record **in the content table**, and
   finding one **while building a variant in a campaign**. The second is the
   harder requirement — it means the metadata travels into Cluster 3's screens.
   *This is the question that decides backend or frontend.* A saved view or a
   client-side filter needs no backend at all; a shared label that another person
   sees, or one that persists across devices, is a backend concept.
10. **Is "in feedback loop / waiting for feedback" a lifecycle, or a label?**
    *Constraint: `status` on a content record is already a lifecycle, constrained
    to `active`/`inactive` (`content/service.py:85`).* Is the feedback state a
    third value of that, a parallel field, or one of the free labels in question 8?
    A lifecycle implies transitions and who may make them; a label does not.

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
   *This is where question 2.9's metadata has to arrive.* Search, category filter,
   recently used, or something the campaign already knows?
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
