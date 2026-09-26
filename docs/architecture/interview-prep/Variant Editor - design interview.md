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
> 39 questions across five clusters, 11 answered.
> **Cluster 2 in progress — 3/9** (2.7 and 2.8 answered out of order; 2.9 added).
> **Cluster 1 ✅ CLOSED 2026-09-25, 8/8.**
> **Two questions promoted out of order:** 2.7 was answered in passing during
> question 3, and 2.8 was added by the same message.

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
2. ✅ **When a manager adds a module, do they pick the module type first, or pick
   what goes in it first?**
   **Resolution (2026-09-25): type first, and content-first is not offered as a
   second entry point either.** The user:

   > *"A, because of potential modules without content (divider, headlines that
   > are not connected to the catalog) but also a manager might start setting the
   > layout and not all necessary fields are prepared. In B this would mean a
   > specific layout can't be selected if field values are missing. The hope is
   > that there never are empty fields, but today this is rarely the case"*

   **Two reasons, and the second is the one that generalises.** The first is the
   obvious one: modules that hold no content at all — a divider, a headline not
   drawn from the catalogue — have no content to pick first, so a content-first
   flow cannot create them. The second is sharper: **content-first makes the
   editor's available choices a function of how complete the data is.** A layout
   a manager wants becomes unselectable because a field has not been written
   yet, which inverts the actual working order — the layout is frequently
   decided *before* the copy exists, and the user is explicit that incomplete
   content is the normal state today rather than the exception.

   **The principle underneath: composition must not be gated on content
   readiness.** A tool whose options disappear when the data is thin is at its
   least useful exactly when the work is at its earliest, and a manager who
   cannot select the layout they want will pick one they can — so the constraint
   would quietly change the output, not just the order of work.

   **This is a workflow argument for what the schema already permits**, and it is
   worth naming because the two agree for different reasons. `module_type` and
   `position` are the only NOT NULL columns and every binding is nullable, so
   the model already says a module exists before anything is in it.

   **Carried forward:** it substantially pre-answers question 1.4 (a module with
   nothing in it is a normal mid-state, not an error) and it constrains question
   2.2 — if layout precedes copy, an empty required field is the ordinary
   condition of a draft and cannot be treated as a defect in the composer.

   **Known cost accepted:** the common case — *"I want the beach article in
   here"* — takes two steps rather than one, and a manager must know which
   module shape suits the content they have in mind before they can place it.

   **Still unresolved and logged, not decided here:** fields are filled from the
   manifest **by exact name** and a missing key silently becomes `""`, so binding
   a content record to a module declaring variables that record does not have
   renders blank with no error anywhere. Whether the composer warns about a poor
   fit at bind time is a question for Cluster 2; that **nothing computes fit
   today** is a fact either way.
3. ✅ **Does a manager consciously choose between the three kinds of module —
   static, content-bound, decision slot — or is that a consequence of what they
   picked?**
   **Resolution (2026-09-25): personalisation is configured on the module, in
   place — shape A.** The user:

   > *"Typically A → Manager decides the position and the strategy; potentially
   > it shows a summary (what content would be selected now), final decision
   > engine runs before send"*

   **Established with it: a manager places a slot and picks a strategy; they do
   not build a rule elsewhere and plug it in.** The decision slot stays a
   separate row — it must, since `module_instances.decision_slot_id` is a
   foreign key — but it is *authored* as a property of the module a manager is
   looking at, not as an independent object with its own creation flow. This
   makes the standalone Decisions screen a management and reuse surface rather
   than the place slots come from.

   **"Position and strategy" is the whole of what a manager supplies**, which
   matches `DecisionSlotDB` exactly: `decision_strategy`, `candidate_filter`,
   `strategy_config`, `max_results`. Nothing about *which content* — that is the
   engine's job.

   **The summary is a preview of resolution, and it is explicitly not a
   commitment.** The user's own framing — *"what content would be selected
   now"*, with the real engine running before send — states the honesty
   requirement that question 4.3 asks about: a composer that showed a resolution
   without saying it is provisional would be showing a manager something that
   will not happen. Carried to Cluster 4 rather than settled here.

   **Known cost accepted:** a slot shared by several modules is created inside
   one of them, so the module a slot was born in is arbitrary. Editing it from
   the Decisions screen must therefore be a first-class path, not a fallback.

   **A correction, and a module type that does not exist.** My reading of
   *"headlines that are not connected to the catalog"* (question 1.2) as the
   existing `hero` module was wrong. The user:

   > *"with headlines i didn't mean hero. Headlines can be necessary to separate
   > different areas within an email. It's a module type that doesn't exist yet
   > in code."*

   A **section heading** — structural punctuation dividing an email into areas,
   in the same family as a divider rather than of `hero`, which is editorial
   content. Logged as a backend gap; it is a manifest and a template, which is
   exactly the two-file shape [[ADR-160 — Channel Model and Composition]]
   point 6 chose.

4. ✅ **What is a module with nothing in it?**
   **Resolution (2026-09-25): a normal mid-state in the composer, and a
   *reported* condition at send — never blocked.** The user: *"report, not
   block"*. The composer half was already settled by question 1.2 (layout
   precedes copy, so an unfilled module is the everyday condition of a draft);
   this closes the send half.

   **It places an unbound module on the "questionable" side of
   [[ADR-174 — Channel Readiness Is Asserted, Not Computed]] point 3's line** —
   *the system blocks what is broken and reports what is merely questionable*.
   The asymmetry that puts it there: an empty **required field on a bound
   module** means a malformed payload reaches a device, which is broken; an
   **unbound module** means a block is simply absent, so the email is shorter
   than planned but still well-formed. Blocking it would also make an ordinary
   drafting state fatal at the last moment.

   **This is a different case from [[ADR-086 — Decision Slots Fail Gracefully]]
   and the send review must not merge them.** ADR-086 covers a slot the system
   *tried* to fill and could not, and hides it. This is a module nobody tried to
   fill. Identical visual outcome, different fact, and only one of them is worth
   telling a manager about — a hidden slot is the system working as designed,
   an unbound module is probably an oversight.

   **Known cost accepted:** a manager can fire a send with a section missing by
   confirming past the report. Accepted as the same bargain ADR-174 point 2
   makes — *"the warning is information, not a control"* — and for the same
   reason: the alternative overrules a person about their own intent.

   **The model cannot distinguish the two ways a module ends up empty** —
   `module_data = null` on a `cms: false` module and both foreign keys null on a
   `cms: true` one — and does not need to, since both report identically.
5. ✅ **How does a manager reorder the stack?**
   **Resolution (2026-09-25): arrows and keyboard, optimised for speed.
   Drag-and-drop is rejected for the module stack.** The user:

   > *"ordering is something that frequently happens until the final send, but
   > drag'n'drop is absolutely painfull. No SaaS platform managed a good
   > drag'n'drop experience that allowed targeting the right spot. Especially if
   > you have to scroll down while dragging. Experience shows that buttons or
   > keyboard is much less annoying, as long as it's fast."*

   **My question conflated two things and the answer separates them.** I assumed
   frequent reordering is what *earns* drag-and-drop. It is not: frequency
   argues for good ergonomics, and drag-and-drop is not good ergonomics here.
   Reordering happens continually right up to the final send — so the "built in
   final order, rarely rearranged" hypothesis is wrong — and that makes speed
   the requirement rather than expressiveness.

   **The rejection has a stated mechanism, not a preference.** A module stack is
   tall, because every row is a content block, so dragging almost always means
   dragging *while scrolling* — which is where drag-and-drop reliably fails to
   hit the intended position. The failure is structural to the surface, which is
   why "no SaaS platform managed a good experience" rather than "we would do it
   better".

   **The one place drag-and-drop survives, and it is a new screen element.** The
   user:

   > *"The only drag'n'drop scenario I can imagine is to have arrows + keys at
   > the modules/preview but a sitemap somewhere that only shows a plain 'module
   > and order' and there you can just drag up/down, as it looks more like a nav
   > bar scrolling is probably not necessary."*

   A compact **outline** listing module type and position only — no content, no
   fields — is short enough to fit without scrolling, which removes the exact
   condition that breaks dragging. So drag-and-drop is not rejected in
   principle; it is rejected on a surface that scrolls and permitted on one that
   does not. **The outline is an addition to the screen cut** and is not in
   `docs/react-screen-inventory.md`.

   **Nothing about this constrains the API.** `UniqueConstraint(variant_id,
   position)` means moving a module from 5 to 2 shifts 2, 3 and 4 regardless, so
   the backend is a bulk renumber whatever the interaction is. This was purely a
   front-end question and the earlier framing — drag means "whole order", arrows
   mean "one change" — was wrong.

   **Known cost accepted:** moving a module from the bottom of a long stack to
   the top is many keystrokes. Mitigated by the outline rather than by
   drag-and-drop on the stack itself.
6. ✅ **May the same content record appear twice in one variant?**
   **Resolution (2026-09-25): manual duplicates are allowed with a note in the
   composer; a slot that would resolve to content already manually selected does
   not render; and the multi-slot collision is fixed in the decision layer
   rather than by cross-slot deduplication.** The user:

   > *"manual duplicates allowed, note in composer. decision resolution rule —
   > when rendering 'if contentid already in email manually selected, do not
   > render module' (human beats system); if it comes to multiple slots, I guess
   > it makes more sense to adjust the backend process that decision resolution
   > not only contains 1 contentid per user but rather a queue of 'next
   > content'. this way decision engine could pick more than one."*

   **"Human beats system" is a new precedence rule and it is not a restatement
   of [[ADR-176 — A Negative Decision Outranks a Positive One]].** ADR-176 ranks
   a *negative* decision over a *positive* one — an exclusion segment beats a
   manager's pin. This ranks a *human* positive over a *machine* positive when
   both point at the same content. Different axis, no conflict, and both can
   hold at once. It is worth stating explicitly because a future reader
   encountering "the manager's pick wins" right after "the manager's pin loses"
   would reasonably suspect one of them is wrong.

   **The collision resolves by hiding the module, which reuses
   [[ADR-086 — Decision Slots Fail Gracefully]]'s existing behaviour rather than
   inventing one.** A slot whose pick is already in the email is, for that
   recipient, a slot with nothing to show — the same outcome as a slot that
   resolved to nothing, reached by a different route.

   **The queue proposal is better than the ordered-exclusion approach I leaned
   towards, and avoids a rule nobody wants.** My lean would have made each slot
   aware of what earlier slots took, which gives **position** a meaning it does
   not have today — the top slot gets first choice, and reordering modules
   silently changes who receives what. The user's shape keeps slots independent
   and moves the work into resolution: one recipient gets a ranked queue, and
   consumers take from it. Reordering stays a presentation change.

   **The business reality check is the part that should govern the build**, and
   it argues against building much at all here. The user:

   > *"The situation that there's different spots in the same asset with
   > personalized content with manual selected content in between is low. It's
   > more likely that it's one spot and gets a rule like 'show up to 3 content
   > records'. Otherwise it's more likely that a manager would use different
   > decision strategies (filter on categories or types) so getting the same
   > content multiple times is low, too."*

   So the collision this question chased is **rare in practice**, and the common
   shape — one slot yielding several records — is a capability that is already
   modelled and does not work. That is where the effort belongs.

   **A scope boundary was drawn in passing and it is significant.** The user:

   > *"the third case 'full email personalized' is not built with this frontend
   > yet. That needs a different approach (including ai subject/preheader/header/
   > editorial etc)"*

   **This editor is for a human-composed email with personalised spots, not for
   a generated one.** A fully personalised email is a different product surface
   requiring AI-authored envelope and editorial copy, and it is explicitly out
   of scope for this client. Recorded so the composer is not stretched towards
   it by degrees — and it is consistent with
   [[ADR-142 — Autonomous Workflows and the Automation Boundary]] and
   [[ADR-082 — AI May Recommend but Not Publish]] rather than a new position.

   **Three backend gaps found while answering, all verified in code:**
   - **`max_results` is dead configuration.** `DecisionSlotDB.max_results`
     exists, defaults to 1, is carried by `DecisionSlotCreate`, exposed by the
     router and copied by `backend/app/campaigns/duplication.py:244` — and is
     **read by neither the decision engine nor the render path**. Every
     reference is CRUD. The *"show up to 3"* case the user calls most likely is
     therefore configurable today and has no effect.
   - **A resolution cannot hold a queue.**
     `DecisionResolutionDB.content_record_id` is a single non-null foreign key,
     one row per recipient per slot, and `resolve_content_for_module` takes
     `.first()`. Supporting several picks means either a rank column with
     several rows or a different shape, and it is the same change `max_results`
     needs — they are one piece of work, not two.
   - **Nothing checks manual selection against slot resolution.**
     `resolve_content_for_module` (`backend/app/rendering/service.py:450`) reads
     only its own module, so the "human beats system" rule has no place to live
     yet. It needs the set of manually bound content records for the variant,
     which the render loop has and does not pass down.
7. ✅ **Can two people edit one variant at once, and what should happen?**
   **Resolution (2026-09-25): optimistic concurrency is the floor, plus an
   *advisory* lock that anyone can clear themselves. Presence and history are
   wanted but explicitly not from the start.** The user:

   > *"it can happen and data loss is always bad. So we need at least B. Locking
   > would be nice in the form of that it's 'blocked by XX'. Each manager can
   > click on 'unblock' themselves, but they will check before. So it doesn't
   > have to be a real 'lock'. Technically maybe a 'last updated by X on XX at
   > XX:XX - unlock'."*

   **The lock is a social signal, not an enforcement mechanism, and that is the
   design.** Anyone may clear it without asking anyone; the expectation is that
   they check first. This is the cheapest thing that works among colleagues and
   it deliberately avoids the failure mode of real locks — a lock held by
   someone who went on holiday, needing an administrator to break.

   **The strongest argument for it is not about people at all.** The user:

   > *"it's realistic that there will be proper ai agents that 'work' parallel
   > in the system. So they need some sort of fence to not start working on
   > something that is edited in that same moment"*

   **Concurrency control here is infrastructure for machine principals, not a
   courtesy between two humans.** [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]
   already makes an agent a first-class caller and
   [[ADR-142 — Autonomous Workflows and the Automation Boundary]] anticipates
   orchestrators acting on their own schedule. An agent that begins rewriting a
   variant a person is mid-edit on produces exactly the silent loss this
   question is about, except faster and more often.

   **This produces an asymmetry the implementation must carry: the same lock is
   advisory for a person and binding for a machine.** A human clicking *unblock*
   is exercising judgement — *"I know Jana is at lunch, this is fine"*. An agent
   has no such judgement and must never clear a fence it did not set. So the
   mechanism is one field and two policies, and that distinction has to be in
   the rule rather than in a convention nobody enforces. **This is the part
   likeliest to owe an ADR**, since it is a new rule about what machine
   principals may do rather than a UI decision.

   **Wanted, and deferred by the user rather than by me:**

   > *"Small UI feature — showing users initials in a bubble on top, each that
   > ever worked in that campaign for example, a very slim history function. Not
   > necessary from the beginning."*

   **Known cost accepted:** two people who both click through the advisory lock
   still collide — at which point optimistic concurrency catches it and one of
   them gets a 409 rather than losing work silently. The two mechanisms are
   layered deliberately: the lock prevents the common case socially, the version
   check makes the uncommon case visible.

   **Backend gaps found while answering, all verified:**
   - **The version token already exists.** `variants` and `module_instances`
     both carry `updated_at` with `onupdate=func.now()`, so optimistic
     concurrency needs no schema change — only a comparison on write and a 409.
   - **Neither table records who changed it.** There is no `updated_by` on
     `variants` or `module_instances`; the only actor column anywhere nearby is
     `ContentVersionDB.created_by`. So *"last updated by X at HH:MM"* must be
     read from `audit_events` (`actor_type` + `actor_id`, `subject_type` +
     `subject_id`, indexed `created_at`) rather than from the row.
   - **That makes this feature the first real consumer of `audit_events`**,
     which `docs/backlog.md` flags as having three unproven properties
     *precisely because nothing reads it back*: `action` is an unvalidated
     VARCHAR, `detail` carries an unenforced policy, and brand filtering cannot
     be a plain `WHERE brand_id = ?`. Building this would settle all three, and
     it is a cheaper first consumer than the operator screen that item
     anticipates — one subject, one lookup, no filtering.
   - **`actor_id` is an id, not a name.** Rendering initials or *"blocked by
     Jana"* needs a join the audit layer deliberately does not do, since
     [[ADR-153 — Audit and Accountability]] keeps identifiers rather
     than contact details in the log.

8. ✅ **Which modules should be catalogue-bound?**
   **Resolution (2026-09-25): line (b) — editorial content only. `hero` becomes
   `cms: true`; `header` and `cta` stay static; decorative modules stay static.**
   The user: *"b, and an override is an everyday tool"*.

   **The deciding test is whether a field carries topical signal**, because that
   is the only thing categorisation feeds, and categorisation exists for exactly
   one purpose the user established earlier — the recipient's affinity profile.
   `hero` is a headline and body copy about a subject, so its invisibility to
   that profile today is a real defect and is the proposal's actual prize.
   `cta` is *"Book now"* and carries no topic; `header` is a subject line
   written for one campaign. Catalogue rows for either would add affinity
   records worth nothing while filling the catalogue with one-offs — degrading
   the thing the coverage argument is trying to protect.

   **A counter-argument was offered and rejected on its merits, which is worth
   recording because the rejection is the sharper reasoning.** I put it that
   line (a) becomes workable if the override layer carries per-campaign
   variation — bind `cta` to a canonical *"Read more"* and override the label
   each time, preserving coverage without one-off rows. The user took (b)
   anyway *and* confirmed overrides are an everyday tool, so the counter was not
   refused for lack of cheap overrides. **It addressed the wrong objection.**
   Cheap overrides solve the *friction* of routing every CTA through the
   catalogue; they do nothing about the fact that a catalogue row carrying no
   topical signal is worthless whatever it costs to create. My conditional
   conflated the two.

   **`header` staying static also keeps [[ADR-162 — Channel Rendering and Artifacts]]
   point 1 intact.** Subject and preheader live in a module *because they are
   fields of an email*; making them catalogue content would have asserted they
   are something else.

   **Known cost accepted:** `cta` and `header` copy remains invisible to the
   affinity profile permanently. Accepted because neither carries a topic, so
   nothing is lost that the profile could have used.

   **Backend consequence, logged:** flipping `hero` to `cms: true` is a manifest
   change *and* a data migration — whatever sits in existing `module_data` for
   hero instances is orphaned by the flag, because rendering reads
   `manifest.cms` to decide where variables come from.
   question 3 and not yet decided.* The manifests currently split six ways:

   | Module | `cms` | Variables |
   |---|---|---|
   | `email/header` | False | `subject`, `preheader` |
   | `email/hero` | False | `headline`, `text` |
   | `email/cta` | False | `label`, `url` |
   | `email/img_left` · `img_right` · `single_stack` | True | `image_url`, `image_alt`, `headline_medium`, `body_medium`, `button_label`, `button_url` |
   | `push/notification` | True | `push_title`, `push_body`, `push_image_url`, `push_link` |

   The user's proposal:

   > *"if it would be more consistent to make hero another module like the rest,
   > connected to cms, options to override img/headlines etc; or even to make ALL
   > modules cms=True. If a manager is forced to select content definitely
   > everything is categorized. That leaves only decorative 'modules' as 'non cms
   > modules' like divider."*

   **The argument is strong and it is not about consistency.** Forcing content
   through the catalogue is what guarantees **categorisation coverage**, and
   categorisation exists for exactly one purpose the user has already stated —
   building the recipient's affinity profile. Content typed straight into
   `module_data` is invisible to that profile forever. So every hand-typed
   module is a small permanent hole in the signal the decision layer runs on.

   **The counter-argument is about what a catalogue is for.** A subject line and
   a CTA label are usually campaign-specific rather than reusable assets, so
   requiring a catalogue record for each would fill the catalogue with one-off
   rows — which degrades exactly the thing the proposal is trying to protect,
   since a catalogue of single-use records is not a catalogue. It also collides
   with [[ADR-162 — Channel Rendering and Artifacts]] point 1: subject and
   preheader live in a module *because they are fields of an email*, and making
   them catalogue content says something different about what they are.

   **The question is therefore where the line sits, and there are three
   candidate lines**, not two: (a) everything except decorative modules, as
   proposed; (b) everything that carries *editorial* content — so `hero` becomes
   CMS, `header` and `cta` do not; (c) leave it as it is and accept the holes.
   *Lean: (b), because it takes the proposal's real prize — `hero` is editorial
   content and its invisibility to the affinity profile is a genuine defect —
   without forcing envelope copy into a catalogue it does not belong in. But
   this is the user's call and the coverage argument may simply outweigh it.*

### What Cluster 1 produced

**Three principles, and none of them is about the module stack.**

**1. Composition must not be gated on content readiness (question 1.2).** A tool
whose options disappear when the data is thin is at its least useful exactly when
the work is earliest. A manager who cannot pick the layout they want picks one
they can — so the constraint would change the output, not merely the order of
work. This is the cluster's most portable finding and it generalises past the
editor.

**2. Human beats system, and it is a different axis from
[[ADR-176 — A Negative Decision Outranks a Positive One]] (question 1.6).**
ADR-176 ranks a negative decision over a positive one. This ranks a *human*
positive over a *machine* positive when both point at the same content. Both
hold; neither implies the other.

**3. Concurrency control is infrastructure for machine principals (question
1.7).** The advisory lock is *advisory for a person and binding for a machine* —
one field, two policies — because a human clearing a fence is exercising
judgement an agent does not have.

**The catalogue boundary moved and the reason is reusable (question 1.8).**
Editorial content is catalogue-bound; envelope and call-to-action copy is not.
The deciding test — *does this field carry topical signal?* — is the right test
because categorisation feeds exactly one thing, the recipient's affinity profile.
A counter-argument was offered and rejected on its merits, which is recorded in
full because the rejection is sharper than the decision.

**Two screen-cut changes.** A compact **outline** view is added (module type and
position only, no scrolling — the one surface where drag-and-drop works). No
cross-channel compare view is built, ever, because an email A/B test and a push
A/B test are separate strategies rather than two readings of one idea.

**A scope boundary.** This editor composes a human-authored email with
personalised spots. A **fully personalised email is a different product surface**
requiring AI-authored envelope and editorial copy, and is out of scope for this
client.

**Eight backend gaps, all verified in code rather than assumed:**

| # | Gap | Where |
|---|---|---|
| 1 | No section-heading module exists | `storage/modules/email/` |
| 2 | `hero` → `cms: true` is a manifest change **and** a data migration | `storage/modules/email/hero.json` |
| 3 | Catalogue field set should derive from manifests | `content/service.py:101` |
| 4 | `max_results` is dead configuration — stored, exposed, duplicated, read by nothing | `campaigns/db_models.py:115` |
| 5 | A resolution cannot hold a queue — one FK, `.first()` at the read site | `campaigns/db_models.py:135` |
| 6 | Nothing checks manual bindings against slot resolutions | `rendering/service.py:450` |
| 7 | No optimistic concurrency, though `updated_at` already exists | `variants`, `module_instances` |
| 8 | No actor on either table; *"last updated by"* must come from `audit_events` | `campaigns/db_models.py` |

**Gaps 4 and 5 are one piece of work, not two** — supporting *"show up to 3"*
and supporting a ranked queue need the same schema change.

**Gap 8 makes the advisory lock the first real consumer of `audit_events`**,
which `docs/backlog.md` flags as having three unproven properties *because
nothing reads it back*. It is a cheaper first consumer than the operator screen
that item anticipates: one subject, one lookup, no filtering.

**ADR work this cluster owes**, to be sequenced after the interview closes rather
than written now: the machine-versus-human lock policy (question 1.7) is a new
rule about what machine principals may do and is the clearest candidate; the
catalogue-binding line (1.8) and the manifest-derived field set (2.8) probably
belong together in a content-catalogue record; *human beats system* (1.6) may be
an addendum to ADR-176 rather than its own record, since it sits on the axis
ADR-176 already names.

## Established during Cluster 1 — the client is keyboard-first

**Recorded 2026-09-25, arising from question 1.5 and applying to every screen,
not to the editor alone.** The user:

> *"Focus is → fast sorting option with arrows. high focus on keys and
> shortcuts (resend has a great shortcuts overlay)"*

**This is a product-level requirement and it appears nowhere else in the
repository.** [[Manager Workflow - design interview]] established that the
manager's job is shifting from producing to deciding and that the landing screen
answers *"does anything need me?"* — a person who works that way is moving
through a queue, and queue work is keyboard work. Shortcuts are therefore not a
power-user nicety bolted on later; they are how the primary user operates the
primary screen.

**It retroactively strengthens [[ADR-173 — The Manager Client's Runtime Dependencies]]
for a reason that record does not give.** React Aria was chosen for permissive
licensing and because it was the only candidate shipping an accessible table.
Keyboard-first operation is the thing React Aria is actually built for — focus
management, roving tabindex and keyboard interaction are its core rather than an
add-on — so the choice is better than its stated justification. Worth carrying
into the technical interview: the honest answer to *"why React Aria"* now has a
third leg that is about the product rather than about compliance.

**A shortcuts overlay is part of the deliverable**, on the user's reference
(Resend's). An overlay is also the cheapest possible discoverability mechanism —
without one, shortcuts exist for whoever reads the documentation, which is
nobody.

**Not yet decided:** which keys, whether shortcuts are global or per-screen, and
whether they are user-configurable. Those are design questions for the build,
not interview questions, and they are logged rather than answered here.

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
7. ✅ **Should a module variable declare a length limit, and is it advisory or
   enforced?**
   **Resolution (2026-09-25): the question was wrong. Lengths are not a
   constraint on one field — they are separate fields.** The user:

   > *"the 'there's only one text length' is not your base. There's only one text
   > length because we haven't implemented more. To show the options we will need
   > at least 2 options (long / medium texts + square / wide image)"*

   **`headline_medium` and `body_medium` are not a medium-length rule applied to
   `headline` — they are their own variables**, and `headline_long` is a
   different variable rather than the same one with a different limit. The
   `_medium` suffix already in every CMS manifest was a naming convention I read
   as incidental; it is the model.

   **This is a better answer than a character counter and it is worth saying
   why.** A limit is a property of a *rendering context* — this module's layout
   needs about this much text — and expressing it as a constraint on a shared
   field forces one piece of content to have one length, which is exactly what
   an editorial discipline of three lengths refuses. Separate fields let the
   same content record carry a long headline and a short one and let each module
   take the one that fits its layout. **No truncation, no ellipsis, no "the
   designer will deal with it".**

   **Consequence: a content record is authored at several lengths on purpose**,
   and the composer never shortens anything — it picks the variable the module
   declares. The counter I leaned towards would have been solving the wrong
   problem politely.

8. ✅ **Should the content catalogue's field set be the union of every module
   manifest's declared variables?** *Proposed by the user during question 3,
   with a worked example, and not yet decided.* Three modules declaring
   `{Text Medium, Headline Medium, Button Label Medium, Image Square, Url}`,
   `{Image Wide, Headline Long, Button Label Long, Url}` and
   `{Image Wide, Headline Long, Text Long, Url}` resolve by exact-name union
   into one catalogue field set of seven. The user:

   > *"before you start hardcoding those fields into the finale json blob. We
   > need a dynamic solution in style of 'drop file'. For example → the .json
   > files of each module define the existing content fields. So it pulls all
   > content fields from the different .json files and this become the content
   > fields in the catalog. […] If someone adds a new module at a later stage,
   > the json will be extended."*

   **The technical premise is correct and was verified, not assumed.**
   `ContentRecordDB.content` is `Column(JSON, nullable=False, default=dict)` —
   one column, no per-field columns, no validation. A module introducing new
   variable names therefore needs **no migration, ever**. Manifest discovery
   already walks every file at startup, so the union is computable where the
   registry already reads.

   **The codebase independently reached the same conclusion and recorded it as a
   stopgap.** `CONTENT_FIELD_GROUPS` (`backend/app/content/service.py:101`)
   hardcodes the per-channel field list and its own docstring says: *"Declared
   here rather than derived from the channel manifests, **which is where it
   belongs** and is not cheap today: the manifests describe modules and their
   templates, not a flat list of the content keys a channel reads. When that
   list exists, this table should read from it rather than repeat it."* The
   proposal is that list. A duplicate of the email half also lives in
   `backend/scripts/import_content_csv.py:33-41` and would collapse with it.

   **Four consequences that need answers before this is an ADR**, none of them
   objections:
   - **`required` stops being a property of a field.** `body_medium` is required
     by one module and absent from another, so the catalogue cannot show one
     truth. `required` is a property of *(module, field)* and only means
     anything once a module is chosen.
   - **`label` has the same problem**, and two modules may legitimately label one
     variable differently.
   - **The authoring form grows with the module library.** Seven fields from
     three modules; twenty-five from ten. A manager authoring one record would
     face every field in the system, most irrelevant — which is the same
     complaint the user made about content at scale, arriving from the other
     direction. The union needs a grouping discipline, not just a list.
   - **Exact-name union is also exact-name collision.** Two modules using one
     name for different intents merge silently and there is no namespacing.
     Today's render path already matches by exact name, so this property exists
     already; the union makes it load-bearing.

   **One tension to resolve explicitly rather than let pass.** On 2026-09-22 the
   user ruled that *"the json files in the modules is just to connect the fields
   to the final layout […] we shouldn't rely on reading the module json"* and
   preferred channel information be held in the backend. That ruling was about
   deriving **which channel a field belongs to**; this proposal derives **which
   fields exist**. They are different claims and can both hold — existence from
   the manifests, channel grouping from somewhere explicit — but the manifests
   are filed per channel, so the union makes the channel derivation available
   whether or not it is used. Worth stating which it is.

   **This is a content-catalogue decision surfaced by the editor interview, not
   an editor decision.** It likely owes its own ADR and it changes what
   Cluster 2's form questions are asking about.

   **Resolution (2026-09-26): adopted. No field is required at the catalogue
   level; the composer warns at bind time instead.** The user's answers also
   dissolved the consequence I was most worried about.

   **The field count is bounded, and my "thirty, maybe fifty" was wrong.** The
   user:

   > *"if we consider 3 module types (much, medium and small amount of content
   > details) there's kind of a cap in fields: image url, alt text, headline,
   > copy, button text (by 3) / url, tracking, hero headline, hero button text,
   > legal conditions (by 1) — so roughly 20 fields for all email fields.
   > push / social / whatsapp / sms may be another 4 per channel (url, tracking,
   > headline, text). in the end it depends on business model but it's unlikely
   > that it will become 50 - 60 - 70 fields."*

   **Modules cluster into a few content densities rather than proliferating**,
   so the union converges instead of growing with the library. The catalogue
   form is long but finite — roughly twenty email fields plus four per
   additional channel. Consequence 3 of this question ("the form grows with the
   module library") is therefore a grouping problem, not a scale problem.

   **Beta scope: two sizes, not three.** *"For our beta example we stick to two
   length (modules that cover full width, modules that split in 50:50)."* The
   size vocabulary is set by layout width, which is why it is two rather than
   three — full-width and half-width are the layouts that exist.

   **Nothing is required at the catalogue level**, confirming the lean, and
   `required` and `label` are therefore properties of *(module, field)* rather
   than of the field. The catalogue cannot show one truth for a field one module
   demands and another never mentions, so it shows neither and the composer
   shows both. This is the same shape as question 1.4 (report, do not block) and
   [[ADR-174 — Channel Readiness Is Asserted, Not Computed]] point 2 (warn, do
   not compute), and it puts the check where the information exists — only the
   composer knows which module was chosen.

9. ✅ **Is a content record safe for a machine to pick?**
   *Raised by the user during question 2.8 and answered in the same message.*
   **Resolution (2026-09-26): a manager-set "machine ready" toggle on the
   content record.** The user:

   > *"To help with all machine selection → toggl for 'machine ready' that way a
   > manager can decide if it's save to use this content record (we need this
   > anyway, maybe there's content that's only allowed for a specific target
   > group or time or any other reason that must be excluded from machine
   > pick)"*

   **This is a third assertion axis and it must not be merged with the other
   two.** ADR-174 point 1 was explicit that `status` and channel readiness are
   different axes and that collapsing them produces an enum that grows by one
   value per channel. The same reasoning applies again:

   | Axis | Answers | Set by |
   |---|---|---|
   | `status` (`active`/`inactive`) | may this record be newly selected at all | a person |
   | channel readiness | may it go out on this channel | a person (ADR-174) |
   | **machine ready** | **may a machine pick it without a person deciding** | **a person** |

   A record can be active, push-ready and *not* machine-selectable — a piece
   that is legally sensitive, time-bound, or meant for one audience only, which
   a person must place deliberately.

   **It is a record-level fail-closed flag and that distinguishes it from
   `candidate_filter`.** `DecisionSlotDB.candidate_filter` is *the slot saying
   what it wants*; this is *the record saying whether it may be taken at all*,
   and it applies to every slot at once. A slot's filter cannot express "never,
   by anyone, automatically" without every slot author remembering to write it —
   which is the fail-open shape the repo refuses elsewhere.

   **It follows the same asserted-not-computed principle as ADR-174** and for
   the same reason: the exclusions the user lists (a target-group restriction, a
   time window, "any other reason") are intent, and no computation over the
   `content` blob can see intent.

   **It is consistent with [[ADR-082 — AI May Recommend but Not Publish]] and
   with [[ADR-176 — A Negative Decision Outranks a Positive One]]** — a negative
   assertion on the record outranks any slot's positive selection — but it is
   narrower than either: it governs the *decision engine*, not AI authorship.

   **Likely owes an ADR, probably the same one as question 1.8 and 2.8**, since
   all three are catalogue-level decisions surfaced by this interview.

## Cluster 3 — Edit versus override

*Where the keystroke goes. The cluster this interview exists for.*

> **Established 2026-09-25, before the cluster opened, while answering question
> 1.8: an override is an everyday tool, not an exception.** The user:
>
> > *"an override is an everyday tool (unfortunately — the longer a company uses
> > the platform the better they like working with ai and automation so override
> > will be less and less needed)"*
>
> **Three things follow and they pull in different directions.**
>
> **(1) The override path must be fast.** It is the common case, so a
> confirmation step, a mode switch or a dialog on every override would tax the
> most frequent action in the composer. This is in real tension with
> [[ADR-040 — Introduce Override Layer]]'s framing of an override as a
> deliberate, logged deviation — deliberate and frequent are not contradictory,
> but a UI tuned for one is usually wrong for the other, and questions 3.2 and
> 3.3 have to resolve it rather than split the difference.
>
> **(2) "Unfortunately" is a design target, not an aside.** The user wants
> overrides to become *less* necessary over time as automation earns trust.
> A composer that makes overriding pleasant and leaves the underlying content
> wrong is working against that, which is an argument for question 3.1's answer
> mattering: an override that should have been a catalogue fix is debt.
>
> **(3) Override frequency is a maturity signal, and this is the first thing in
> the repository that gives `outcome_delta` a reason to exist beyond curiosity.**
> If a company's override rate falls as it uses the platform, the automation is
> earning trust; if it rises, something is drifting. That makes override volume
> a measure of the *product* rather than of a campaign — a claim the playbook
> can make and few competitors can. Worth carrying to the business side and to
> question 3.9.

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
