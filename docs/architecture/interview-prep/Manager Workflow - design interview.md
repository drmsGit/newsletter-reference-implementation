---
type: interview-prep
topic:
  - architecture
  - frontend
  - design
created: 2026-09-21
modified: 2026-09-22
status: closed
---

> **Status: interview OPEN.** Clustering approved 2026-09-21. All five clusters
> written out — 49 questions, 18 answered.
> **Cluster 2 CLOSED 2026-09-21, 18/18** — see *What Cluster 2 produced* for the
> five backend requirements and the ADR work it owes.
> **Cluster 1 ✅ CLOSED 2026-09-24, 8/8.**
> **Cluster 3 ✅ CLOSED 2026-09-23, 10/10.**
> **Cluster 4 ✅ CLOSED 2026-09-24, 7/7.**
> **Cluster 5 ✅ CLOSED 2026-09-24, 8/8.**
> **INTERVIEW COMPLETE — 53 of 53.** ADRs written 2026-09-24:
> [[ADR-174 — Channel Readiness Is Asserted, Not Computed]],
> [[ADR-175 — Facets Are the Manager's Own Taxonomy, Not the Engine's]],
> [[ADR-176 — A Negative Decision Outranks a Positive One]], plus dated addenda to
> ADR-142, ADR-150, ADR-161 and ADR-168. Next: the variant editor's own design
> interview (question 3.3b).

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
| ✅ **Approvals as the landing screen** | **Confirmed by question 1.1 (2026-09-22)** — and on a stronger argument than the one it was built with: the manager's job is shifting from producing to deciding. Was a guess; is now a decision. |
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

## Cluster 1 — The daily loop and the home screen  ✅ CLOSED 2026-09-24, 8/8

*What a manager opens this for, what is waiting, and what "done for today" means.*
Screens: **approvals**, **approval detail**, the shell itself.

1. ✅ **What does a manager open this client for on an ordinary day, and what is
   the first question they need answered?**
   **Resolution (2026-09-22): "does anything need me?" — the approval inbox is the
   landing screen.** The user:

   > *"'Today' most platforms try to show a bit of everything but no manager uses
   > them, they go directly to the area they have to work in. This is a 'future
   > platform' — there will be more ai and more decisions to make so → 'Does
   > anything need me?' The approval inbox is the perfect place to be on the first
   > page. Even if it is not the way a manager works today, it will become the way
   > they work in the future."*

   **Established with it, and it is the sharpest statement of this product's
   thesis anywhere in the repository: the manager's job is shifting from producing
   to deciding, and the client is designed for where that ends up rather than
   where it is now.** Everything Cluster 2 decided converges on it — content
   authoring is outsourceable to an agency or an AI agent (question 2.4), an
   integration's readiness assertion routes through this inbox (question 2.6b),
   [[ADR-082 — AI May Recommend but Not Publish]] keeps publication human, and
   [[ADR-142 — Autonomous Workflows and the Automation Boundary]] draws the
   automation boundary at exactly this line. If production is increasingly
   delegated, **what is left for a person is judgement, and the inbox is where
   judgement happens.**
   **A dashboard is rejected, explicitly and on evidence.** "A bit of everything"
   is what most platforms show and what no manager uses. The landing screen
   answers **one** question rather than several, so the overview option is closed
   and no such screen enters the cut.
   **This confirms rather than merely permits what is built** — approvals as the
   landing screen stops being an implementer's guess and becomes a decision, and
   the ⚠️ against it above is cleared.
   **Known cost accepted, and it is deliberate:** this is not how most managers
   work today, so an adopter evaluating the product against their current habits
   may find the landing screen strange. Accepted as a bet on where the work is
   going rather than a misreading of where it is.
   **Worth carrying to the business side:** this is a positioning statement as
   much as a design one, and `docs/business/POSITIONING.md` is the open gate.
2. ✅ **Is there a state that means "done for today", and should the client show
   it?**
   **Resolution (2026-09-22): no completion signal at all.** The work is
   continuous and the client never implies an end point. An empty inbox is an
   empty list, not an achievement.
   **Established with it:** this is Cluster 2's principle again — *the system
   reports, the manager decides* — extended to judgement about the work itself.
   The client has no way to know whether campaigns are on track; it only knows
   whether anything is blocked on this person, and it must not let the second
   masquerade as the first. **The cross-screen all-clear is rejected with it**, as
   an overview by another name after question 1 closed that door.
   **A line worth drawing carefully rather than assuming.** A factual
   *"nothing is waiting for a decision"* describes the list; *"You're all caught
   up ✓"* is a completion signal. The current empty state reads
   **"Nothing is waiting for a decision."** — believed to be on the right side of
   that line, but it is the implementer's copy and this resolution is the reason
   to check it rather than defend it.
   **Known cost accepted:** a manager gets no positive confirmation that they have
   nothing to do, which some people find unsatisfying. Accepted because the
   alternative is a reassurance the client cannot honestly give.
3. ✅ **The inbox now carries send approvals and content-readiness reviews. How
   should it handle two kinds of item at very different volumes?**
   **Resolution (2026-09-22): one flat list, newest first, with filters by action
   type and by requester.** Structural grouping was rejected in favour of
   filtering.
   **Established with it:** this is *the system reports, the manager decides*
   applied to prioritisation — **the system does not decide which requests matter
   enough to separate.** It presents them in arrival order and gives the manager
   the means to narrow. Consistent with Cluster 2's answer to the same shape of
   problem, where filtering beat imposed structure.
   [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] point 3's
   durable actor distinction earns its keep here: **"requester" is a filter
   dimension**, so "show me what Acme Agency sent" is a real question the data can
   answer.
   **Backend consequence, and it compounds question 2.10's.** `GET /approvals/`
   accepts **only** `status` (`pending`/`decided`/`all`) — no action-type filter,
   no requester filter, no pagination. Two query parameters and paging are owed
   here, which is the same requirement as 2.10 arriving on another route rather
   than a separate one.
   **Known cost accepted, and it is real:** a single send approval can sit below
   forty content items, and firing a send is the highest-consequence decision in
   the product. Filters mitigate it; they do not prevent a manager who does not
   filter from missing one. Accepted deliberately over grouping.
4. ✅ **What must a person see before deciding a held request?**
   **Resolution (2026-09-22): generic rows, plus a link to the subject — and the
   link target depends on the action type.** A content-readiness request links to
   the content record, a campaign-related one to the campaign, an audience one to
   the group. The user: *"For the start: Generic row + link (to campaign / to
   content / to audience group), improvements will become features."*
   **Established with it:** the client **stays ignorant of action types**, which
   was the point of the generic renderer. Mapping `subject_type` → a route is one
   small table, not per-action presentation, so a new action type still needs no
   client change — it needs a route for its subject, which the client already has.
   **Explicitly deferred, and named rather than discovered later:** combinatorial
   requests — the user's example, *"the three groups get these three campaigns"* —
   will need a purpose-built screen. That is a later feature, not a reason to
   abandon the generic approach now.
   **Gap, and it is the same shape as one already found.** `PendingActionDB`
   **stores** `subject_type` and `subject_id` (`app/approvals/db_models.py:79-80`)
   and `PendingActionDetail` **exposes neither** — so the client cannot build the
   link this resolution requires. The data exists; the response model drops it,
   exactly as `ModuleVariableOut` drops `label` and `envelope`. Two fields on a
   response model, and the second instance of this defect the interview has found.
   **Known cost accepted:** a reviewer judging copy leaves the inbox to read it.
   Accepted as the honest version — a summary that tries to be the record is worse
   than a link to the record.
5. ✅ **Do approvals need a comment or a conversation?**
   **Resolution (2026-09-24, reopened 2026-09-23 and now closed): comments exist
   and are always optional. Never required.** The user: *"it doesn't make sense to
   require it so a manager quickly will start to type in 'reason' or '---' just to
   be able to approve it."*
   **Established with it, and it generalises past approvals: a required free-text
   field does not produce reasons, it produces `---`.** Junk data is worse than no
   data because it looks like data — a rejection reason nobody can act on is
   indistinguishable, in the database and in a report, from one somebody wrote
   carefully. The requirement would have bought compliance with the form and
   nothing else.
   **Settled firmly and not to be revisited: this is not a ticket system.** No
   thread, no replies. Humans and agencies already have structured channels for
   that, and duplicating one inside a marketing platform is scope the product
   should refuse.
   **What stands:** a rejection reason is worth having, because *"an agency needs
   to know what they need to change, an ai needs to know how to improve"* — and
   `PendingActionDB.decision_reason` already exists, nullable, 1000 characters. So
   the decider's side needs no new model at all. Whether a **requester** note is
   added is the same shape of question and takes the same answer: optional if it
   exists.
   **The proposal already explains itself, which is why the comment is only half
   the loop.** Question 1.5's own check established that the machine's reasoning
   and the human's are correctly separate: `DecisionResolutionDB.reason` and
   `score` say why a strategy chose something
   ([[ADR-085 — Decision Resolution Should Be Optionally Explainable]]), and
   `decision_reason` says why a person decided. The comment is the human's answer
   back, not a restatement of the proposal.
   **Left to the build rather than the design:** the resubmission sketch — *"if an
   agency proposes the same content again, the reason can be overwritten (maybe
   not cleared before, so the manager can see what was wrong the first time)"*.
   That is field lifecycle on an optional column, not an open design question.
   **Unchanged and still owed elsewhere:** audience membership records no reason at
   all, and the case that needs one is external automation. That is Cluster 4
   question 3's gap, not this one's.

6. ✅ **After a decision, does the approver need to see what happened as a
   result?**
   **Resolution (2026-09-23): the decision history moves to its own screen — log
   and queue stay separate.** The inbox holds what is waiting; a decided item
   leaves it and appears in a history screen instead.
   **Established with it:** this protects question 1's property directly. The
   landing screen answers **one** question — *does anything need me* — and a
   decided item answers a different one. It also avoids worsening question 3's
   accepted risk: a send approval can already sit below forty content items, and
   adding decided rows to that same list would make burial more likely, not less.
   **Cheap on the backend, new on the client.** `GET /approvals/?status=decided`
   already exists and is documented, so the history screen needs no new route —
   but it **is a screen that appears in no inventory**, so the first cut grows
   from sixteen to seventeen. Worth saying out loud rather than letting it arrive
   unannounced.
   **Open, and deferred with question 5:** what the history says *about outcome* —
   whether an approved send that later failed is the approver's business — belongs
   to the question 5 revisit rather than being settled here.
7. ✅ **A held request expires without anyone deciding it. Who needs to know?**
   **Resolution (2026-09-23): the question is wrong for content review — expiry
   should not exist for it.** A deadline is right for firing a send, where the
   moment genuinely passes. It is wrong for *"is this copy good"*, which does not
   go stale. **The TTL belongs to the action type, not to approvals as a whole.**
   **Half of that is already true, and the design anticipated variation.**
   `default_ttl_seconds` is declared per action — 24 hours on
   `send.fire_send_instance`, 8 hours on `ai.apply_subject_preheader`. What it did
   **not** anticipate is *absence*, and the assumption is baked in three places:

   - `PendingActionDB.expires_at` is `nullable=False` (`approvals/db_models.py:94`)
     — every held action must carry a deadline;
   - `default_ttl_seconds: int` on the action definition
     (`approvals/actions/base.py:58`) — not `int | None`;
   - `expire_due_pending_actions` and `approve()`'s expired check both compare
     against it, as does the inbox's "pending excludes a request whose deadline has
     passed".

   **So this is a schema change, not a configuration one**, and in a repository
   with no Alembic that means a hand-written migration beside `create_all`. Making
   `expires_at` nullable also means every comparison against it must treat null as
   *never expires* rather than *expired*, which is the direction that fails safe
   but must be written deliberately.
   **It touches [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §4**,
   whose held-action design assumes a deadline. Whether that needs an addendum
   depends on how explicitly §4 requires one — to be checked when the ADR work is
   done rather than asserted here.
   **Established with it:** the content-readiness action from question 2.6b is the
   first action type that should carry **no** TTL, so this lands as part of
   building it rather than as separate work.
   **The notification question is answered by not arising.** With no deadline on
   content review there is nothing to expire unnoticed. For actions that *do*
   expire, nobody is notified — the deadline is visible in the inbox before and in
   the history after, consistent with question 2's no-completion-signal and the
   cluster principle.

8. ✅ **What order do the screens appear in the navigation, and does the landing
   screen belong in it?**
   **Resolution (2026-09-23): grouped — decide · make · send.** The user: *"this
   is a platform with a high functionality and doesn't try to be a one pager. It's
   only important that the nav is logically and user friendly."*
   **Established with it:** structure is accepted **ahead of** the volume that
   would force it, deliberately, because the screen count only grows from here —
   History arrived in question 6, Deliveries is unbuilt, Settings is owed by
   question 2.9's facet administration, and administration screens come last but
   do come. A flat list that works at four items and fails at ten is a rework
   scheduled for later.
   **The grouping is the decision; the exact placement is not.** Approvals and
   History are clearly *decide*; Content and Campaigns are clearly *make*.
   **Audiences is the genuinely arguable one** — choosing who receives something
   is arguably part of making it — and Recipients, Categories and Settings have no
   obvious home yet. Those follow as each screen is built, against the stated
   test: logical and user-friendly.
   **Deferred as a future feature, named so it is not reinvented:** *"the option
   that a manager creates their own nav bar like adding favorites next to
   decide/make/send might be a good feature, but we don't need it from the
   beginning."*
   **The landing screen stays in the nav**, inside *decide*, since grouping
   removes the oddity that made pulling it out attractive.

---

### What Cluster 1 produced

**The product's thesis, stated for the first time.** Question 1: *"This is a
future platform — there will be more ai and more decisions to make."* **The
manager's job is shifting from producing to deciding**, and the client is
designed for where that ends up rather than where it is now. Everything Cluster 2
decided converges on it. This is a positioning statement as much as a design one,
and `docs/business/POSITIONING.md` is the open gate it bears on.

**Three backend gaps, on top of Cluster 2's five.**

6. **`PendingActionDetail` does not expose `subject_type` / `subject_id`** (Q4),
   although `PendingActionDB` stores both — so the client cannot build the link to
   the thing being decided. Second instance of a defect already seen once, where a
   response model drops fields the table has.
7. **`GET /approvals/` accepts only `status`** (Q3) — no action-type filter, no
   requester filter, no pagination. The same requirement as Cluster 2's question
   10 arriving on another route.
8. **A held action cannot exist without a deadline** (Q7). `expires_at` is
   `nullable=False` and `default_ttl_seconds: int` is not optional, so "content
   review does not expire" is a schema change plus a hand-written migration, and
   every comparison must then read null as *never expires* rather than *expired*.
   Touches [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §4.

**One gap that belongs to Cluster 4 but was found here.** Audience membership
records **no reason**, and the case that needs one is external automation, not the
in-app suggestion function — an orchestrator selecting recipients daily for a
reactivation send must say *why this recipient*, and with AI in the loop the
platform cannot reconstruct it. `POST /api/audience-groups/{id}/members/{id}`
takes **no request body at all**.

**The screen count grew.** Seventeen, not sixteen: question 6 separated the
decision **history** from the inbox, so log and queue stay apart.

**What is settled about the shape of the client.** The landing screen answers
**one** question and a dashboard is rejected on evidence. There is **no completion
signal** — the client never tells anyone they are finished. The inbox is a flat
list with filters rather than imposed grouping. The nav is **grouped: decide ·
make · send**, accepted ahead of the volume that would force it, with per-screen
placement to follow and manager-defined favourites deferred as a future feature.

**Still open in this cluster:** question 5 is **◐ partial** at the user's request —
not a ticket system and no thread are firm, a rejection reason is provisional, and
the requester note plus the resubmission-overwrite behaviour are to be asked again.


## Cluster 2 — Authoring content across channels  ✅ CLOSED 2026-09-21

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
   **Rider, resolved (2026-09-21): fields appear in the manifest's declared
   order.** Today it is JSON insertion order — an accident of how each record was
   written, so two records can show the same fields in different places. The
   manifest already lists its variables in an order somebody chose; using it makes
   every record consistent and makes reordering a form an edit to a manifest
   rather than to code. Consistent with the ruling that manifests are the source
   for grouping. Required fields are **not** sorted to the top: that would
   override a deliberate sequence with a mechanical one.
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

> **Vocabulary note.** These questions were asked using the word *dimension*, and
> question 13 later settled the term as **facet**. The questions are left as they
> were asked rather than rewritten, so the record shows how the name was arrived
> at — but **"facet" is the agreed word** for the API, the UI and the playbook.
> Read *dimension* below as *facet*, except where it says *system dimensions*
> versus *manager dimensions*, which is a distinction about who declares a facet
> rather than two different things.

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
9b. ✅ **Are dimensions global, or per brand?**
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
11. ✅ **What replaces the dropdown of every content record id when a manager is
    picking content mid-composition?**
    **Resolution (2026-09-21): a picker pre-narrowed by what the slot can use —
    and the narrowing is a default, not a restriction.** It opens showing content
    ready for this variant's channel and matching what the module or slot
    requires; dimensions and search narrow further. **There must be a visible,
    reversible way to show content that is not currently choosable.** The user:

    > *"Maybe a manager prepared content that is not fully ready yet but they
    > already want to start building the campaign; it mustn't become a 'where's my
    > content record, I can't find it'."*

    **Established with it: this is the cluster's principle applied to a filter —
    the system reports, the manager decides.** A pre-narrowed picker that silently
    hides records is the system deciding what exists. The channel filter is
    therefore a **removable chip that happens to start on**, and an unready record
    appears marked as unready rather than absent.
    **It is safe because of question 3b.** Picking unready content cannot quietly
    ship an empty push, because a required-field check before firing is already
    owed from that answer. The escape hatch and the send-time check are one
    design: the earlier surface stays permissive precisely because the later one
    refuses.
    **Fallback recorded, if the pre-narrowing proves too complex to get right:**
    search-first with filters secondary.
    **Answered together with question 3.5**, which is the same requirement seen
    from the campaign side.
12. ✅ **Does the dimensions concept apply to anything other than content?**
    **Resolution (2026-09-21): content and campaigns. Audiences get search and
    paging only.** The axes mean the same thing for content and campaigns — a B2B
    campaign uses B2B content — so filing both by them is coherent. An audience
    group is *defined by its rules* rather than filed by topic, so tagging it
    would be describing a thing that already describes itself.
    **Established with it:** dimensions are **not a column on the content table**.
    They attach to at least two entity types, so the model is a declared dimension,
    its values, and links from taggable things to values. Whether that is one
    polymorphic link table or one per entity is an implementation choice; this
    repo's idiom favours the explicit version.
    **Second-order effect on question 11, and a useful one.** If a campaign
    carries dimensions too, the content picker can pre-narrow by *the campaign's
    own axes* — building a B2B Lisbon campaign shows B2B Lisbon content first —
    which makes "pre-narrowed by what the slot can use" much stronger than a
    channel filter alone. Worth designing for; not required by this resolution.
    **Known cost accepted:** two entity types means the tagging surface is built
    twice unless it is shared from the start.
13. ✅ **What is this concept called, in the API, the UI and the playbook?**
    **Resolution (2026-09-21): facets, with facet values.** The user: *"it's best
    to explain a new vocabulary than risking (system) confusion because of
    comfortability."*
    **Established with it, and it outlives this decision: precision beats
    familiarity when the familiar word is already taken.** "Tag" was the original
    suggestion and was rejected by its own connotation — it implies loose and
    free-form, which is exactly what question 8 decided against. "Label" collides
    with `ModuleVariable.label`, a form caption. "Attribute" collides with
    `RecipientDB.attributes`, free-form recipient data. "Category" is ADR-080's
    governed affinity taxonomy. **Facet** is the precise term for a declared axis
    you filter along, composes correctly with AND, and collides with nothing.
    **Known cost accepted:** it is jargon, and a manager or a playbook reader
    needs it explained once. Accepted deliberately — a word that needs explaining
    once is cheaper than a word that quietly means two things.
    **Consequence:** the repository has **no glossary** — the `docs/implementation/`
    tier defines no domain vocabulary at all. "Facet" is the first term that
    demonstrably needs one, alongside campaign, variant, module instance, decision
    slot, snapshot and signal contribution.
14. ✅ **Is "in feedback loop / waiting for feedback" a facet, or a lifecycle
    state?**
    **Resolution (2026-09-21): neither — readiness already covers it.** The states
    map onto what this cluster has already decided:
    *not ready* = still being worked on · *ready* = the author is done ·
    *pending action* = an integration asserted readiness and a person has not
    decided yet (question 6b).
    **Established with it:** no third state axis. `status` stays the record's own
    lifecycle, per-channel readiness stays question 3's assertion, and nothing new
    is built. **The original example conflated two things and the interview
    separated them**: the *states* dissolve into readiness, while the *product
    types, B2B/B2C and destinations* become facets. Asking whether the need was
    already met before modelling a third thing is what avoided a workflow engine
    nobody asked for.
    **Known cost accepted:** an adopter whose editorial process has more than
    "being worked on / done" gets no support for it. If that turns out to be
    common, a single-select `Workflow` facet is the cheap next step — it needs no
    lifecycle engine and each team names its own stages.

---

### What Cluster 2 produced

**Five backend requirements, none of which existed before the interview ran.**

1. **A required-field check before a send fires** (Q3b). Nothing checks today —
   `resolve_module_variables` defaults a missing field to `""` and
   `ModuleVariable.required` is never enforced at render, so an empty push
   notification ships to a real device. Belongs in Cluster 5's pre-flight.
2. **A read-only candidate count for a decision slot** (Q4b). `POST
   /decision/slots/{id}/execute` resolves for real and writes a
   `DecisionResolution`, so there is no way to ask what a slot would choose
   between without causing a decision.
3. **A content-readiness approvable action**, plus its `APPROVABLE_ROUTES` entry
   (Q6b). That table is fail-closed by omission, so without the entry a machine
   asserting readiness gets a hard 403 rather than a hold.
4. **The facet model** (Q8, 9, 9b, 12): declared facets, their values, and links
   from content *and campaigns* to values — per brand, governed by an
   administrator. Its administration surface belongs in Settings, which is
   **gap C2** and has no router at all, so this work inherits that dependency.
5. **Server-side filtering and pagination on every list route** (Q10). Reprices
   **P3-02** from a latent scaling note to a blocker, and applies to content,
   campaigns, audiences, recipients and approvals.

**ADR work owed.**
- [[ADR-161 — Channel Execution Shapes]] point 7's rider — *"catalogue readiness
  is 'push fields not empty'"* — is **now false**; readiness is asserted, not
  computed. A dated addendum, not a supersession.
- [[ADR-150 — Tenancy and Access Model]]'s 2026-09-15 addendum needs a sentence
  on why findability differs from affinity, so facets are per-brand while
  categories stay global.
- **Facets are a new first-class concept and need a record of their own**, or
  several — the model, the per-brand decision, and the governance. Not yet
  numbered or scoped.

**Maintenance that falls out**, needing no ADR: `CONTENT_FIELD_GROUPS` reads from
the manifests rather than repeating them, and the duplicate email field list in
`backend/scripts/import_content_csv.py:33-41` goes with it.

**Client work this invalidates.** The flat content-field list is wrong and marked
❌ above. The four Phase 2 list screens fetch everything and render it, which
will not survive requirement 5 — the cost of having built them before this
interview ran.

**Two principles established**, both of which should be checked against every
remaining screen decision: **the system reports, the manager decides** (no
auto-collapse, no inferred readiness, no un-asserting, no nagging — and where a
signal is load-bearing it becomes a check at the point of action); and
**precision beats familiarity in naming** (facet over tag, because a word that
needs explaining once is cheaper than one that quietly means two things).


## Cluster 3 — Composing a campaign  ✅ CLOSED 2026-09-23, 10/10

*What gets assembled, in what order, and what campaign detail is actually for.*
Screens: **campaigns list**, **campaign detail** (inventory B11), **decisions**,
**decision slot detail**.

1. ✅ **What is a manager looking for in the campaign list?**
   **Resolution (2026-09-23): finding, not monitoring — and monitoring gets a
   screen of its own.** The list is a way to reach a campaign: name, facets, last
   touched. State belongs in the workspace where the work happens. The user:
   *"Monitoring will need a separate screen → multiple campaigns with multiple
   assets create a long list easily. If enough place it can be a left/right
   placing or an easy to reach new place."*
   **Row click navigates to the workspace**, settled by question 2. The ⚠️ against
   "campaign rows do not navigate" is cleared as wrong.
   **Established with it, and it is the second structural principle this interview
   has produced: a screen answers one question.** Cluster 1 question 1 rejected a
   dashboard because the landing screen answers *does anything need me*; question
   6 moved decision history out of the inbox because a decided item answers a
   different question; this moves monitoring out of the campaign list for the same
   reason. **Three separate answers, one rule** — and it should be checked against
   every remaining screen rather than rediscovered.
   **The layout note is recorded rather than decided:** *left/right placing* if
   there is room, otherwise somewhere easy to reach. That is a presentation
   question for when the screen is designed.
1b. ✅ **What is the monitoring screen, and is it the deliveries screen?**
   **Resolution (2026-09-24), answered as Cluster 5 question 4: no.** Monitoring
   is campaign-level and deliveries is send-level, so they are two screens and the
   first cut grows to nineteen. Full reasoning there.

   *Original framing:*
   *Raised by question 1, and it decides whether the cut grows again.* The user's
   framing — *"multiple campaigns with multiple assets"* — spans campaigns,
   their variants and their sends, which is broader than Cluster 5's **deliveries**
   screen but overlaps it substantially. If monitoring **is** deliveries seen from
   the campaign side, no new screen is needed. If it is a campaign-level view of
   what is in flight, the first cut goes from seventeen to eighteen.
   *Answer this together with Cluster 5 question 4, which asks what question the
   deliveries list answers.*

2. ✅ **What is the unit of work — the campaign, or the variant?**
   **Resolution (2026-09-23): the campaign is the workspace; variants live inside
   it.** A manager works on "the October newsletter", and its email variant, push
   variant and A/B versions are all inside that one screen.
   **Established with it: campaign detail — inventory B11 — is the product's main
   screen**, not an index onto other screens. That is why it carries the largest
   block of derived state in the application, and the weight is inherent rather
   than accidental: overrideability, module limits from the channel manifest,
   audience counts per channel and providers filtered by channel all belong to one
   place because the manager is in one place.
   **It settles half of question 1 in advance:** a campaign row must navigate, and
   it navigates to the workspace. The ⚠️ against "campaign rows do not navigate" in
   *Where the frontend already stands* is not merely unconfirmed — it is **wrong**,
   and only defensible while B11 does not exist.
   **Known cost accepted:** one screen holds a great deal, which makes question 3
   — what is visible at once versus a click away — the hardest question in this
   cluster rather than a layout detail.

3. ✅ **Campaign detail is the workspace. What must be visible at once, and what
   can be a click away?**
   **Resolution (2026-09-23): variants are edited on their own screens, and the
   real finding is that the editor has never been designed.** The user:

   > *"In the backend process the real editor was never discussed. The manager will
   > not work with a drop down selection content + layout. we will need to build a
   > real editor with selection creating the preview, sorting buttons, override
   > directly not with json structure etc. there's no need to push everything into
   > one screen."*

   **This refines question 2 rather than reversing it.** The campaign stays the
   unit of work — it is what a manager is working *on* and where they orient — but
   the variant editor is the tool they enter from it, the way a document is the
   work and an editor is the tool. **The consequence is that B11 is lighter than
   the inventory implies and the heavy screen is somewhere else**: campaign detail
   shows the campaign's shape and state, and the composition weight moves to the
   editor.
   **That editor is in no inventory.** `docs/react-screen-inventory.md`'s sixteen
   screens have *campaign detail* and no variant editor, because the Jinja UI
   composes inside the campaign page. The first cut grows again.
   **Named requirements, none of which the backend was designed against:**
   selection that produces a **preview**, **sorting** controls for module order,
   and **direct field editing** for overrides.
   **The API is JSON-blob shaped today, which is the concrete version of "not with
   json structure":** `ModuleInstanceCreate.module_data` and
   `ContentOverrideCreate.field_overrides` are both `dict[str, Any]`
   (`campaigns/models.py:76`, `overrides/models.py:11`). A client *can* assemble
   those dicts — it knows the field names from the manifest, per Cluster 2 — so
   this is not necessarily a new API. It does mean the editor does real work that
   nothing has specified.
   **Preview is the part that may not be servable today**, and it is worth
   checking rather than assuming: `GET /rendering/variants/{variant_id}` renders
   **saved** state. "Selection creating the preview" implies seeing a change before
   committing it, which is either save-then-render or a render-with-unsaved-changes
   endpoint that does not exist.
   **This is large enough to deserve its own treatment.** A real editor — preview,
   ordering, inline override, module picking — is not one screen decision; it is
   the substance of what a manager does all day, and this interview has one
   question about it. Whether it becomes a sixth cluster or a separate design
   interview is question 3b.
3b. ✅ **Does the variant editor need its own design interview?**
   **Resolution (2026-09-23): yes, its own interview — and it does not have to
   wait for Clusters 4 and 5.** The user corrected the assumption built into the
   question: *"It doesn't depend on audience or send."* It can therefore run in
   parallel with the rest of this document rather than after it.

   **The brief, in the user's words, recorded so the future interview starts from
   it rather than from my reading of it:**

   > *"it's an editor to build the variant (mainly email as it's the most complex)
   > to get the finished html(body) that goes to the send provider. It doesnt
   > depend on audience or send, it's 'only' live rendering content / layout blocks
   > (seeing what you've picked), options to override the content or to hide
   > elemtns (like no button, no headline), if multiple designs are prepared maybe
   > switching between designs. customizable functions. as we're doing beta /
   > stage 1 — concept is the most important to find a way that companies can
   > easily customize their frontend editor functions as the need it and how their
   > managers work best."*

   **The beta priority is the extensibility concept, not the editor.** What matters
   for stage 1 is *how an adopter customises the editor's functions to how their
   managers work* — which is the same posture as the drop-a-file module registry
   and the provider adapters, applied to the client. That reframes it from "build
   an editor" to "design the seam an editor is built on".
   **Scope named:** email first as the most complex case; the output is the
   finished HTML body the send provider receives; live rendering of the chosen
   content and layout blocks; content override; **hiding elements**; and switching
   between prepared designs.
   **One gap already visible in that list.** *Hiding an element* has no model:
   `ModuleInstanceDB` carries `variant_id`, `module_type`, `position`,
   `content_record_id`, `module_data` and `decision_slot_id` — **no visibility
   flag**. The only "hidden" in the codebase is
   [[ADR-086 — Decision Slots Fail Gracefully]]'s *hidden slot*, where a slot that
   resolves to nothing renders as an HTML comment — automatic degradation, not a
   manager's choice. Whether "no button" is expressible by clearing a field
   depends on each template, which makes it a template convention rather than a
   guarantee. That is a question for the editor interview, flagged now so it is not
   discovered mid-build.

4. ✅ **In what order does a manager bring a variant into existence?**
   **Resolution (2026-09-23): pick the channel, and the editor opens empty.**
   Creating a variant is one decision. *"If they need an existing layout they can
   start with duplicating an older campaign/variant."*
   **Established with it:** the one **irreversible** choice is made deliberately
   and alone. [[ADR-160 — Channel Model and Composition]] point 5 fixes channel at
   creation and gives it no setter anywhere, so isolating it from everything
   editable is the shape the model already wants.
   **Duplication becomes the reuse path**, which makes question 8 load-bearing
   rather than a footnote — "start from something" is not a creation option, it is
   a copy. Note the limit that falls out: a variant's channel cannot change, so
   duplication reuses a layout **within** a channel and an email variant can never
   become a push one.
   **Rejected with it:** a starting-design picker at creation time, since prepared
   designs are a concept that does not exist yet and question 3b's editor
   interview owns it; and content-first assembly, which would run against a model
   where a variant owns modules and modules reference content.

5. ✅ **How does a manager find the right content record while composing?**
   **Resolution (2026-09-23): answered by Cluster 2 question 11 — a picker
   pre-narrowed by what the slot can use, where the narrowing is a default and not
   a restriction.** It opens showing content ready for this variant's channel and
   matching what the module or slot requires; facets and search narrow further;
   and there is a visible, reversible way to show content that is not currently
   choosable, so a manager who prepared something unfinished can still reach it.
   Safe because Cluster 2 question 3b owes a required-field check before a send
   fires.
   **Question 2.12's second-order effect applies here specifically:** because
   campaigns carry facets too, this picker can pre-narrow by the **campaign's own
   facets** — building a B2B Lisbon campaign surfaces B2B Lisbon content first —
   which is a stronger default than the channel filter alone.
   **Not repeated here on purpose.** This question existed because the campaign
   side is the harder surface; the answer turned out to be one design serving both,
   and recording it twice would create two places to keep in step.

6. ✅ **When does a manager reach for a decision slot instead of fixed content?**
   **Resolution (2026-09-23): a deliberate choice, made when the module is
   created.** The user: *"when a manager creates a new module and picks the
   layout, they can choose between 'content catalog record' or 'decision engine
   strategy' — preview then shows either catalog input + override or a placeholder
   for the personalized block (maybe with override options to put a headline over
   it)."*
   **Established with it, and it is a good sign: the interaction maps one-to-one
   onto the data model.** `ModuleInstanceCreate` already carries
   `content_record_id` **or** `decision_slot_id`, both nullable
   (`campaigns/models.py:73-77`), so the fork the manager sees *is* the fork the
   model expresses. No new concept, no translation layer.
   **A personalised block still takes overrides**, per the user's aside about
   putting a headline over it — consistent with
   [[ADR-041 — Override Precedence]], where a field-level override wins over the
   resolved content whether that content was picked or chosen by a strategy.
   **Fixed is the default and personalisation is opt-in**, with the cost accepted:
   the engine only runs where somebody chose it, so catalogue depth can feed an
   engine nobody switched on. Question 2.4b's candidate count at the slot is the
   counterweight — it makes the engine's state visible where it is configured.
   **The preview behaviour belongs to question 3b's editor interview**, which is
   where "what a placeholder for a personalised block looks like" gets designed.

7. ✅ **What does a manager need to see about how a decision slot resolved?**
   **Resolution (2026-09-23): the distribution — what got chosen and how often —
   and not the individual resolutions.** Which records won, and how concentrated
   the picks are.
   **Established with it:** this is the shape that **exposes starvation directly**.
   One record winning 90% of the time is visible at a glance, which is the failure
   mode question 2.4b named and could not otherwise be seen — a slot resolving
   badly and a slot resolving well look identical row by row. Distribution answers
   *is the engine doing anything* without pretending to answer *is this right for
   Anna*, which it deliberately does not.
   **Two backend consequences, and the second is a hazard already in the code.**
   A **distribution endpoint** is owed: an aggregate over `DecisionResolutionDB`
   grouped by `content_record_id` with counts, which nothing exposes today.
   And **`GET /campaigns/decision-slots/{id}/resolutions` returns every resolution
   row, unpaginated** (`campaigns/router.py:286`,
   `campaigns/service.py:794`) — on the table whose own model comment calls it
   *"the fastest-growing table in the schema"*, measured at 96,040 rows. That route
   is the worst instance of the pattern Cluster 2 question 10 ruled against, and it
   exists on the one table where the row count is unbounded by design.
   **`reason` and `score` are not wasted by this answer.** They stay what
   [[ADR-085 — Decision Resolution Should Be Optionally Explainable]] made them: a
   diagnostic for answering *why did this person get that* after the fact, rather
   than something a manager browses. Question 1.5 established they are the
   machine's reasoning, distinct from the human's `decision_reason`.
   **Known cost accepted:** a distribution can look healthy while individual picks
   are poor, and nothing routinely surfaces that.

8. ✅ **When is duplication used, and what should the manager be asked or told?**
   **Resolution (2026-09-23): a wizard, because cross-brand duplication has real
   decisions.** Name and target brand, then content handling, then facet
   reassignment, then a review. One flow for both cases rather than a fast path
   and a slow one.
   **Established with it:** question 4 made duplication the **only** route to
   reusing a layout — "start from something" is a copy, not a creation option — so
   this is a primary flow rather than a convenience, and the weight is justified by
   what it carries.
   **It completes question 2.9b's commitment.** Facets are per brand, and the
   consequence the user named there was that duplicating across brands works *"only
   if they have shared values or the duplication wizard allows reassignment"*. This
   is the reassignment step, made explicit.
   **What the service already gives it, and what it does not.** `duplicate_campaign`
   (`campaigns/duplication.py:127`) already distinguishes the cases via
   `crossed_brands()`, runs `KEEP` within a brand where modules reference the same
   records and `COPY` across one where records must be duplicated, and already
   reports what crossed verbatim as readable labels — which is the review step's
   content. **What it cannot do is accept a mapping**: reassigning facet values on
   the way across is new, and lands with the facet model from Cluster 2 rather than
   as separate work.
   **A limit worth stating in the wizard rather than discovering:** a variant's
   channel is fixed at creation with no setter, so duplication reuses a layout
   **within** a channel. An email variant cannot become a push one.
   **Known cost accepted:** a wizard is heavy for the common same-brand copy, which
   needs no decisions at all. Accepted over two divergent paths.

---

### What Cluster 3 produced

**The largest finding is an absence.** *"In the backend process the real editor
was never discussed."* A manager will not compose by selecting content from a
dropdown and a layout from another; what is needed is live rendering of the
blocks they picked, module ordering, direct field editing rather than JSON, and
element hiding. **That editor appears in no inventory**, it is where the weight
of composing actually sits, and it gets **its own design interview** (question
3b) which does *not* depend on Clusters 4 or 5.

**Its beta priority is the seam, not the editor.** *"Concept is the most
important to find a way that companies can easily customize their frontend editor
functions as the need it and how their managers work best"* — the same posture as
the drop-a-file module registry and the provider adapters, applied to the client.

**Three backend gaps, bringing the running total to eleven.**

9. **No distribution endpoint for a decision slot** (Q7). The answer is an
   aggregate over `DecisionResolutionDB` grouped by content record; nothing
   exposes one.
10. **`GET /campaigns/decision-slots/{id}/resolutions` returns every row,
    unpaginated** (Q7) — on the table its own model comment calls the
    fastest-growing in the schema, measured at 96,040 rows. The worst instance of
    what Cluster 2 question 10 ruled against, on the one table whose row count is
    unbounded by design.
11. **`duplicate_campaign` cannot accept a facet-value mapping** (Q8), which
    question 2.9b's per-brand decision requires. Lands with the facet model.

**A capability with no model, found in the editor brief:** *hiding an element*.
`ModuleInstanceDB` has no visibility flag; the only "hidden" in the codebase is
[[ADR-086 — Decision Slots Fail Gracefully]]'s hidden slot, which is automatic
degradation rather than a manager's choice.

**Two things the model got right, worth recording because so much else is
missing.** The fixed-versus-personalised fork a manager sees maps one-to-one onto
`ModuleInstanceCreate`'s `content_record_id` or `decision_slot_id` (Q6). And
isolating channel as the single creation-time decision (Q4) is exactly the shape
[[ADR-160 — Channel Model and Composition]] point 5 already wanted, fixing it with
no setter anywhere.

**The second structural principle was named here: a screen answers one question.**
Cluster 1 rejected a dashboard for it and moved decision history out of the inbox
for it; question 1 moved monitoring out of the campaign list for it. Three
independent answers, one rule.

**Screen count keeps growing** — seventeen after Cluster 1, plus a variant editor,
plus a monitoring screen if question 1b decides it is not the deliveries screen.


## Cluster 4 — Choosing who receives it  ✅ CLOSED 2026-09-24, 7/7

*How a manager decides the audience, and what they must verify before trusting it.*
Screens: **audience groups**, **audience detail**, **recipients**,
**recipient detail**.

1. ✅ **How does a manager arrive at an audience for a campaign?**
   **Resolution (2026-09-24): the system suggests and the manager adjusts — and
   it starts on the campaign screen, not the audience screen.** The user: *"System
   suggests and manager adjusts (or 'force adds' recipients) — this is started on
   the campaign screen. On the audience screen manager can build audience 'from
   scratch' (find_by_criteria) or with a button 'suggest from campaign'. But this
   is hopefully not that necessary anymore in the future (system and ai suggestion
   beats human decision)."*
   **Established with it:** the primary path is **Cluster 1 question 1's thesis
   applied to audiences** — the system proposes, the manager judges. Building an
   audience by hand is the secondary path and is expected to **decline**, which is
   a statement about where the product is going rather than a feature ranking.
   **The machinery exists and is not on the JSON plane.**
   `suggest_include_blocks_for_campaign` (`audience/service.py:680`),
   `campaign_category_scores` (`:609`), `create_suggested_group_for_campaign`
   (`:696`) and `recalculate_suggested_blocks` (`:748`) all exist and are reachable
   only from `/ui/campaigns/{campaign_id}/suggest-audience`. **A JSON route is
   owed**, and it is filed under campaigns rather than audiences — which matches
   where the user says the flow starts.
   **Two entry points, deliberately:** the campaign workspace triggers suggestion
   as part of preparing a send; the audience screen offers *build from criteria*
   and a *suggest from campaign* button for working on a group directly.
   **"Force adds" is the load-bearing phrase**, and it pre-answers question 2:
   explicit members are framed as an **override on top of the rules**, not as a
   parallel way of building a group.

2. ✅ **Are explicit members an override on the rules, and does a force-add
   survive resolution?**
   **Resolution (2026-09-24): inclusion is a union, and exclusion segments beat a
   force-add. This reverses a dated decision.** The user: *"exclusion segments
   always should be excluded (a manager who decides that this is the group that
   shouldn't get it, because of reason X → they shouldn't get it as safety;
   **Shouldn't get it by human beats Should get it by system/human**) suppression
   like strict block lists are still a thing. Exclusion segments are more of an
   attribute / topic / interest / temporary reason; block list is a legal / data
   protection matter."*

   **This is the third structural principle the interview has produced: a negative
   decision outranks a positive one.** It generalises past audiences — wherever
   someone has said *not this*, that beats anyone or anything saying *yes this*,
   because the cost of wrongly including is higher than the cost of wrongly
   omitting.

   **Two kinds of exclusion, and the distinction is the decision:**

   | | What it is | Beats a pin? |
   |---|---|---|
   | **Exclusion segment** | attribute, topic, interest, a temporary reason — editorial and operational | **yes, now** |
   | **Blocklist / suppression** | legal and data-protection | yes, and always did |

   **What is being reversed, and where it lives.** `resolve_audience`
   (`audience/service.py:514`) implements
   `((∪ include) − (∪ exclude)) ∪ pins`, and its docstring states the rule
   **decided 2026-07-26**: *"a manual pin is a deliberate override and is always
   included — exclude blocks shape the rule-driven audience but never remove a
   hand-pinned recipient."* The new order is
   `((∪ include) ∪ pins) − (∪ exclude)`, then the consent floor as before.
   **It is not in an ADR — it is in a docstring and four documentation pages**
   (`Flow - Audience resolution`, `audience`, `MOC - System Overview`, and
   `docs/backlog.md`), plus the Jinja router and a template. **So this is not a
   supersession**, but it is a deliberate architecture decision reversing a
   recorded one, which is exactly the case that should now get a record rather
   than another docstring.
   **Blast radius, checked rather than assumed:** the tests that exist assert pins
   against the **consent floor** — `test_consent_gates.py:298-309` and
   `test_brand_scoping.py:881` — and that behaviour is **unchanged**. No test was
   found asserting a pin survives an *exclude block*, so the reversal may cost
   less than the number of documents implies. To be confirmed when it is built.
   **The consent/suppression floor is untouched** and stays absolute, which is the
   half of the old docstring that survives intact.

3. ✅ **What must a manager see to trust an audience before sending to it?**
   **Resolution (2026-09-24): the arithmetic — how the number was arrived at.**
   Not *1,204* but the working: included by rules, added by hand, removed by
   exclusion segments, dropped by consent, and the total that will actually
   receive.
   **Established with it:** this is what makes question 2's reversal **visible at
   the moment it matters**. A manager who force-added four people and sees
   *− exclusion segments −15* learns that their add was overridden, rather than
   discovering it from a send that reached fewer people than expected. A bare
   count could not have shown that, which is why the precedence change and this
   answer belong together.
   **The numbers already exist and are discarded.** `resolve_audience`
   (`audience/service.py:514`) builds `include_ids`, `exclude_ids`, the pin set
   from `get_member_recipient_ids`, and then applies the consent floor — every
   term of the arithmetic is computed inside that function and **only the final
   list is returned**. So this is not new logic; it is a return shape that keeps
   what the function already knows.
   **It subsumes the Q1.5 gap without depending on it.** The arithmetic explains
   the *group*; the missing per-membership reason explains an *individual*. Both
   are wanted, and the arithmetic is answerable today while the reason needs the
   request body that `POST /api/audience-groups/{group_id}/members/{recipient_id}`
   does not have.
   **Rejected, with reasons worth keeping:** a sample of members is concrete but
   **blind to absence**, and the people wrongly excluded are exactly those not in
   it; rules-in-prose checks intent rather than outcome, and the outcome is what
   a manager is about to send to.
   **Per-channel is not a footnote here** — the consent line differs by channel,
   which is question 4.

4. ✅ **One group resolves to different people per channel. What does a manager
   need to see about that?**
   **Resolution (2026-09-24): the arithmetic is always per channel — there is no
   channel-less number.** An audience count means nothing until a channel is
   named, so the client never shows one without it.
   **Established with it:** this removes a class of error the codebase has already
   suffered. `resolve_audience`'s docstring records it: consent is keyed
   `(recipient, brand, channel, purpose)`
   ([[ADR-163 — Per-Channel Consent and Addressability]] point 1), and gating a
   push send on email consent *"asks the wrong question twice over — it would
   admit people who accepted email and never accepted notifications, and refuse
   people who did the reverse"*. It defaulted to email while email was the only
   channel, **which made a push send unplannable: the audience resolved to nobody
   and the planner reported "0 consenting recipients"**.
   **The concrete implementation rule that follows: the client always passes the
   channel explicitly and never relies on the default.**
   `resolve_audience(db, group_id, channel=DEFAULT_CHANNEL)` still defaults to
   email, deliberately, for screens previewing an email audience. That default is
   convenient for the service and a trap for a client that shows numbers — under
   this resolution a defaulted channel is always wrong on screen.
   **Where the channel comes from:** the variant, when planning a send. When a
   manager opens an audience group directly there is no variant, so the screen
   either asks or shows each registered channel. That is a presentation choice
   left open; what is settled is that it may not show a bare number.
   **Rejected:** flagging the difference only when it "surprises", since a
   threshold is the system deciding what is notable — the shape turned down in
   questions 2.2 and 1.3.

5. ✅ **What does a manager legitimately do on the recipients screen?**
   **Resolution (2026-09-24): look one person up — "why did Anna get this" — and
   nothing else. Read-only, with a planned end of life.** The user: *"no editing
   options (unless maybe an unsubscribe button in case of emergency, tho this can
   be part of the gdpr package) — in the future 'Nothing' as soon as a crm can
   take over and gets all recipient information from the platform."*
   **Established with it:** this screen is **temporary by design**, which bounds
   how much it is worth investing in. It exists because the reasoning lives here
   and not in the CRM — [[ADR-120 — CRM as Customer Source of Truth]] owns the
   person, this platform owns why they were chosen — and it goes away when the CRM
   can receive that reasoning.
   **Editing is refused**, which keeps [[ADR-126 — Maintain Local Recipient Projection]] honest: a projection that can be edited is a second source of
   truth. The emergency unsubscribe is explicitly parked as *possibly* belonging
   to the GDPR package instead — [[ADR-004 — Privacy Operations as a First-Class Architectural Concern]] and [[ADR-154 — Erasure and Retention]] are its natural
   home, and putting it there keeps this screen read-only.
   **The screen is not buildable as stated today, and the reason is structural
   rather than a missing endpoint.** "Why did Anna get this" needs three things:
   her consent per channel (exists), what was sent to her, and which audiences she
   is in. There is **no per-recipient delivery query** and **no reverse membership
   lookup** — and the second cannot simply be added, because **rule-based
   membership is computed at resolution time and never stored**. Only *pins* are
   rows in `AudienceGroupMemberDB`; everyone included by a rule exists as a set
   inside `resolve_audience` and nowhere else. So "which groups is Anna in" is
   answerable only by resolving every group, or only for hand-pinned membership.
   **That is worth deciding rather than discovering**: either the screen answers a
   narrower question than its name suggests, or resolution results become
   durable — which is a significant model change and bears on
   [[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]], whose whole
   point is that this data is derived.
   **What is answerable today** is the decision side: `DecisionResolutionDB` stores
   `recipient_id`, `content_record_id`, `reason` and `score`, so *why this content*
   has an answer even where *which audience* does not.

6. ✅ **What does a manager need from the consent grid, given the screen is
   read-only?**
   **Resolution (2026-09-24): only the cells that matter — the channels this brand
   actually sends on — with drift against the CRM flagged.** Not the full
   `(channel, purpose)` matrix.
   **Established with it:** both halves already exist and neither is new work.
   Channel availability is a per-deployment setting (`available_channels` and
   `channel_available`, `settings/service.py:158-178`), and drift has an endpoint:
   `GET /recipients/consent/drift`, alongside `GET /recipients/consent/sync-log`.
   **Flagging drift is the point rather than a nicety** — on a projection, the
   most likely way the screen lies is by being out of date, and
   [[ADR-126 — Maintain Local Recipient Projection]] accepts that copy in exchange
   for not depending on the CRM at send time.
   **It honours the schema-names warning.** `Recipient.email` and
   `email_consent_status` are the **flattened email cell** of a grid keyed
   `(brand, channel, purpose)` ([[ADR-163 — Per-Channel Consent and Addressability]] point 2), and `docs/react-screen-inventory.md` warns against
   building a single "Consent: yes/no" control from them. Showing cells per channel
   — even a reduced set — is the shape that cannot collapse into that mistake.
   **Known cost accepted, and it is sharper than it looks:** hiding channels not in
   use hides one possible explanation for why a send skipped somebody. If a send
   targets a channel the deployment has switched off, the consent grid will not say
   so — the answer lives in settings instead. Worth remembering when question 5's
   "why did Anna get this" is built.

7. ✅ **When and why does a manager press Recalculate, and should they have to?**
   **Resolution (2026-09-24): once a group exists, recalculation is always manual
   — unless the send itself was set to re-resolve. And a significantly changed
   campaign gets a new segment rather than a recalculated one.** The user: *"once
   created recalculation is always a manual task unless in the send 'recalculate
   before send' was activated. If the campaign changed significantly the manager
   would simply create a new segment."*
   **Two different operations, and keeping them apart is the point.** The answer
   touches both and they must not be conflated:

   | | What it re-does | When |
   |---|---|---|
   | **Re-suggest** (`recalculate_suggested_blocks`, `audience/service.py:748`) | derives the **rules** again from the campaign's content categories | manual only |
   | **Re-resolve** (`audience_resolution_mode="rerun"`) | runs the **existing rules** against current recipients before firing | automatic, if the send says so |

   Re-suggesting can overwrite rules a manager edited; re-resolving cannot,
   because it changes no rules — it only asks who matches them now. That is why one
   is manual and the other may be automatic, and it is consistent rather than an
   exception.
   **Established with it:** *create a new segment* is the normal response to a
   campaign that moved, not *recalculate*. Re-suggestion is therefore a rare
   operation, which argues against building much around it — and it keeps the
   cluster principle intact, since the system never silently replaces rules a
   person adjusted.
   **This hands Cluster 5 question 2 a constraint rather than a free choice.**
   `freeze` versus `rerun` is now *"recalculate before send"* from the manager's
   side — a property of the send, phrased in audience terms — which is how that
   question should be put rather than as two mode names.

---

### What Cluster 4 produced

**A dated decision is reversed** (Q2). `resolve_audience` implements
`((∪ include) − (∪ exclude)) ∪ pins` and its docstring records, from 2026-07-26,
that *"a manual pin is always included — exclude blocks never remove a hand-pinned
recipient"*. That is now wrong: exclusion segments beat a force-add. The
consent/suppression floor is untouched and stays absolute. **It is not in an ADR**
— it lives in a docstring and four documentation pages — so this is no
supersession, but it is a deliberate reversal that should get a record rather than
another docstring. Tests assert pins against the *consent floor* only, so the
blast radius is smaller than the document count suggests.

**The third structural principle: a negative decision outranks a positive one.**
*"Shouldn't get it by human beats Should get it by system/human."* Wrongly
including costs more than wrongly omitting, and that generalises well past
audiences.

**A distinction the model does not have** (Q2): an **exclusion segment** is an
attribute, topic, interest or temporary reason and is editorial; a **blocklist** is
legal and data-protection. Both are `kind="exclude"` today.

**Four backend gaps, bringing the running total to fifteen.**

12. **No JSON route for audience suggestion** (Q1). `suggest_include_blocks_for_campaign`,
    `campaign_category_scores`, `create_suggested_group_for_campaign` and
    `recalculate_suggested_blocks` all exist and are reachable only from Jinja —
    and Q1 makes suggestion the *primary* way an audience comes into being.
13. **`resolve_audience` returns only the final list** (Q3), discarding the
    arithmetic it computed: included by rules, added by hand, removed by
    exclusions, dropped by consent. The numbers exist inside the function.
14. **No per-recipient delivery query and no reverse membership lookup** (Q5) —
    and the second is structural, not missing: rule-based membership is **computed
    at resolution time and never stored**, so only pins are rows. "Which groups is
    Anna in" is answerable only by resolving every group. Bears on
    [[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]].
15. **`resolve_audience` defaults `channel` to email** (Q4) — convenient for the
    service, a trap for a client that shows numbers, and the recorded cause of a
    push send once resolving to nobody.

**Screens with a planned end of life** (Q5). Recipients is read-only and
**temporary by design** — it exists because the reasoning lives here rather than in
the CRM, and it goes away when the CRM can receive that reasoning. That bounds
how much it is worth building.

**A constraint handed forward.** Cluster 5 question 2 should ask about *"recalculate
before send"* rather than about `freeze` versus `rerun` — the manager's framing, in
audience terms, for what is a property of the send.


## Cluster 5 — Planning, checking and firing a send  ✅ CLOSED 2026-09-24, 8/8

*What a manager confirms before real mail leaves, and what they watch afterwards.*
Screens: **deliveries**, **delivery detail**.

1. ✅ **What does a manager confirm before real mail leaves, and what should stop
   them?**
   **Resolution (2026-09-24): a review screen, with two tiers — hard failures
   block, everything else informs.** It states what will happen: the snapshot, the
   audience arithmetic per channel, provider, from-address and schedule. Things
   that make the send broken or unlawful refuse outright; everything else is
   stated and the manager decides.
   **Established with it, and it resolves a tension that has been building: the
   system blocks what is broken, and reports what is merely questionable.** The
   cluster principle — *the system reports, the manager decides* — held everywhere
   until question 2.3b asked for a real check, because an empty push notification
   reaching a real device is not a judgement call. This is the reconciliation, and
   it is narrow on purpose: blocking is reserved for *broken*, not for
   *questionable*.
   **It fits the model rather than needing a new one.**
   `prepare_send_from_audience` already creates a `SendInstanceDB` in **`draft`**
   with one execution per recipient, and firing is a separate call
   (`POST /delivery/send-instances/{id}/send`). **The review screen is that
   draft** — planning and firing were already two steps, and this is the screen
   that was missing between them.
   **What it needs from the backend**, and the first is C8 itself:
   planning has no JSON route at all; the arithmetic from question 4.3, which
   `resolve_audience` computes and discards; and the required-field check question
   2.3b owes, which nothing performs.
   **Open rider: the list of what blocks.** Empty required fields and zero
   recipients are clearly blocking; the recipient cap already raises. Whether
   anything else does — a thin decision slot, an excluded force-add — is not
   settled, and getting that list wrong in either direction is how this screen
   becomes either a rubber stamp or an obstacle.

2. ✅ **"Recalculate before send": a per-send choice, or a deployment default?**
   **Resolution (2026-09-24): always recalculate — the choice is removed.** A send
   goes to whoever qualifies at the moment it goes out, not whoever qualified when
   it was planned. Consent and exclusions are therefore always current at the only
   moment that matters.
   **Established with it:** one fewer mode, one fewer thing for a manager to
   understand, and the lawful answer by construction rather than by configuration.
   It also makes question 4.2's reversal meaningful in practice — an exclusion
   segment applied after planning still removes the recipient, because the rules
   are re-run.
   **The current default is backwards relative to this.**
   `prepare_send_from_audience` takes `audience_resolution_mode: str = "freeze"`
   (`delivery/service.py:202`), `SendInstanceDB.audience_resolution_mode` defaults
   to `"freeze"` too, and the function validates the value is one of the two. Under
   this resolution **`freeze` is the mode that should never be used**, so either the
   default flips or the concept goes. `reconcile_executions_to_audience`
   (`delivery/service.py:350`) becomes the always-path rather than the exception.
   **Whether the column survives is deliberately not decided here** — removing it
   is a migration, keeping it is a setting nobody sets, and that is an
   implementation call rather than a workflow one.
   **The cost is real and lands on question 1.** The number a manager reviewed is
   not necessarily the number that receives, because the audience is re-resolved
   after they approved it. The review screen must say so rather than present a
   figure it cannot honour — the arithmetic is *as of now*, and the send recomputes
   it. Stating that is the honest version; showing a precise number that silently
   changes is not.

3. ✅ **Does a manager schedule sends, or fire them?**
   **Resolution (2026-09-24): both, and one mechanism covers both — a schedule
   datetime.** The user: *"a managers campaign is scheduled and rarely fired
   directly, an automation / triggered is fired at the moment and rarely
   scheduled; but — a triggered can always send a schedule datetime 'now + 5
   minutes', so we can implement a schedule datetime."*
   **Established with it:** the two cases split by **caller**, not by feature. A
   manager's newsletter is scheduled, so the review screen leads with a date; an
   automation wants immediacy and can express it as a near-future time. **There is
   no separate "fire now" path to build for the machine plane**, which is a real
   simplification — one field, one code path, two uses.
   **Question 2 makes scheduling safe in a way it was not.** A send scheduled for
   Tuesday resolves its audience on Tuesday. Without always-recalculate, a schedule
   meant sending to a list fixed days earlier, which is exactly where consent goes
   stale.
   **The operational consequence, worth stating because it is the adopter's to
   configure:** a scheduled send fires when `process_due_scheduled_sends` next
   runs, and that is a **cron seam** the deployment drives rather than something
   the platform guarantees. "Now + 5 minutes" is only as prompt as that interval.
   An adopter polling hourly has an automation that reacts hourly, which may
   surprise them.
   **The direct route still exists** — `POST /delivery/send-instances/{id}/send`
   fires immediately — so a manager pressing send in-app need not wait for a
   scheduler. What this resolution removes is the need for an *automation* to use
   it.

4. ✅ **What question does the deliveries list answer, and is it the monitoring
   screen from question 3.1?**
   **Resolution (2026-09-24): no — they are two screens. Monitoring is
   campaign-level; deliveries is send-level.** Monitoring answers *where are my
   campaigns*, including ones that have sent nothing yet. Deliveries answers *what
   did this send do*.
   **This answers question 3.1b**, which asked whether the monitoring screen the
   user requested in the campaign list was this one. It is not.
   **Established with it:** the *a screen answers one question* rule decides it.
   A campaign in flight with nothing sent has no row in a send list, and a send
   that failed is not a campaign state — so one screen would answer neither
   question well. That rule has now decided four screen boundaries: no dashboard,
   history out of the inbox, monitoring out of the campaign list, and this.
   **The cut grows to nineteen.** Sixteen in the inventory, plus decision history
   (question 1.6), plus the variant editor (question 3.3), plus monitoring. Worth
   restating plainly: **this interview has added three screens and removed none**,
   and each was added because a screen was being asked to answer two questions.
   **Neither is servable today.** Deliveries has no flat list and no get-by-id —
   only the snapshot-scoped route — which is the gap already logged with C8. And
   **monitoring needs a campaign-level state view that does not exist at all**: no
   route answers "which campaigns are in flight", because campaign status is a
   column on the campaign and *in flight* is derived from its variants, their
   snapshots and their sends.

5. ✅ **What does a manager watch during and after a send?**
   **Resolution (2026-09-24): the three counts — sent, failed, excluded — and what
   explains the gap between the total reviewed and the total sent.** A manager who
   approved 1,104 and sees 1,098 sent gets an answer rather than a discrepancy.
   **Question 2 is what makes the gap routine rather than exceptional.** Because
   the audience re-resolves at fire time, `excluded_count` is no longer an edge
   case — it is the number that reconciles the review screen to reality, and it
   carries the consent withdrawn and exclusions applied between approval and send.
   **What needs defining rather than assuming:** whether `excluded_count` today
   means *excluded at plan time by the consent gate* or *removed at re-resolution*.
   Under this resolution the screen needs the second, and the two are not the same
   number. Executions are created one per recipient at plan time and
   `reconcile_executions_to_audience` adjusts them at fire time, so the delta is
   derivable — but which column holds it is a question for the build.
   **This is the third response model found dropping fields its table stores, and
   three is a pattern rather than three accidents:**

   | Model | Table has | Model exposes |
   |---|---|---|
   | `ModuleVariableOut` | `label`, `envelope` | neither |
   | `PendingActionDetail` | `subject_type`, `subject_id` | neither |
   | `SendInstance` | 15 columns incl. three counts | 8, none of the counts |

   Each was found by asking what a screen needs, which is the method working — but
   it suggests the response models were written to the routes that existed rather
   than to what a client would ask for. **Worth a sweep rather than three
   one-line fixes**, and worth remembering when the ADR work is done: the schema
   honesty pass in Phase 0 caught bare dicts and did not catch under-exposure.
   **Live progress is not required**, which spares the client polling: the counts
   are the answer, before and after.

6. ✅ **A send fails for some recipients. What does the manager do?**
   **Resolution (2026-09-24): no retry button. Build a segment instead.** The
   user: *"system/server fails that can be retried usually are taken care of the
   provider. in general it depends. no 'retry button', but building a segment with
   the option to select 'campaign X was / wasnt delivered' would work."*
   **Established with it, and it is the most economical answer in the cluster:**
   *resend to whoever missed it* is an **audience** question, not a delivery
   feature. No retry subsystem, no backoff, no idempotency worry, no risk of
   sending twice — the manager builds a segment of people a campaign did not reach
   and sends to it, using machinery that already exists for a different reason.
   **It also disposes of the transient-failure case correctly:** retryable
   provider failures are the provider's job, not this platform's.
   **What it needs is a new kind of criterion, and that is the real cost.**
   Criteria today support exactly four keys — `language`, `status`, `category_id`
   and `min_score` (`audience/service.py:402-415`) — and **all four are recipient
   attributes**. *"Campaign X was or was not delivered"* queries
   `DeliveryExecutionDB` instead, so audience criteria would span two domains for
   the first time: who someone **is**, and what has **happened** to them.
   **That is a bigger door than this question opens.** The same mechanism would
   serve engagement criteria — opened, clicked, did not open — which is the
   insight and signal layer, and it is the shape of the user's own Cluster 1
   example, *"select recipients each day that should get a reactivation email"*.
   They said that case comes from **external automation**, so there may be two
   paths rather than one: criteria the platform evaluates, and segments an
   orchestrator populates with a reason. Worth deciding which before building
   either.

7. ✅ **Where does a test send belong: a deployment diagnostic, or part of the
   manager's pre-flight?**
   **Resolution (2026-09-24): both — one endpoint, two surfaces, two meanings.**
   The operator uses it at setup to answer *does mail leave this installation at
   all*; the manager uses it before a send to answer *does this look right in a
   real inbox*. `POST /delivery/send-test` serves both.
   **This overturns the inventory**, which cut send-test from the first cut as *"an
   operator tool that belongs beside the deployment docs"*. Half of that is right
   and the half it missed is the manager's: no review screen can show what an email
   client does to the HTML, which is precisely what
   [[ADR-063 — Rendering Parity Over Rendering Implementation]] exists about.
   **The permission tension is real and is recorded rather than resolved.**
   `send-test` is priced `sends.execute` by its own entry in the policy table — the
   same permission as firing for real — and the reasoning is sound for a manager:
   *"It reaches a real inbox through a real provider — that it goes to one typed
   address rather than to an audience makes it smaller, not different in kind."*
   For the **operator** case it is awkward: somebody verifying an installation must
   hold the permission to fire campaigns. Whether that is acceptable (an operator
   at setup is trusted anyway) or wrong (setup should not require send rights) is
   **open**, and it is the kind of question `MAILS_A_PERSON` in
   `test_api_guard.py` will make loud if the answer changes — that set is asserted
   in both directions.
   **One feature with two audiences usually serves one badly**, which is the cost
   accepted here. The mitigation is that the two surfaces differ: the manager's is
   a button on the review screen with their own address prefilled; the operator's
   is a documented call.

8. ✅ **When is the approval gate on a send used: machines only, or do people
   route sends to each other?**
   **Resolution (2026-09-24): people too — a manager may require a second pair of
   eyes on their own send.** Sending to fifty thousand people is worth a
   colleague's check, and question 1.1's thesis makes deciding the manager's job
   rather than an interruption to it.
   **It contradicts a recorded build note and needs a record.**
   [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]]'s notes
   state that *"a person firing a send **is** the approval, which was implicit
   while people could not reach this plane at all"*. That reasoning was correct
   when only machines could request; it stops being sufficient once a person can.
   It extends rather than reverses the 2026-09-19 addendum, which already decided
   approving requires a session-authenticated person and is refused to a bearer
   credential.
   **It needs a concept the model does not have.** `may_send_unattended` is a
   column on an **integration** and does not exist on a user, so "this send needs
   approval" has nowhere to live on the person's side.
   **And it opens a concrete hole, found by checking rather than assumed.**
   `may_decide` (`approvals/service.py:345`) checks the action's own
   `approve_permission` against the **request's** brand — which is the right design
   and is well argued in its docstring — but **nothing compares the decider to the
   requester**. `requested_by_type` and `requested_by_id` are stored and never read
   for this. That has been safe purely by construction: machines requested, and a
   machine cannot approve. **The moment a person can request, they can approve
   their own request**, and the second pair of eyes becomes the first pair clicking
   twice. A self-approval refusal is owed with this feature, not after it.
   **The alternative that was not taken** — a brand-level setting requiring
   approval on every send — stays available if per-send proves too easy to skip;
   it would be governed like the recipient cap rather than chosen per action, and
   it needs Settings, which is gap C2.

---

### What Cluster 5 produced

**The principle got its exception, and it is narrow.** *The system blocks what is
broken, and reports what is merely questionable* (Q1). Blocking is reserved for
*broken* — an empty required field, no recipients — and everything else is stated
for the manager to judge. That reconciles the cluster principle with question
2.3b's demand for a real check.

**A mode is removed** (Q2). Always recalculate; `freeze` is the mode that should
never be used, and both the function default and the column default currently say
`freeze`. The cost lands on Q1: the reviewed number is *as of now* and the send
recomputes it, so the review screen must say so rather than present a figure it
cannot honour.

**Three more backend gaps, and one pattern.**

16. **Audience criteria cannot express delivery history** (Q6). Today's four keys
    — `language`, `status`, `category_id`, `min_score` — are all recipient
    attributes. *"Campaign X was or was not delivered"* queries
    `DeliveryExecutionDB`, so criteria would span who someone **is** and what has
    **happened** to them. The same door opens engagement criteria.
17. **Nothing prevents self-approval** (Q8). `may_decide` checks the action's
    permission against the request's brand and never compares decider to
    requester. Safe only while machines requested and could not approve; a hole
    the moment a person can request.
18. **No campaign-level state view** (Q4). Nothing answers "which campaigns are in
    flight" — *in flight* is derived from variants, snapshots and sends.

**The pattern, named because three is not a coincidence** (Q5): response models
routinely expose less than their tables store — `ModuleVariableOut` drops `label`
and `envelope`, `PendingActionDetail` drops `subject_type` and `subject_id`,
`SendInstance` exposes 8 of 15 columns and none of the three counts. Each was
found by asking what a screen needs. **Worth a sweep rather than three one-line
fixes**: Phase 0's schema-honesty pass caught bare dicts and did not catch
under-exposure.

**Two things solved by reusing what exists rather than building.** A failed send
needs no retry feature — build a segment of who missed it (Q6). And an automation
needing an immediate send can schedule `now + 5 minutes`, so there is no separate
fire-now path for the machine plane (Q3).

**The inventory is overturned once** (Q7): `send-test` is not only a deployment
diagnostic. No review screen can show what an email client does to the HTML, which
is what [[ADR-063 — Rendering Parity Over Rendering Implementation]] exists about.
Its `sends.execute` pricing is left as an open question for the operator case.

**Two records owed.** ADR-168's build note — *"a person firing a send is the
approval"* — becomes insufficient once people can request (Q8). And the
`freeze`/`rerun` choice disappearing is a decision worth recording wherever the
mode is documented.


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
