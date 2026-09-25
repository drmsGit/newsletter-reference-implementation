---
type: interview-prep
topic:
  - architecture
  - frontend
  - design
  - variant
created: 2026-09-24
modified: 2026-09-25
status: open
source:
  - "Manager Workflow - design interview, 2026-09-24 — closed 53/53 and did not cover the composer"
---

> **Status: interview OPEN.** Clustering approved 2026-09-24, with two
> corrections from the user: *edit vs override* was promoted to a cluster of its
> own, and the proposed "what a variant is for" cluster was **struck** because
> [[ADR-021 — Variants Are Human Created Versions]] already settles it.
> 36 questions across five clusters, 1 answered.
> **Cluster 1 in progress — 1/7.**

# Variant Editor — design interview (forward-looking)

## Why this came up

[[Manager Workflow - design interview]] closed 53/53 and deliberately stopped at
the composer's door. Cluster 3 asked what a campaign *is* and what campaign
detail is *for*; it never asked what happens when a manager opens a variant and
starts assembling it. That is the largest single screen in the product and the
only one where a manager does something other than look, decide or confirm.

It is also the screen where the previous failure mode is most likely to repeat.
The model supports several workflows equally well, and nothing in the repository
says which one a manager means. Building from the model alone would once again
be converting *what the API allows* into screens and calling it design.

**One question dominates and is why this interview has five clusters instead of
four.** The user's one surviving requirement from their predecessor system:

> *"need to make a change to the content record while orchestrating a campaign?
> a manager doesn't want to switch tabs"*

That sentence and [[ADR-040 — Introduce Override Layer]] describe two different
things. The override layer exists **precisely so that composing a campaign does
not change the catalogue**. So when a manager types into a field in the
composer, where the keystroke lands is a real fork with real consequences for
content reuse, audit, approval and every already-composed campaign. Cluster 3
is about nothing else.

## Established up front (don't re-litigate)

**What a variant is — [[ADR-021 — Variants Are Human Created Versions]] and its
2026-09-12 addendum.** A variant is a deliberately created, reviewable version
of a campaign, never an automatic byproduct of personalization: if a slot
resolves to 80 selections that is 80 renderings of *one* variant. Channel is a
**second, independent sense** that composes with the A/B sense — "Push A" and
"Push B" are each legitimate variants. A variant may be AI-drafted; what makes
it a variant is that it is deliberate and reviewed, not who wrote the first
draft. The flat-list awkwardness this produces is **explicitly a display
concern**, to be solved by grouping in the UI and not by a model concept.
*Only the shape of that grouping is open, and it is question 1.1.*

**Where personalization lives** — [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]
and [[ADR-079 — Dynamic Resolution Outside Builder]]. Slots resolve inside a
variant; resolution does not happen in the builder.

**What a composition stores** — [[ADR-031 — Newsletter Composition Stores Structure Not Content]].
Which content reference, module, position, configuration and override belongs to
a campaign and variant. **It does not own the source content.**

**Channel is fixed at creation** — [[ADR-160 — Channel Model and Composition]]
points 4 and 5. Switching an email variant to push would invalidate its modules,
its content-readiness and its renderer at once, so changing channel means
creating a new variant. Nothing updates `variants.channel`, and it has no server
default.

**A renderer formats and never decides** — [[ADR-162 — Channel Rendering and Artifacts]]
point 2. Everything decided happens in `resolve_module_variables`. Point 1: the
variant holds **no channel fields at all** — subject and preheader are fields of
an *email*, so they live in the composition as a `header` module's declared
variables at position 0.

**A required-field check blocks the send** — [[ADR-174 — Channel Readiness Is Asserted, Not Computed]]
point 3. It belongs in the send review screen's pre-flight and is one of the
narrow set of things that **blocks** rather than informs. *What the composer does
about the same emptiness, earlier, is open — question 2.2.*

**Readiness is asserted, not computed** — ADR-174 point 1, for the content
record. *Whether the same principle governs a variant's readiness is question
4.7, and is not assumed here.*

**A negative decision outranks a positive one** — [[ADR-176 — A Negative Decision Outranks a Positive One]].

**Comments are optional** — Manager Workflow Q1.5, settled 2026-09-24. A manager
is never forced to justify an action. *Whether that survives contact with an
override, which is a deviation by definition, is question 3.8.*

### CampaignStudio is not a blueprint

The user's previous system — a Cloudpage/AMPscript/SSJS frontend on Salesforce
Marketing Cloud — was reviewed on 2026-09-24 as *input*, explicitly not as a
model to follow, and **essentially nothing was taken from it.** Recorded here so
it is not reached for again mid-interview. The user's reasons:

1. its workaround list is very long;
2. it is very business-specific and heavily customised, so copying it means
   building functions a normal company never needs;
3. it works against finding the common ground a blueprint needs — *"enough to
   start fast"* but flexible enough to *"become what your company needs to be"*;
4. a lot is fixed there that should not be — the hero/editorial split, which
   this architecture already has as modules;
5. we can do better, especially on combining screens and on override behaviour;
6. its follow-up, survey and raffle flows are Salesforce-only development work,
   so none of it becomes a screen here.

**Three findings were examined and all three dissolved.** Its per-campaign
content versioning is a webview artefact of serving content from a Cloudpage —
this platform sends finished HTML, and the audit versioning that *is* real
already exists. Its three headline lengths are **not** an artefact but deliberate
editorial discipline, and they map to module variables rather than to a new
concept (*question 2.7*). Its unexplained numeric value is category scoring,
which `ContentCategoryAssignmentDB.score` already carries.

**One requirement survived**, and it is Cluster 3's subject.

## What the model actually constrains

Gathered 2026-09-24 so the interview argues from the code rather than from
memory. These are facts, not decisions.

| Layer | Constraint |
|---|---|
| Variant | `channel` fixed at creation, no server default. `name` is an internal label, never recipient-facing. `status` defaults to `draft` and **no ADR defines its values** |
| Module stack | `UniqueConstraint(variant_id, position)` — a naive reorder collides. `module_type` and `position` are `NOT NULL` |
| Module binding | `content_record_id`, `decision_slot_id` and `module_data` — a `CHECK` enforces that the two FKs are **never both set**, and **all three may be null**, which renders nothing |
| Fields | Filled from the manifest **by exact name**; a missing key defaults to `""`. `ModuleVariable.required` is surfaced to `GET /modules` and **enforced nowhere** |
| Manifest | `ModuleVariable` carries `name`, `required`, `label`, `envelope`. `ModuleVariableOut` **drops `label` and `envelope`** — the API does not expose the authoring form's own field labels |
| Envelope | Which module carries a channel's envelope is **found by reading manifests** for a variable declaring `envelope`, never by special-casing a module name. Push has none — a notification's title is body |
| Overrides | `ContentOverrideDB` is **field edits only**, keyed to a module instance, lifecycle create → active → reset, with `outcome_delta` filled retroactively. Swapping the whole record is **deliberately not** an override |
| Preview | `mode="preview"` vs send, optional `recipient_id`. A slot resolving to nothing emits an HTML comment and **hides the slot** ([[ADR-086 — Decision Slots Fail Gracefully]]) |
| Design | Documented in the reference data model as colours, typography, spacing, footer behaviour — *"Design is not a template"* — and **there is no `DesignDB` table**. It is described, not built |

## Sketch (not decided — input to the interview)

My lean, stated once so it can be argued with rather than leaking into questions:
a single composer screen with the module stack down the left, the selected
module's fields on the right, and preview on demand rather than always-on. I
think the edit/override fork should be **explicit and visible rather than
inferred from context**, because an invisible default here is the kind of thing
that is discovered months later by a manager wondering why last week's campaign
changed. I hold that loosely — it costs a click on the most frequent action in
the product, and that is a real objection.

---

## Cluster 1 — Composing the module stack

*What a manager assembles, in what order, and what a half-built variant is.*

1. ✅ **The variant list groups by channel — what does that actually look like?**
   **Resolution (2026-09-25): channel as a section heading, versions listed under
   it, and no cross-channel view at all.** The user:

   > *"it's a list of what exists per channel. There's no need to see the idea
   > across its channels on that surface (a manager would just open the different
   > variants/channels if needed), strategies differ by channel massively"*

   **Established with it, and it closes the compare view permanently rather than
   deferring it.** The reason given is not that a cross-channel comparison is
   inconvenient to build — it is that **it is not meaningful**. An email A/B test
   and a push A/B test are not two readings of one idea; they are separate
   strategies that happen to share a campaign. So "A" in the email group and "A"
   in the push group are not a pair, and a UI that placed them side by side would
   be asserting a relationship the work does not have.

   **This gives [[ADR-160 — Channel Model and Composition]] point 5 a workflow
   reason to stand on.** That point fixes channel at creation and argues it
   technically — switching channel invalidates a variant's modules, its
   content-readiness and its renderer at once. The answer here says the same
   thing from the manager's side: they were never one object being viewed two
   ways, so there is nothing to switch. Two independent arguments reaching the
   same constraint is the strongest position a decision can be in.

   **It also settles a question the model could not answer.** Nothing links
   "Email A" to "Push A" — there is no shared key, and pairing them would have
   meant inferring a relationship from a free-text internal label. That absence
   now reads as correct rather than as a gap.

   **Known cost accepted:** *"is this campaign running on push yet?"* is easy and
   *"how does the beach angle differ across channels?"* is not answered on this
   surface. Accepted explicitly — a manager who wants that opens both variants.

   **Consequence for the screen cut:** no compare view, no cross-channel variant
   screen, and the variant list is a grouped list rather than a matrix. One less
   screen than the sketch implied.
2. **When a manager adds a module, do they pick the module type first, or pick
   what goes in it first?** *Constraint: `module_type` and `position` are the
   only NOT NULL columns, so the model's grain is type-first. Lean: type-first,
   but I suspect the real workflow is "I want this article in here".*
3. **Does a manager consciously choose between the three kinds of module — static,
   content-bound, decision slot — or is that a consequence of what they picked?**
   *Constraint: the CHECK enforces the two FKs are never both set, but nothing
   makes a manager name the kind.* Is "this slot is personalised" a decision a
   manager makes about a module, or a different kind of thing they add?
4. **What is a module with nothing in it?** *Constraint: all three binding
   columns null is legal and renders nothing.* A deliberate placeholder the
   manager will fill later, an error, or something the editor should not let
   exist?
5. **How does a manager reorder the stack?** *Constraint:
   `UniqueConstraint(variant_id, position)` — swapping two positions collides
   unless the whole reorder is one transaction. That is an implementation
   detail; the question is whether reordering is drag-and-drop, move up/down, or
   explicit numbers, because a drag implies "send me the whole new order" and
   the others imply "send me one change".*
6. **May the same content record appear twice in one variant?** *Constraint:
   nothing forbids it. Lean: allow it — a "featured" and a "more like this"
   block legitimately overlap — but the editor should say so rather than let it
   pass silently.*
7. **Can two people edit one variant at once, and what should happen?**
   *Constraint: there is no lock, no version column and no optimistic
   concurrency on `module_instances`. Last write wins, silently.* Is this a real
   scenario for a manager and an agency, or is single-editor an acceptable
   assumption to state out loud?

## Cluster 2 — Filling a module's fields

*The authoring form itself: where it lives, what it enforces, what it shows.*

1. **Where does a manager fill fields — inline in the stack, a side panel, or a
   separate screen?** This decides whether the composer is one screen or two,
   and it constrains Cluster 3.
2. **A required field is empty. What does the composer do?** *Constraint:
   ADR-174 point 3 already puts the **blocking** check in the send review
   pre-flight, so the composer is not the last line of defence. Lean: show it,
   never block it — an author mid-draft has empty fields by definition.* Does an
   empty required field make the variant look incomplete in the variant list, or
   only inside the editor?
3. **Does the manager see subject and preheader as "the email's subject", or as
   a module's fields like any other?** *Constraint: ADR-162 point 1 made them a
   `header` module's declared variables at position 0, and which module carries
   the envelope is discovered by reading manifests. The model says "module"; a
   manager almost certainly thinks "the subject line".* If the composer promotes
   them to a fixed position at the top of the screen, is that a display
   convenience or a re-introduction of the concept the ADR removed?
4. **Should the API expose `ModuleVariable.label`?** *Constraint: it exists on
   the dataclass and `ModuleVariableOut` drops it. Its docstring says it exists
   "so a channel added later gets a readable authoring surface from its manifest
   alone" — which is exactly what a generated client needs and cannot currently
   get.* Same question for `envelope`. *Lean: expose both; this is a backend
   gap, not a design decision — but it is worth confirming that the manifest is
   meant to drive the form's labels at all.*
5. **Which fields are rich text, and who decides?** *Constraint: rendering
   special-cases a single field name today. A manifest-declared field type would
   generalise it; a hardcoded name will not survive the second channel.* Does a
   manager need formatting control at all, or is formatting the module's job?
6. **What does a manager see for a module bound to a decision slot?** There are
   no fields to fill — the fields come from whatever the slot resolves to. Is
   this an empty form, a description of the rule, or a sample of what it would
   pick?
7. **Should a module variable declare a length limit, and is it advisory or
   enforced?** *Constraint: no limit exists anywhere today. The user's
   predecessor system enforced three headline lengths and the user was explicit
   that this was **deliberate editorial discipline, not a platform artefact**,
   and that it maps to module variables rather than a new concept. Lean:
   advisory — a counter, not a block, since the same discipline is a house style
   and not a correctness property.*

## Cluster 3 — Edit versus override

*Where the keystroke goes. The cluster this interview exists for.*

1. **A manager is composing a campaign, sees a typo in a headline, and fixes it.
   Where does that change land — in `content_records`, or in
   `field_overrides`?** *Constraint: [[ADR-040 — Introduce Override Layer]]
   exists so the catalogue is not edited during composition, and
   [[ADR-041 — Override Precedence]] makes an override win until reset. But the
   user's stated requirement is literally "make a change to the content record
   while orchestrating a campaign".* A typo is the easy case and both answers
   are defensible: it is wrong *everywhere*, so the catalogue is right; but the
   manager is in a campaign, so the override is what the model expects.
2. **Is it one behaviour or two?** If a manager can do both, what distinguishes
   them at the moment of typing — two fields, a mode, a choice on save, or an
   "also update the original" checkbox? *Lean: two visible actions, because an
   invisible default here is discovered months later.*
3. **If it is two, which is the default?** The default is what most managers will
   do most of the time without noticing they chose.
4. **How does the composer show that a field is currently overridden?**
   *Constraint: ADR-041 — the override wins "until it is deleted or reset", so
   this state is durable and invisible unless the UI says so.* Does the manager
   need to see the catalogue value it is covering?
5. **What is "reset", who can do it, and does it appear anywhere other than the
   composer?** *Constraint: create → active → reset is the modelled lifecycle.*
6. **An override is scoped to one module instance. The same content record in
   another variant is unaffected.** Is that what a manager expects, or is the
   expectation "I fixed it for this campaign" — meaning every module in the
   campaign that uses that record? *This is the one place the model may be
   finer-grained than the mental model.*
7. **Editing the catalogue record changes every composed-but-unsent campaign
   using it.** *Constraint: snapshots pin what was sent, so history is safe —
   the exposure is campaigns already built and not yet fired, including ones
   another person is responsible for.* What must the composer tell the manager
   before that edit — nothing, a count, or a list?
8. **Does an override need a reason?** *Constraint: Manager Workflow Q1.5 settled
   that comments are always optional. An override is a deliberate deviation from
   what the system produced, and `outcome_delta` exists to ask later whether it
   was a good one — which is hard to answer without knowing what was intended.*
   Does "optional everywhere" hold here, or is this the exception?
9. **Is `outcome_delta` a manager-facing thing?** Does the composer ever show
   "the last time you overrode this, it performed worse", or is that purely an
   insight-layer concern that never reaches this screen?

## Cluster 4 — Preview, proof and readiness

*What a manager checks before handing the variant on, and what "ready" means.*

1. **Who is the preview for — the author checking their own work, or the approver
   checking someone else's?** *This decides whether preview belongs in the
   composer, the approval screen, or both, and they are not the same artefact:
   an author wants to iterate, an approver wants proof.*
2. **Preview takes an optional `recipient_id`. Does a manager pick a real
   recipient, pick a segment, or see a generic preview with slots unresolved?**
   *Lean: a real recipient, because a personalised newsletter previewed
   generically is not the thing being reviewed. The cost is that the manager
   must choose one, and whoever they choose is not representative.*
3. **`mode="preview"` and the send path resolve decisions differently. Must the
   composer say so?** A preview that silently differs from what will ship is
   worse than no preview.
4. **A decision slot that resolves to nothing is hidden, not placeheld
   ([[ADR-086 — Decision Slots Fail Gracefully]]). In the composer, should a
   hidden slot be visible to the author?** *Constraint: rendering emits an HTML
   comment, so the information exists.* The recipient must not see a gap; the
   author probably must.
5. **ADR-086 also says that if no meaningful content remains, the email must not
   be sent. Who evaluates "meaningful", and when?** *Constraint: this is
   currently unimplemented. It is a compose-time question and a send-time
   question and they may get different answers — at compose time the slots have
   not resolved for anybody.*
6. **What are `variants.status`'s values, and who moves them?** *Constraint: the
   column defaults to `draft` and **no ADR defines the vocabulary**. The content
   record's `status` is deliberately constrained to exactly two values, with a
   comment refusing to invent a richer vocabulary locally — the same restraint
   presumably applies here.* Does the composer drive status, or does status
   change as a side effect of submitting for approval?
7. **Is a variant's readiness asserted or computed?** *Constraint: ADR-174 point
   1 chose **asserted** for a content record's channel readiness, with the
   reasoning that a computation over fields cannot capture intent. Whether that
   generalises to a variant is genuinely open: a variant's completeness is more
   mechanical — every required field filled, every slot bound — so a computation
   might be honest here where it was not there.* This is the question most
   likely to owe an ADR.

## Cluster 5 — Reuse and repetition

*The weekly newsletter, and everything that is not a first draft.*

1. **How does a manager create a variant — blank, a copy of another variant, a
   saved starting point, or an AI draft?** *Constraint: ADR-021 explicitly
   permits an AI-drafted variant. Lean: copy is the common case and blank is the
   rare one, which is the opposite of what a "New variant" button implies.*
2. **A weekly newsletter goes out every Thursday. What carries over from last
   week?** The structure, the modules with their content cleared, the whole
   thing including last week's content, or nothing? *This is the single most
   common real workflow in email marketing and the model says nothing about it.*
3. **Is a module stack ever saved as a reusable thing?** *Constraint: the
   reference data model describes **Design** as colours, typography, spacing and
   footer behaviour, and says explicitly **"Design is not a template"** — and
   there is no `DesignDB` table, so it is documented rather than built.
   [[ADR-030 — Separate Global and Repeatable Structures]] separates global from
   repeatable structures but does not make either reusable across campaigns.* If
   the answer is yes, this is a new model concept and needs an ADR before a
   screen.
4. **If a saved starting point exists and someone changes it, do existing
   variants follow or stay?** *This is question 3.1 one level up, and the answer
   should probably be the same shape.*
5. **Can a manager copy a variant to another channel — "make a push version of
   this email"?** *Constraint: channel is fixed at creation and the two channels'
   modules come from different manifests, so a copy is not a copy — at best it
   is "carry the content references across and rebuild the stack". Lean: offer
   it, and be honest that it is a starting point rather than a translation.*
6. **Can a variant be copied across campaigns, and across brands?**
   *Constraint: a campaign is composed for one brand ([[ADR-150 — Tenancy and Access Model]]),
   and content records are brand-scoped. A cross-brand copy either breaks the
   boundary or silently drops every content reference.* Lean: within a brand
   only, and say why rather than hiding the option.

## Related

- [[Manager Workflow - design interview]] — closed 53/53; this interview covers
  what it deliberately left out
- [[Omni-Channel - design interview]] — the genre, and the source of the
  that/how split reused in question 1.1
- [[ADR-021 — Variants Are Human Created Versions]]
- [[ADR-030 — Separate Global and Repeatable Structures]]
- [[ADR-031 — Newsletter Composition Stores Structure Not Content]]
- [[ADR-040 — Introduce Override Layer]]
- [[ADR-041 — Override Precedence]]
- [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]
- [[ADR-086 — Decision Slots Fail Gracefully]]
- [[ADR-160 — Channel Model and Composition]]
- [[ADR-162 — Channel Rendering and Artifacts]]
- [[ADR-174 — Channel Readiness Is Asserted, Not Computed]]
- [[ADR-176 — A Negative Decision Outranks a Positive One]]
- `docs/react-screen-inventory.md` — the screens this interview governs
