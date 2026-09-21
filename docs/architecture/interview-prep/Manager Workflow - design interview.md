---
type: interview-prep
topic:
  - architecture
  - frontend
  - design
created: 2026-09-21
status: open
---

> **Status: interview OPEN.** Cluster 2 is written in full as a format test.
> Clusters 1 and 3–5 are headlines only, pending approval of the clustering
> itself. **No further frontend work before Cluster 2 closes** — the questions in
> it decide screens that are already built.

# Manager Workflow — design interview (forward-looking)

Like [[Omni-Channel - design interview]] and [[AI Layer - design interview]],
this file gathers the **decisions needed before writing ADRs**, rather than
reviewing implemented code.

## Why this came up

The React client was being built from the API surface. Two phases shipped —
sign-in, the shell, and seven read-only screens — and a third was about to design
the send-planning screen from a service function's signature.

The user stopped it, on 2026-09-20, with the objection that matters:

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
that better than another. That gap is what this interview fills.

**The clearest instance, and the one that prompted this.** The user asked how
push fields and email fields are kept from being mixed up in an authoring form —
a workflow question. It was answered by investigating where field-to-channel
knowledge lives in the backend — a data-modelling question. The investigation was
accurate and it answered the wrong thing.

---

## Established up front (don't re-litigate)

These bind the answers. They are not open in this interview.

**The client.**
- [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] — a plain
  React SPA, routing called as a library, types generated from the schema.
- [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]] — the
  session cookie, `X-CSRF-Token`, same-origin serving.
- [[ADR-173 — The Manager Client's Runtime Dependencies]] — React Aria for
  behaviour and accessibility, plain CSS for appearance, TanStack Query for the
  cache.
- [[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]] —
  the working brand is the session's, resolved server-side. A screen never asks
  which brand it is in; it asks what it can see.

**Channels and content.**
- [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] — the core is
  channel-neutral orchestration, not an email tool.
- [[ADR-160 — Channel Model and Composition]] point 3 — **channel readiness is a
  property of the content record**, and channel fields are separate and required,
  **never derived from email fields**.
- [[ADR-161 — Channel Execution Shapes]] point 7 — the split: provider `.py` =
  capabilities · module manifest = fields and limits · channel = an attribute on
  the variant plus which manifests it accepts.
- [[ADR-162 — Channel Rendering and Artifacts]] point 1 — the variant holds no
  channel fields; subject and preheader are module fields. Both alternatives were
  rejected as *"a second place where channel fields live, beside the manifests."*
- [[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]] — flows
  are sequenced variants. There is no canvas to build.

**Already ruled, and directly relevant to Cluster 2.**
[[Omni-Channel - design interview]] Cluster 1 question 2 settled that a variant
carrying both "A/B version" and "channel expression" reads awkwardly, and judged
it *"a **display** concern — the UI groups by channel — not a model one."*

**So: that the UI groups by channel is settled. How it groups was never asked,
and is question 2 below.**

**The screen cut.** Sixteen screens in the first cut (core loop plus supporting),
per the inventory. Diagnostics and sub-pages are out. Administration is last.

---

## Where the frontend already stands

Built and committed as of 2026-09-21. **The decisions marked ⚠️ were made by the
implementer, not by anyone who uses this product**, and are in scope for this
interview to overturn.

| Built | Status |
|---|---|
| Sign-in, two-step code flow | Follows ADR-151 §2's uniform response. Not a workflow question. |
| Shell, brand switcher, sign-out | Switcher hidden when `switchable` is false, per ADR-150 pt 4. |
| ⚠️ **Approvals as the landing screen** | Justified from ADR-169, which is about the *model* of flows, not about what a manager opens first. **A guess.** |
| ⚠️ **Table columns on all four lists** | Name/status/updated, chosen by the implementer. No basis. |
| ⚠️ **Campaign rows do not navigate** | Defensible (B11 is unbuilt) but a design call. |
| ⚠️ **Content fields rendered as one flat list** | Every field in `content` shown in insertion order, email and push interleaved. **This is the thing the user objected to.** |
| Approval detail reads `may_decide` | Correct — the rule stays on the server per the inventory. |

Deliveries is **absent**: its read surface is snapshot-scoped only, with no
list route and no get-by-id, so it is unbuildable today. Logged with C8.

---

## Sketch (not decided — input to the interview)

My lean, stated so it can be argued with rather than absorbed silently.

A manager's day looks like *"what needs me?" → "make the thing" → "who gets it?"
→ "send it" → "what happened?"*. The clustering below follows that shape. If the
work actually divides by role, by cadence, or by campaign rather than by task,
the clustering is wrong and Cluster 2 is the only part worth keeping.

On content specifically: I lean toward **one record carrying every channel's
fields**, shown in per-channel sections rather than tabs, because ADR-160 point 3
already makes readiness a property of the record and a tab hides the thing a
manager most needs to see — that push is empty. **That lean is exactly what
question 1 and question 2 exist to test, and it may be wrong.**

---

## Planned interview — five clusters

Clusters 1 and 3–5 are **headlines pending approval of the clustering**. Only
Cluster 2 is written out.

### Cluster 1 — The daily loop and the home screen
*What a manager opens this for, what is waiting, and what "done for today" means.*
Screens: **approvals**, **approval detail**, and the shell itself — nav order and
what the landing screen is.

### Cluster 2 — Authoring content across channels  ← **written in full below**
*How one message becomes email and push without the two being mixed up.*
Screens: **content list**, **content detail**, **categories**, **category detail**.

### Cluster 3 — Composing a campaign
*What gets assembled, in what order, and what campaign detail is actually for.*
Screens: **campaigns list**, **campaign detail** (inventory B11), **decisions**,
**decision slot detail**.

### Cluster 4 — Choosing who receives it
*How a manager decides the audience, and what they must be able to verify first.*
Screens: **audience groups**, **audience detail**, **recipients**,
**recipient detail**.

### Cluster 5 — Planning, checking and firing a send
*What a manager confirms before real mail leaves, and what they watch afterwards.*
Screens: **deliveries**, **delivery detail**.

---

## Cluster 2 — Authoring content across channels

Seven questions. Each carries the constraint that already binds it, and my lean
where I have one.

1. **Is a content record one message expressed in several channels, or is a push
   message a different record from the email message?**
   *Constraint: [[ADR-160 — Channel Model and Composition]] point 3 makes channel
   readiness a property of the content record, and push fields separate and
   required. Lean: one record.*
   The workflow question underneath is which sentence describes the work: *"write
   the beach article, then give it a push title"*, or *"write the beach email;
   separately, write the beach push"*. The first makes a record a message with
   several expressions. The second makes a record a channel-specific artifact and
   pushes the "same story" relationship somewhere else — a category, a naming
   convention, or nothing.
   **This question also decides an open backend conflict**, so it is worth more
   than it looks: `CONTENT_FIELD_GROUPS` (`backend/app/content/service.py:101-108`)
   declares which fields belong to which channel, its own docstring calls itself a
   stopgap, and [[ADR-162 — Channel Rendering and Artifacts]] point 1 forbids a
   second home for channel fields beside the manifests. Nothing is being changed
   there until this is answered.

2. **When a manager opens a content record, what do they see first?**
   All fields flat in one list? Email and push as labelled sections, both always
   visible? Tabs, one channel at a time? Or only the channels already filled, with
   the rest added deliberately?
   *This is the question I answered from the backend instead of asking. Lean:
   sections rather than tabs, so that "push is empty" is visible without a click —
   but that presumes emptiness is something a manager needs to see, which is
   question 3.*
   Worth knowing: the field order a manager sees today is **JSON insertion
   order**, which is an accident of how the record was written, not a decision.

3. **What tells a manager a record is ready for push?**
   *Constraint: [[ADR-161 — Channel Execution Shapes]] point 7's rider says
   catalogue readiness is "push fields not empty" — and **that is not implemented
   anywhere**. No readiness predicate exists in `app/`.*
   Is readiness computed by the system and displayed, or asserted by the manager
   the way `status` is? And is "not ready for push" a warning, a filter, or simply
   a fact shown without judgement? The answer decides whether the client displays
   a computed badge, or whether the backend grows a predicate first.

4. **Does a manager fill channel fields speculatively, or only once a variant on
   that channel exists?**
   Put concretely: when someone writes an article today, do they fill push fields
   because the article *might* be pushed, or only when a push variant is actually
   being composed?
   This decides whether authoring is channel-aware at all. If fields are filled
   speculatively, every record carries every channel's fields and the form is
   channel-shaped from the start. If not, authoring is driven from the campaign,
   and the content screen is the wrong place for channel fields entirely.

5. **When a channel is added later, what happens to the records that already
   exist?**
   Adding a channel is two files (ADR-160 point 6). Several hundred content
   records would then have no fields for it. Is that a backlog a manager works
   through, a filter ("show me records not ready for WhatsApp"), or invisible
   until a campaign needs it?
   *No lean. This is the question that most distinguishes a reference architecture
   from a demo, and I do not know the answer.*

6. **Is the person writing email copy the same person writing push copy?**
   Bears on whether this is one screen or two, and on whether channel authoring
   needs a permission of its own — today it does not have one.
   If they are different people, "push is empty" is a **handoff**, not a warning,
   and the screen has a job nobody has described yet.

7. **Are categories authored alongside content, or managed separately?**
   Categories govern what a decision slot may pick, so they are consumed by
   decisioning — but they are attached while writing.
   *This also settles a clustering question: if categories are part of authoring
   they belong in this cluster; if they are taxonomy administration they belong in
   Cluster 3 with decisions, or in administration entirely.*

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
