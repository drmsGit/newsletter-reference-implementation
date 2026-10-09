---
type: interview-prep
topic:
  - architecture
  - data
  - crm
  - personalisation
created: 2026-10-09
modified: 2026-10-09
status: planned
---

> **Status: PLANNED, not started (2026-10-09).** The plan was agreed with the user on
> 2026-10-09 and is written down here so it can run without being re-derived.
> **Run this when task-294 is picked up:** read this file, re-verify the pre-read facts
> below (they are dated 2026-10-09), then start Cluster A, question 1, one question at a
> time, each with a suggestion, then stop and let the user decide (project working rule).
> Nothing below is decided. The "Suggestion" lines are starting positions, not answers.

# Related Data Access — design interview (forward-looking)

Like [[Manager Workflow - design interview]] and [[Audience Write Surface - final design pass]],
this file gathers the **decisions needed before writing ADRs**. It belongs to task-294
(*Related data: synced and stored, or pulled when needed, and usable in audience rules?*).
Read task-119 and task-120 in the same session; both overlap (see *Timeline and couplings*).

## Why this came up

task-294 was split off the task-293 audience-editor interview on 2026-10-06. The user's
case for client Condor: "anyone who is interested in beach content and departure airport
FRA or BER", where *preferred departure airport* is a CRM attribute. The user's own
phrasing of the question: "Is it synched into the platform and stored? or are those only
pulled into the platform when needed."

On 2026-10-09 the user sharpened it into a hypothesis, recorded here to be tested, not
decided:

> The platform is Python and React. It does not have a heavy structure that prepares
> newsletters upfront and needs personalisation data inside the platform, because it is
> possible to request data on call when a newsletter or push message is assembled. We
> assume we build scripts for a lot of things. So why not build a script: "that's the
> communication asset with {{}} variables; when generating the HTML, pull data from
> external system Y", instead of "look into a table in this platform"?

Two uses were named:
1. **Content:** pull order information or customer-service data into an email.
2. **Selection:** check an audience against a CRM filter, so not every CRM attribute is
   stored in the platform but pulled when needed.

## Established up front (not reopened)

- The CRM is the customer source of truth; the platform may keep a minimal projection, and
  its mechanism is out of scope of the decision:
  [[ADR-120 — CRM as Customer Source of Truth]],
  [[ADR-126 — Maintain Local Recipient Projection]],
  [[ADR-121 — Minimal Recipient Model]].
- Consent and addressability are local and fail closed; a refusal wins; audience and consent
  are re-checked at send time:
  [[ADR-163 — Per-Channel Consent and Addressability]],
  [[ADR-176 — A Negative Decision Outranks a Positive One]] point 4.
- Signals are the platform's own derived data, kept local:
  [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]].
- The renderer formats and never decides; it receives resolved content:
  [[ADR-162 — Channel Rendering and Artifacts]] point 2.
- Merge Context is **named and not built**:
  [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]] (it "must remain
  available after delivery"),
  [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]]
  point 7 ("when it does, the delivery record must gain the merge context").
- No maintained connector library; one worked example per seam; the connector is the REST
  API (`docs/business/BRIEF.md`).
- A DWH is never required: [[ADR-124 — DWH Is Recommended but Not Mandatory]],
  [[ADR-125 — Define a Minimal Reference Architecture]].
- n8n is optional and the platform works without it:
  [[ADR-142 — Autonomous Workflows and the Automation Boundary]] point 2. Nothing identifying
  goes to anything outside the platform (point 5);
  [[ADR-144 — AI Data and Model Governance]] point 4 (personalisation by merge variables,
  filled locally).
- Audience rules are flat; related data was deliberately left out of them until this task:
  [[ADR-188 — Audience Rules Are Flat, and May Read Engagement History]].
- Long-lived reusable audiences belong in the CRM; temporary ones in the platform:
  [[ADR-123 — Audience Ownership Depends on Reuse]],
  [[ADR-052 — Delivery Layer Supports Multiple Audience Resolution Modes]] (references,
  queries, explicit lists).

## Timeline and couplings

- **Queue position:** task-294 has ordinal 300350. Ahead of it in the Needs-ADR range: the
  lifecycle block (task-117, 136, 135, 246, 314, 324) and task-119. task-120 follows it.
  No launch gate depends on it (`docs/business/LAUNCH-GATES.md`; `BETA-SCOPE.md` requires
  none of the Needs-ADR items); it is post-beta unless the Condor pilot needs it.
- **Can run in parallel with other work:** yes. The interview is docs-only. The couplings:
  1. **task-136 (data lifecycle).** Its ADR cannot be final without knowing whether delivery
     records copy merge values. Carve "retention of the values used in a send" out of 136
     into Cluster C here, or run Cluster C first.
  2. **task-119 (what n8n and the CRM must do).** The CRM is not chosen. Every use case on it
     today is inbound; a pull adds an outbound one. Read it in the same session and update
     its finite use-case list afterwards.
  3. **The content-selection design session** (a separate Claude session, running on
     2026-10-09). Decision strategies reading recipient or product data
     ([[ADR-127 — Decision Execution May Use Recipient Context]]) is the overlap. Cluster E
     carries a boundary line.
- **Recommended order:** the lifecycle interviews as planned, with the carve-out above; this
  interview in two passes (Pass 1 = Clusters A to C, Pass 2 = D and E); task-119 right after
  Pass 2.
- **Other tasks that consume the answer:** task-134(c) (transactional merge variables from
  arbitrary JSON), task-60 (personalised subject line), task-125 (subject generation),
  task-84 and task-85 (conversions in, DWH export out; boundary only), task-128 (minimum
  sync outward, other direction), task-79 (dev-data pseudonymisation), task-308 (shared
  discovery helper, only if a data source becomes a drop-a-file registry).
- **Gap:** no task owns the content-side merge context. It is a "not done (Needs-ADR)" row in
  `docs/playbook-strategy.md` (drift table) and left open by ADR-183 point 7. At the close,
  decide with the user whether to widen task-294 or file a sibling decision task.

## First feedback on the hypothesis (for the user to react to, not a decision)

**Agree, and the repo already leans that way.**
- Order and customer-service data cannot be stored today, by design:
  `validate_recipient_attributes` (`backend/app/recipients/service.py:91-122`) rejects keys
  such as `invoice`, `payment`, `billing`, `ticket`, `service_case`, `phone`, `address` with
  "Keep this data in the CRM."
- `RecipientDB.attributes` is display-only: audience rules, decision, rendering and delivery
  never read it, so the projection is not load-bearing yet.
- The slot for the idea exists and is empty (ADR-005, ADR-162 point 2, ADR-183 point 7). The
  AI layer already promises `{{first_name}}` filled locally at render; nothing implements it.
- It fits the product stance: no maintained connectors, one worked example per seam, and
  task-120's "if the chapter cannot be written against the real seams, the seams are the
  finding."

**Refine: three access patterns, not two.**
- **Store:** a projection synced in (today's model).
- **Carry:** the data travels with the trigger (n8n sends the order JSON with the send
  request); the platform neither stores nor pulls. Natural for event-driven mail and for
  task-134(c).
- **Pull:** the platform calls the source at render or resolution time (the hypothesis).

**Refine: content time and selection time are different problems.**
- *Content time* (a person's own order in their email): per recipient, bounded by the send
  cap, fits the send loop.
- *Selection time* (a CRM filter in an audience rule): resolution is recomputed on every
  count, preview, arithmetic recalculation and per-person page
  (`backend/app/audience/service.py:987, 1030, 1264, 1177-1233`) and again at send. A live
  CRM call per attribute per evaluation does not survive that. What does: the CRM answers
  "who is in segment X" once, as a set of `external_id`s, cached "as of" a time and
  intersected with the platform's own rule results (rules are already set algebra over
  recipient ids, `_resolve`, `audience/service.py:1236-1295`). That is ADR-052's unbuilt
  "references" mode. The Condor case is half platform data (category interest from signals)
  and half CRM data (airport), so a pure CRM filter cannot evaluate it alone.

**Push back: a pull moves storage, it does not remove it.** Merge context must remain
available after delivery; `reconstruct_delivery` (`backend/app/delivery/service.py:1353-1423`)
re-renders and compares a hash, which fails if a value was fetched and not recorded. "Not
stored forever" holds for the standing projection; a per-delivery copy of the values used (or
a hash plus source plus `fetched_at`, giving up "what exactly did X see") is still needed, and
it is personal data under [[ADR-154 — Erasure and Retention]], whose erasure is unbuilt.

**Push back: the send loop is not built for a fetch inside it.** Sends are synchronous,
sequential and in one request, with no worker (`delivery/service.py:1114`). An exception in
render fails the whole send (`997-1011`); one second per fetch at the 1000-recipient cap is
about 17 minutes in one request, against a 30-minute stranded threshold. A fetch before the
`sending` marker is safe to retry, so the duplicate-send doctrine (task-318, task-327)
survives. A policy is needed: bulk pre-fetch, then per-recipient skip with a recorded reason
(the `excluded` / `STAGE_RENDER` mechanism exists), fallback text, or abort.

**Push back: some data must never be pulled.** Consent, status, language, unsubscribe state
and signals stay local and authoritative. A pull must be opt-in per field so that a CRM outage
never stops a newsletter that does not use CRM data.

**Smaller risks to put to the user:**
- *What does the manager approve?* The snapshot freezes the approved composition (ADR-183).
  A placeholder resolved at send means the approved text is a template, not the final text
  per person.
- *Template safety.* `{{x}}` typed into content copy is not interpreted today (Jinja
  `from_string` runs only on module layout templates, `backend/app/rendering/service.py:364`).
  A new substitution over manager-authored copy must be a restricted placeholder syntax,
  never template evaluation.
- *A new kind of principal.* Today every machine path is inbound
  ([[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]) and credentials are
  environment-only and deployment-wide ([[ADR-152 — Secret and Credential Handling]]).

**Strain on an accepted ADR.** ADR-126's Rationale argues against direct CRM access for every
communication decision; its Decision wording ("imported, synchronized, projected, cached",
mechanism out of scope) allows more. Likely an **addendum**, not a supersession (supersession
is rare here and is said out loud before it is proposed).

**Working rule to test, not a decision:** the platform keeps what it needs to *decide* and to
be *accountable*; the source keeps the rest. Store: identity, consent, language, signals, and
the few slow-changing attributes a manager filters on (airport). Carry or pull: anything used
only inside one person's message, and anything volatile, large or sensitive.

## Pre-read facts (verified 2026-10-09; re-verify before the session)

- Recipient model and writers: `backend/app/recipients/db_models.py:6-30` (`attributes` at
  line 17, `external_id` unique); the only writer is `create_recipient`
  (`recipients/service.py:203-276`), reached by `POST /recipients/` (inbound, caller-initiated).
  The platform never calls a CRM today.
- Audience: `CRITERIA_FIELDS` at `audience/service.py:116`; the comment at 113 says related
  data waits for task-294. Rule results are sets of recipient ids; the category filter runs in
  Python over decay-on-read signals; `only_ids` (line 703) is an existing "check one person"
  hook. ADR-052 "references" mode is not implemented.
- Rendering: the frame is built once per snapshot (`rendering/frame.py:77-145`); layout is
  re-run per recipient in the send loop (`delivery/service.py:1219`); there is no per-recipient
  substitution except the decision-slot pick and the unsubscribe footer. Subject and preheader
  are one value per variant.
- Delivery: one `provider.send` per recipient, commit after each; timeouts are "maybe sent" and
  never resent; every send carries an idempotency key; a retry reaches only people still in the
  audience. The delivery record holds `sent_at`, slot picks with copied values, an artifact hash
  (`delivery/service.py:1301-1308`).
- Extension patterns: the drop-a-file registries (task-308 records that they are copies of one
  shape); provider adapters use an explicit factory (`delivery/providers/factory.py`,
  `ai/adapters/factory.py`), the AI one deliberately explicit because which models a deployment
  may call is a governed choice. The nearest analogue to a data-source connector is
  `DeliveryProvider` (`delivery/providers/base.py:45-68`): never raises, returns a result.
- Outbound HTTP exists only for the Resend and Anthropic adapters (15 s and 60 s timeouts,
  credentials from the environment). No outbound principal, no per-source or per-brand
  credential model, no retry or circuit breaker.
- Not found decided anywhere (to cover in this interview): failure and offline behaviour of a
  pull; reproducibility of pulled values; whether pulled data may feed audience rules; erasure
  of pulled values; sensitive attributes; declared versus discovered rule fields; who owns
  connector code; preview behaviour.
- Previously asked, do not re-ask: identifiers-only was confirmed 2026-07-05 (baseline G1);
  what stays open there is how simple personalisation (salutation) gets its data: "a narrow,
  purpose-limited projection field, a just-in-time CRM lookup at send time, or something else".

## Sketch (not decided, input to the interview)

Three access patterns (store, carry, pull) and a rubric that assigns each kind of data to one
of them; the content side through a declared merge context with the used values recorded in
the delivery record; the selection side through stored declared attributes plus a
CRM-evaluated reference mode; a `DataSource` seam with a mock and one worked example, taught
in a playbook chapter (task-120) rather than shipped as maintained connectors.

---

## Cluster A — The principle: what the platform keeps and what it borrows

1. Do we recognise three access patterns, store / carry / pull?
   *Suggestion:* yes; "carry" is new and fits event-driven mail.
2. Which properties decide the pattern for a piece of data: used to select versus to fill
   content; volatility; volume; sensitivity; must it be reconstructable? The output is a short
   rubric the playbook can teach.
3. Default posture: a stored projection with pull and carry as extensions, or content data
   pulled by default? And is ADR-126's rationale an addendum or a supersession?
   *Suggestion:* addendum.
4. The fixed line: consent, status, language, unsubscribe state and signals stay local.
   *Suggestion:* confirm.
5. Who decides which related fields exist: declared in a file (label, kind, source), as
   proposed and parked in the task-293 interview, or discovered?
   *Suggestion:* declared.

## Cluster B — Content time: the merge context

1. What is a variable: its syntax, where it may appear (module fields, subject and preheader,
   task-60), and that substitution is restricted, not template evaluation.
   *Suggestion:* declared per module manifest, in the style of [[ADR-177 — A Field Is Defined Once, Required Per Module]].
2. What may a variable carry: a scalar or a list (order lines); who formats it; length limit;
   escaping; is a fallback mandatory?
   *Suggestion:* scalar first, fallback mandatory.
3. Where does the value come from: the projection (firstname, today's `attributes`), a pull,
   or the trigger payload (carry, task-134(c))?
   *Suggestion:* all three behind one interface.
4. What the manager approves: placeholders in the frame, preview with sample data, test send.
5. Is the subject line the same mechanism? (task-60; ADR-040 / ADR-041 territory, see
   [[ADR-040 — Introduce Override Layer]] and [[ADR-041 — Override Precedence]].)

## Cluster C — Proof and privacy: what must be recorded about what was used

1. What the delivery record holds for merge values: the values, or hash plus source plus
   `fetched_at`, or nothing. ADR-005 says it must remain available.
   *Suggestion:* the values, per send, minimal.
2. Retention and erasure of those values ([[ADR-154 — Erasure and Retention]]); hand-off to
   task-136. *Suggestion:* the same lifecycle as the delivery record.
3. Reconstruction shows the recorded values and never re-pulls. *Suggestion:* yes.
4. Pulled data never enters an AI path, and only `external_id` leaves the platform
   (ADR-142 point 5, ADR-144 point 4). *Suggestion:* confirm.
5. Sensitive attributes (health, credit): no local copy at all? (a bullet of task-294.)
   *Suggestion:* pull or carry only.

## Cluster D — Selection time: related data in audience rules

1. May a rule read related data, and in which form: a stored declared attribute (airport) or a
   CRM-evaluated reference (ADR-052 references mode)?
   *Suggestion:* both, chosen per field, declared.
2. Reference mode: the CRM returns a set of `external_id`s, intersected with the platform's
   own results, cached per send plan. *Suggestion:* yes.
3. Counts and previews: the manager sees "as of <time>" with a manual refresh; no live call
   per recalculation. *Suggestion:* yes.
4. Send time: the audience is re-resolved (ADR-176 point 4); what happens when the CRM is
   unreachable. *Suggestion:* fail closed: exclude and say so; never send to an unverified set.
5. Who may build rules on related data; per brand; visibility; the declaration file (label,
   kind: one of / number / yes-no).
6. Conversions from outside as rule input: the boundary with task-84.

## Cluster E — Seams and operations: relational data (task-120) and the mechanics of a pull

*Boundary: a product catalogue feeding decision slots belongs to the content-selection design
session; here only the data-source seam is decided.*

1. Ship a seam plus one worked example, or only a playbook chapter? And how does this square
   with task-120's 2026-09-18 framing of stored extension tables?
   *Suggestion:* a seam, one worked example and the chapter.
2. The connector contract: a `DataSource` interface modelled on `DeliveryProvider` (never
   raises, returns a result), a mock for development and tests, registered by explicit
   factory (a governed choice, like the AI adapters) or by drop-a-file (task-308).
   *Suggestion:* explicit factory.
3. Credentials: an outbound principal and per-source secrets; an addendum to ADR-166 and
   ADR-152. *Suggestion:* yes, if a pull survives Cluster A.
4. The send-loop policy: bulk pre-fetch before the loop, a per-recipient timeout, and on
   failure skip with a recorded reason, fall back, or abort; a per-send choice in the style of
   `skip_without_resolution`; the interplay with the stranded rule and the duplicate-send
   doctrine.
5. Caching time-to-live, rate limits, an audit entry per fetch
   ([[ADR-153 — Audit and Accountability]]), and dev safety (task-79).
6. The seam test: can the chapter be written against the real seams? What breaks?

## Close — what gets recorded

- ADRs through the `adr-author` agent, numbers taken from `ls docs/architecture/ADR/` at that
  moment. Expected: a new ADR for the merge context and the data-access patterns (fills
  ADR-183 point 7); an addendum to ADR-126; addenda to ADR-052 and ADR-188 if decided;
  addenda to ADR-166 and ADR-152 only if an outbound principal is chosen.
- Tasks through the `backlog` CLI: close task-294 when its two criteria are met; reshape
  task-120 into the chapter task; update task-119's use-case list; link task-134(c) and
  task-60; file build tasks (merge context and delivery-record values, the `DataSource` seam
  with a mock, the send-loop fetch policy, reference-mode audiences). Ordinals step by 100.
- A decision-log entry in `docs/playbook-strategy.md`, and the merge-context row of its drift
  table updated.
- A final-design pass before any build task starts ("an accepted ADR is not an implementation
  plan").
- **Done when** task-294's two acceptance criteria are met and the "not found decided
  anywhere" items above are covered, with no recorded decision contradicting ADR-163 or
  ADR-176 (fail closed), ADR-154 (erasure), ADR-142 point 5 (nothing identifying leaves) or the
  no-maintained-connectors stance.

## Related

- [[Manager Workflow - design interview]] (Cluster 4: choosing who receives it)
- [[Audience Write Surface - final design pass]] (the case that raised the question)
- [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]
- [[ADR-126 — Maintain Local Recipient Projection]]
- [[ADR-183 — A Snapshot Freezes the Composition and Every Delivery Records What It Got]]
- [[ADR-188 — Audience Rules Are Flat, and May Read Engagement History]]
