---
type: adr
status: proposed
topic:
  - architecture
  - automation
  - campaigns
  - consent
created: 2026-09-19
source:
  - "Journey/flow design conversation (2026-09-19)"
depends_on:
  - "[[ADR-142 — Autonomous Workflows and the Automation Boundary]]"
  - "[[ADR-140 — AI Capability Layer]]"
  - "[[ADR-160 — Channel Model and Composition]]"
  - "[[ADR-163 — Per-Channel Consent and Addressability]]"
  - "[[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]"
enables:
  - "[[ADR-154 — Erasure and Retention]]"
---

## Status
Proposed

## Context

The question has been open since 2026-09-15, when the [[ADR-163 — Per-Channel Consent and Addressability]] addendum found there is **no unsubscribe page anywhere** and **no double-opt-in process** — the only opt-out writer is a provider webhook. The framing was corrected at the time and the correction is what this record answers: not *"we need to build an unsubscribe process"* but *"how do we build flows and journeys at all — an automation studio like Salesforce, or a Python script?"*

Three things made it urgent rather than interesting.

**It gates the React frontend.** A journey canvas is the largest unknown surface in a manager UI, and no screen below it can be designed while it might exist. `docs/backlog.md` says so in those words.

**[[ADR-142 — Autonomous Workflows and the Automation Boundary]] appears to contradict itself here.** It draws the boundary cleanly — the platform owns the *action*, the orchestrator owns the *flow*, and the connector **is** the documented REST API rather than a custom node — and it also states (§2) that *"the platform stays fully usable with no orchestrator at all."* An unsubscribe is a legal obligation rather than a convenience, so it cannot depend on an n8n a self-hosting company never installed. Either the platform needs flow machinery of its own, or one of those two sentences is wrong.

**And several blocked items were piling up behind it**, none of which should be built as a one-off: the unsubscribe surface in several variants, double opt-in, and ADR-163's brand-scoped-by-default opt-out scope, which currently has nowhere to live.

What changed between the question being asked and being answered is that the approval surface got built ([[ADR-142 — Autonomous Workflows and the Automation Boundary]] §4, 2026-09-19). "The system chooses the moment, a human says yes, the platform executes" stopped being a design sketch and became a working mechanism with two differently-shaped consumers. That removed the strongest argument for a canvas, which was that there was nowhere else for a triggered send to land.

## Decision

**1. Unsubscribe and double opt-in are routes, not flows, and need no mechanism at all.**
A flow has steps, waits and branches. An unsubscribe is a signed link, a page, and a consent write. Double opt-in is a signed link, a confirmation page, and a consent write. Neither has a second step that happens later, so there is nothing for an engine to sequence.

This dissolves the apparent contradiction in ADR-142 rather than resolving it: **no flow was ever involved**, so the platform staying usable without an orchestrator costs nothing and the flow-ownership boundary is untouched. The several unsubscribe variants the backlog anticipated are several routes, not several journeys.

**2. A multi-step cycle is a sequence of variants, and there is no canvas.**
A campaign carries an ordered set of steps. Each step is an existing variant with an **offset** from the cycle's anchor, and offsets may be negative — so "seven days before the birthday" and "on the birthday" are two steps of one cycle rather than two campaigns.

Welcome series, birthday pairs and winback sequences are all this shape. None of them forks.

**3. Branching is expressed as per-variant followup conditions — a graph that is authored rather than drawn.**
A variant declares what follows it and under what condition: *if opened, then variant X; if not, then variant Y* — and X and Y declare their own followups in turn. This is an adjacency list, which is the same information a canvas holds and needs no canvas to author, because each edge is written while editing the variant it leaves from.

**A followup is a row, not columns on a variant**, and that follows from two requirements at once: a branch needs more than one followup per variant, and point 6's toggle needs each one individually addressable. Each row carries a condition, a target variant, an offset and an `active` flag.

**Three things that looked like branches are not**, and this is why the sequence is sufficient: a condition like *"skip this step if they have already bought"* is the step's own audience predicate re-resolved at send time, which `audience_resolution_mode = "rerun"` already does; a recipient who unsubscribes mid-cycle is dropped by the exclusion stack rather than by an exit path; and *"remind if no open after X days"* is a followup whose condition is *did not open* and whose offset is X. **The reminder option therefore stops being a separate feature** and becomes this record's first worked example.

**4. Conditions reuse the audience criteria vocabulary.**
A followup or exit condition speaks the same predicates an audience rule block speaks — engagement signals, dates, categories — extended with the engagement predicates (recency, frequency, decay state) already parked in `docs/backlog.md` for exactly this workstream. One vocabulary, one place to extend, and a condition means the same thing wherever it is written.

**5. A cycle is anchored by a date on the recipient, and an external trigger writes that date.**
The anchor is a date the recipient carries — a birthday, a subscription date, a first purchase — and every step is the predicate *anchor + offset is today*. Step three of a welcome series is "subscribed seven days ago".

A campaign says which kind of anchor it uses. Where the platform can evaluate the date itself it does; where only the source system knows it — a first purchase — [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]'s machine plane writes it, and the cycle then runs identically. **One mechanism serves both**, which is what keeps the playbook's own site able to run a welcome series without installing an orchestrator while leaving ADR-142's boundary exactly where it was.

**6. A cycle is approved once, at setup, and corrected by toggling individual followups.**
`docs/playbook-strategy.md` settled the first half on 2026-07-31: *"automated/recurring cycles need that approval once, at setup, with a 'correct your proposal' adjustment path afterward rather than re-approving every cycle."* Asking per step would bury a manager in approvals, which is the outcome [[ADR-140 — AI Capability Layer]]'s Context rejects by name.

The second half is the `active` flag on each followup row. **Correcting a cycle is switching one branch off, not revoking the whole arrangement** — a smaller, reversible act that matches what actually goes wrong, and it gives the "adjustment path" a concrete shape it did not have. Every send a cycle fires still appears in delivery history and the audit log; unattended means unattended-per-send, not unrecorded.

**7. There is no per-recipient cycle state, and that is a deliberate absence.**
Because the anchor is a date on the recipient, "where is this person in the cycle" is computable rather than stored: nothing can drift, nothing needs reconciling, and a recipient re-enters a birthday cycle every year for free. This is the same choice [[ADR-163 — Per-Channel Consent and Addressability]] made when it computed consent from events rather than storing a status.

**8. Adaptive branching is out of scope, and the boundary is stated rather than left open.**
When a cycle becomes *"people who did X get this, everyone else gets Y"* at real complexity, the honest question is whether a human can predict the best split at all. At that point choosing it is a decision-layer or Mode B concern, not an authoring surface — which is [[ADR-142 — Autonomous Workflows and the Automation Boundary]]'s boundary arriving from a new direction and agreeing with itself.

## Consequences

### Positive

- **The largest unknown surface in the manager UI disappears.** A sequence with per-variant followups renders as lists and menus — the frontend can be designed against screens that already exist, and nothing is blocked on a canvas nobody has specified.
- **The reminder feature, the welcome series, the birthday pair and winback are one mechanism**, not four. The backlog item that tracked reminders separately collapses into this record.
- **ADR-142's boundary survives intact and is reinforced.** No flow ownership moves in-house, because points 1 and 2 establish that the cases forcing the question were not flows.
- **Nothing new has to stay consistent.** No cycle-state table, no second predicate language, no parallel approval mechanism — the audience vocabulary, the exclusion stack, `rerun` resolution and the approval surface are all reused as they stand.
- **The correction path is smaller than the commitment.** A manager who mis-specifies one branch switches that branch off; they do not have to tear down and re-approve a cycle that is otherwise working.
- **An external trigger and a platform-evaluated date are the same mechanism**, so a company with a CRM and a company without one run the same cycles.

### Negative

- **A true parallel fork cannot be expressed.** Two different paths running simultaneously with different content and later merging is a graph this model does not hold. Believed not to be needed; recorded so that discovering otherwise is recognised as this record being wrong rather than as a missing feature.
- **A followup graph can contain a loop**, and nothing in the model prevents variant A following B while B follows A. This needs a cycle check at authoring time, and an unguarded version would mail somebody forever.
- **Steps fire unattended once a cycle is approved**, which is the point and is also the risk. A wrong predicate reaches everyone it matches, every day, until somebody notices — and the thing that notices is a person reading delivery history, because no alerting exists.
- **"Anchor plus offset is today" means a missed day is a missed send.** The recurring evaluation has no catch-up: if the process that runs it does not run, those recipients are simply not sent to, and nothing records that they were skipped.
- **A manager who adds a cycle today reaches people mid-way through it** — somebody who subscribed five days ago receives step three and never received steps one and two. Judged correct, because retroactively sending a week-old welcome is worse, but it will read as a bug the first time it is seen.
- **Conditions inherit the audience vocabulary's weaknesses along with its strengths**, including the consent subquery's cost growing with a recipient's history depth, now paid per step rather than per send.

## Notes

- **The recurring evaluation is a route a scheduler calls**, following `process_due_scheduled_sends` and the approvals expiry sweep. The architecture exposes the seam rather than baking in a scheduler, which is the established convention and the reason there is no background thread anywhere in this codebase.
- **This record does not build anything.** The blocked items behind it — the unsubscribe surface, double opt-in, ADR-163's opt-out scope — become buildable as ordinary routes the moment point 1 is accepted, and `List-Unsubscribe` is independently a beta blocker tracked in `docs/backlog.md`.
- **The design conversation rejected a canvas twice, for different reasons.** First because the legal obligations turned out not to be flows, and then — after the initial "one predicate, one send" framing was corrected as too narrow — because multi-step cycles turned out to be a sequence with locally-declared edges. The second correction came with the observation that a canvas is mostly aesthetics: it displays a graph the manager could author one email at a time, and it charges a whole UI surface for the display.
- **Deliberately not decided here:** whether a followup's offset is relative to the anchor or to the preceding step's send. Anchor-relative is simpler and is what point 5 implies; step-relative survives a step being skipped by its own predicate. Worth settling in the final-design pass, with a worked welcome series in front of it.

## Related ADRs

### Depends On
- [[ADR-140 — AI Capability Layer]]
- [[ADR-142 — Autonomous Workflows and the Automation Boundary]]
- [[ADR-160 — Channel Model and Composition]]
- [[ADR-163 — Per-Channel Consent and Addressability]]
- [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]
