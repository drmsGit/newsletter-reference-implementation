---
type: adr
status: accepted
topic:
  - architecture
  - ai
  - automation
  - governance
created: 2026-07-31
modified: 2026-09-29
source:
  - "AI Layer design interview (interview-prep, 2026-07-27 – 31), Cluster 3"
depends_on:
  - "[[ADR-140 — AI Capability Layer]]"
  - "[[ADR-141 — In-App Assistive AI Actions]]"
  - "[[ADR-144 — AI Data and Model Governance]]"
  - "[[ADR-002 — API First Architecture]]"
  - "[[ADR-091 — Automation Layer Is Orchestration, Not a Workflow Engine]]"
  - "[[ADR-092 — Automation Layer Receives Triggers, It Does Not Own Trigger Sources]]"
  - "[[ADR-094 — Campaign Execution May Be Started by Scheduler or Automation]]"
  - "[[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]"
---

## Status
Accepted

## Context

ADR-140 established the AI capability layer, ADR-141 its first mode (in-app
assistive actions), ADR-144 the cross-cutting governance. **Mode B** is the second
mode: **autonomous workflows** — work that runs without a marketer clicking
anything, typically orchestrated in n8n or a comparable tool.

ADR-091/092/094 already place the boundary in principle (the automation layer is
*orchestration*, not a workflow engine; it receives triggers rather than owning
trigger sources). What was undecided is everything operational: how an autonomous
flow gets sign-off, what data may leave the platform, how much we actually *ship*,
and how the boundary survives contact with a real organisation.

That last point turned out to drive the rest. **Automation is usually not
marketing's department.** Two mirror-image expectations meet at this boundary: the
automation/IT team owns the flows and "just wants the system to send the right
email", while marketing owns the platform and "just wants the platform to do the
flow". Flows always require genuine expertise on the orchestrator side, and there
is **no way to "prompt" a flow into existence** from this architecture — that is
platform-specific work, permanently out of scope here.

## Decision

**1. The platform owns *actions*; the orchestrator owns *flow logic*.**
The platform exposes **triggerable-action APIs** (build a group, create a campaign,
send, precompute content, read stats) plus an **approval surface**. n8n — or Make,
Zapier, Logic Apps, or a plain cron script — decides *when* and *in what order*.
This confirms ADR-091/092 rather than extending them.

**2. Whatever lets the platform work independently wins.**
Where a capability could sit on either side of the boundary, it goes in the
**platform**. Rationale is organisational, not technical: if the platform depends
on flow logic to function, marketing is blocked on another department for routine
work. Two consequences follow: **every action an orchestrator can trigger must also
be triggerable in-app**, and **the platform stays fully usable with no orchestrator
at all**. The orchestrator adds reach and timing, never capability.

**3. No custom orchestrator node — the connector *is* the documented REST API.**
Publishing an n8n community node would be a maintained vendor integration, exactly
what the provider layer refuses to become (ADR-100/105). n8n's generic HTTP node
calls the API like any other client (ADR-002).

**4. Approval: the platform holds the pending action; approving executes it.**
An autonomous flow calls an action, receives "pending approval", and **finishes** —
it does *not* park a long-running execution waiting for a human. The platform
stores the pending action and runs it on approval. This is not a new mechanism: it
is exactly ADR-141's draft→publish step, using **the same approval inbox**, the
same audit trail, and it survives orchestrator restarts.

- **Email/push is notification only** — a link *into* the inbox, never one-click
  approve/reject. A one-click approve link is a bearer credential sitting in a
  mailbox, and ADR-132 already establishes that **security scanners and MPP
  prefetch links in email**: a scanner could approve a full-audience send with no
  human involved. It is also forwardable and logged by mail gateways.
- **Pending actions expire.** A held "send the morning campaign" is worthless three
  days later.
- **An action history is required** — approved, rejected *and* expired requests stay
  inspectable. It **extends the ADR-140 audit surface**; it is not a second log.

**5. Minimal-data contract: IDs + non-personal metadata, never identifying data.**
ADR-144 drew the PII line at "no raw PII **to the model**". Mode B generalises it:
**no identifying data to anything outside the platform** — a model and an
orchestrator are two cases of one rule, and (per Context) the orchestrator may
literally belong to another department. Non-personal metadata is explicitly
*wanted* — campaign/group labels, counts, statuses — so a notification reads
"Campaign *Autumn Hiking* — 1,240 recipients in *Hiking enthusiasts*" instead of a
pair of UUIDs. The test is simply: **does it help identify the recipient?**
Personalisation stays with merge variables resolved locally at render (ADR-005).
The ADR-144 opt-up applies unchanged — per-action, deliberate, logged — and **each
triggerable action declares its own minimum payload**, mirroring ADR-141's task
contract, so there is no global payload spec to maintain.

**6. Ship one worked example, not a workflow library — two artifacts, two value
stories.**
A starter library of four or five flows would become a maintained integration
surface *and* silently bless one orchestrator. Instead:
- **Deliverability-anomaly alert** (the quick win): read-only — schedule → read
  stats → notify. No approval, no send, so importing it cannot break anything, and
  it proves the platform→orchestrator direction in minutes. Its value story is
  *"this improves daily business too"*, and it addresses a real gap: **with current
  platforms you often never learn a deliverability problem exists** unless you build
  your own monitoring.
- **Automated audience suggestion → approval inbox** (the complex one): the
  autonomous counterpart of the in-app system-suggested audience. Its value story is
  the marketer's, and it exercises the entire loop from point 4.
- **Everything else** — fatigue handling, precomputing "next content", the morning
  campaign — is **documented as a vendor-neutral sequence of API calls**, with no
  shipped JSON. Prose costs nothing to keep current; the maintained artifact count
  stays at two.

**7. Temporary exclusion: Mode B needs only the interface.**
Flows and external systems must be able to **read, write and explicitly override** a
recipient-level suppression gate ("don't email this person until D, because R").
Overriding is the existing **pin** mechanism (`resolve_audience`'s `… ∪ pins`), now
callable from outside — e.g. a website form firing *"this recipient must get the
masterclass mail"*. Precedence is three-tier: **consent** is a hard floor and never
overridable; **suppression** is soft and overridable by an explicit, logged act;
include/exclude rule-blocks are ordinary audience logic. **The data model — the
concrete field/table shape and an opt-out reason taxonomy — is deliberately *not*
decided here**; it is a data-model concern, tracked in `docs/backlog.md`.

**8. Testing belongs at the strategy level, not the email level.**
A per-send "AI writes a challenger, send it to 5%" feature was evaluated and
**rejected**: you cannot A/B a *rendering* when personalisation produces N
renderings per send, so "how much system-generated content before the test stops
making sense?" has no answer by construction. Testing therefore moves up a level —
**challenge the strategy** (which categories, what cadence, which audience, how much
exploration), which is the *same* workflow as point 6's audience suggestion with a
**different goal and prompt**. That re-aiming is itself a demonstration of ADR-140's
frontend-editable prompts: same dev scaffold, manager changes the prompt, different
product capability. Ordinary human-driven A/B testing remains a normal product
feature (tracked separately); a significance gate is optional when the output is
accumulated learning and mandatory only if rollout is ever automated.

**9. Fatigue is deterministic — a threshold, not a prediction.**
Don't use AI where a rule suffices, and here the rule is also *more explainable*,
which points 4 and 7 now require. Fatigue is a **downward trend in engagement
*rate*, relative to the recipient's own baseline** — not an absolute "below X%",
which would punish someone whose normal is engaging with every tenth email. Three
implementation constraints:
- It needs a **denominator**: contributions record engagements, not sends, so the
  rate is engagements (`SignalContributionDB`) ÷ sends (`DeliveryExecutionDB`).
  Without it, a quiet sending month flags the entire list as fatigued.
- It must use **undecayed contribution counts bucketed by window** — never the
  decayed signal score, or ADR-132's decay would itself manufacture a downward
  trend for every recipient.
- It **depends on the retention window**: ADR-132 bounds local contributions, and
  the configured trend window must fit inside whatever retention policy is chosen.
  The two decisions belong together.

Thresholds, trend window, and exclusion duration are **manager-adjustable settings**;
the result writes to the point-7 suppression gate.

**10. "AI tunes the system's own parameters" is named, documented, and not built.**
Over time AI can propose *configuration* changes — "try a 20% drop threshold instead
of 30%" — landing in the approval inbox and writing to **settings**. This is a third
kind of AI action, distinct from generating content and from proposing an audience,
and it does not fit ADR-141's task contract cleanly: the landing place is settings,
not a record. **It is documented as direction only.** A general capability claim
("the system can analyse your data and suggest improvements") needs no proof
implementation, and committing an ADR to a detailed mechanism before package 1.0
runs and a beta has happened risks locking in something a real deployment
invalidates. Revisit after 1.0.

## Consequences

### Positive
- The boundary survives a real org chart: two departments can own their side without
  blocking each other, and the platform never stops working if the orchestrator is
  absent, broken, or owned by someone else.
- No long-running orchestrator state — approvals survive restarts, because the
  platform holds them.
- One approval surface for Mode A and Mode B, one audit trail, one action history.
- Identifying data never leaves the platform by default, whether the recipient of
  that data is a model or an automation tool.
- Two maintained artifacts instead of a workflow library; orchestrator-neutrality
  stays real rather than nominal.
- Fatigue is explainable to a manager and to a recipient, and doubles as the
  baseline any future prediction must beat.

### Negative
- "Everything must also be triggerable in-app" constrains the action API: no
  orchestrator-only shortcuts, even when one would be convenient.
- Approval-by-email-link is off the table, which is the one UX most people expect;
  the mitigation (deep link into the inbox) is one extra click.
- Only two shipped workflows means adopters wire their own beyond the worked
  examples — documented sequences, not turnkey imports.
- Deferring the suppression data model leaves an interface decided against a shape
  that doesn't exist yet; the data-model ADR must not contradict point 7.
- A deterministic fatigue rule needs per-company tuning and real data to calibrate.

## Notes

- **Deliberately out of scope**, tracked in `docs/backlog.md`: the suppression /
  opt-out data model and reason taxonomy; the A/B component and random audience
  split; multivariate testing; automated winner rollout.
- **Deliberately not built** (point 10): AI-driven settings tuning — documented as
  direction, revisited after 1.0 and a beta phase.
- **Rejected during design:** the per-email 5% champion/challenger (point 8), a
  custom n8n node (point 3), a starter library of workflows (point 6), one-click
  approve links in email (point 4), and modeling suppression as a consent value or
  an audience rule-block (point 7).
- **Status.** Decided in the design interview; implementation is phased with the
  Mode-A build. Accepted as a design decision, not as shipped code.

## Addendum 2026-09-24 — a held action may carry no deadline

Prompted by the Manager Workflow design interview (Cluster 1), which asked what the
approval inbox actually holds and found an action type §4 cannot express.

**§4 stands as written for the case it was written about.** *"Pending actions expire. A
held 'send the morning campaign' is worthless three days later"* is correct, and it is
correct for exactly the reason it gives: the value of that action decays because the
moment it was chosen for passes. **Content review does not decay that way.** A variant
waiting to be read is worth the same on Thursday as it was on Monday, and expiring it
does not protect anybody — it silently drops a request a person was going to answer.

**The TTL therefore belongs to the action type, and must be allowed to be absent.**
Some actions expire because their moment passes; some do not, and the registry is the
place that knows which. What §4 should be read as saying is that *an action that expires
declares its own deadline*, not that every action has one.

**Today this is not expressible, in two places at once.**
`PendingActionDB.expires_at` is `nullable=False` (`backend/app/approvals/db_models.py:94`)
under a comment that makes the reasoning explicit — *"No default and no nullability — the
registry always supplies one, so a module that forgets cannot create an immortal held
send"* — and `default_ttl_seconds: int` on the action contract
(`backend/app/approvals/actions/base.py:58`) is not optional. The column's comment is
defending against a forgetful module, which is a real risk; it happens to also forbid a
deliberate absence, which is the case that now exists.

**The cost is stated rather than left to the build, because it is larger than one
nullable column.** Making `expires_at` nullable means **every comparison must read null
as *never expires* rather than *expired*** — the expiry sweep, any inbox filter, any
"is this still actionable" check — and a null that sorts or compares the wrong way in one
of them produces the exact failure the NOT NULL was protecting against, from the other
direction. It also needs a **hand-written migration**: there is no Alembic in this
repository, tables come from `create_all` plus `backend/scripts/migrate_*.sql`, so this
is a script somebody writes and runs rather than a generated step.

Not built; logged in `docs/backlog.md`. Nothing in §4's other bullets changes — the
inbox, the audit surface and the notification-only rule for email and push are untouched.

## Addendum 2026-09-24 — the soft-suppression override moves up a level

Prompted by [[ADR-176 — A Negative Decision Outranks a Positive One]], which removes the
mechanism §7 names, and resolved the same day rather than left as a conflict.

**What §7 relied on.** It makes recipient-level suppression *"soft and overridable by an
explicit, logged act"*, and identifies that act as the **pin** — `resolve_audience`'s
`… ∪ pins`, now callable from outside — with a website form firing *"this recipient must
get the masterclass mail"* as its worked example. ADR-176 point 1 ends pin precedence: an
exclusion segment now removes a hand-pinned recipient.

**The override survives, at a different level, and the new level is better.** A manager
who genuinely wants a suppressed recipient in a send does not pin past the exclusion —
they **remove the exclusion segment from their audience group**. That is a deliberate act
on a named list, visible to anyone who opens the group, rather than a quiet per-recipient
exception nobody reviewing the audience would notice. §7's requirement that the override
be *explicit and logged* is better served by it, not worse.

**The distinction §7 needed and did not have, settled 2026-09-24:**

- A **blocklist** is a legal and data-protection matter — GDPR, privacy law, a hard
  suppression. It is not overridable by anybody, and it is not what §7 was describing.
- A **system suggestion** — *"this recipient should not get newsletters at the moment"*,
  news fatigue, over-mailing — is an **exclusion segment**. It wins over a manager's
  *must get*, and it is removable from a group by a manager who decides otherwise.

So §7's *"soft"* now means *removable from the group*, and its *"hard"* is the
consent/suppression floor. Both beat a positive decision, which is
[[ADR-176 — A Negative Decision Outranks a Positive One]]'s principle applied here.

**It is better that the system writes its suggestion as an audience group or segment
rather than as a per-recipient flag**, precisely because a list can be inspected,
reasoned about and removed as a unit. That is the shape §2's *"the platform stays fully
usable with no orchestrator at all"* wants too: a suggestion expressed as data a person
can see and undo, not as behaviour they can only discover.

**Two capabilities this needs that do not exist**, logged rather than solved here. An
orchestrator writing a temporary exclusion must be able to **remove** audience members it
added, and/or a membership must be able to **expire**: `AudienceGroupMemberDB` carries
`group_id`, `recipient_id` and `added_at` and nothing else — no deletion date, no TTL, no
record of who added it or why. A *temporary* exclusion with no expiry is a permanent one
that somebody has to remember to undo. Logged in `docs/backlog.md`; a different topic
from this addendum's subject.

**Nothing in §7's other reasoning changes.** Suppression stays a platform concern rather
than an orchestrator's, the exclusion stack still records why each recipient was
excluded, and the automation boundary is untouched.

## Addendum 2026-09-29 — a held action is claimed by state, not by lock

Prompted by the 2026-09-19 code review's P1-01 (task-4) and by the expiry sweep's
lost update (task-13), whose shared fix the user approved on 2026-09-29. §4's
*"approving executes it"* stands; what changes is how the platform makes sure it
executes **once**.

**The lock §4's implementation relied on did not hold across the run.**
`_claim` in `backend/app/approvals/service.py` takes `with_for_update()` on the
`pending_actions` row, and `approve` meant to keep that lock while `module.execute`
ran. But the action runs on the same session, and `send_send_instance` commits inside
it — it moves the send to `sending` and commits. That commit ends the transaction
holding the lock while the row still reads `pending`, because `approve` writes the
status only after execute returns. Two approvers could therefore both claim and both
execute; only `send_send_instance`'s own status guard stopped the second. That is
exactly the masking `_claim`'s docstring names as the reason its lock exists: the
first action whose execution is not idempotent would have run twice, silently.

**The expiry sweep had the mirror-image fault.** `expire_due_pending_actions` and
`_mark_expired` take no lock and re-check no status. A sweep can read a pending row,
an approver can decide it, and the sweep then commits `status='expired'` over that
decision from its stale ORM object — an approved, executed, mailed request recorded
as lapsed. Two overlapping sweeps both emit `approval.expired`.

**1. A request is claimed by state, not by lock.** Approving is a conditional
`UPDATE … SET status='executing' … WHERE id=? AND status='pending'`, committed
**before** the action runs. Zero rows updated means another decider won, and this
caller stops. The action may then commit whatever it likes; the claim is already
durable. Only the caller whose claim succeeded finalises the row:
`executing → approved`, or `executing → failed`.

**2. Reject and expiry use the same conditional transition from `pending`.** Neither
can overwrite a decision or a running execution, because neither matches a row that
has left `pending`. That closes task-13's lost update and the doubled
`approval.expired` together.

**3. `executing` is a new lifecycle state, and it means *a person approved; the
outcome is not yet known*.** It joins pending, approved, rejected, expired and failed
in `backend/app/approvals/db_models.py`. Writing `approved` at claim time instead
would be simpler and wrong: the model's docstring makes `status` *"a cache of the
latest audit entry"*, and the GRANTED audit event is written only after execute
returns. A row reading `approved` while its action was still running — or after a
crash — would assert an outcome that had not happened.

**4. The decision is recorded at claim time.** `decided_at` and `decided_by_*` are set
when the claim is taken, because that is when the person decided. The meaning of
`ck_pending_actions_decided` — `(status = 'pending') = (decided_at IS NULL)` — is
therefore unchanged: only `pending` is undecided.

**5. An executing request is still open.** The one-open-request-per-subject partial
index, `ux_pending_actions_one_open_per_subject` on (action_key, subject_type,
subject_id), covers `pending` **and** `executing`, so no new held request can be
created for a thing whose approved action is running.

**6. A crash during execution leaves the row `executing`, deliberately, and nothing
retries it.** Nobody can know whether the action ran, and re-approving would be
exactly the double execution this addendum closes. It is the same shape as a send
left in `sending`. The row is shown under its own status; resolving it is a person's
investigation, not a button. The inbox counts `pending`, so it no longer shows it.

**Implemented by `migrate_0022`**: `ck_pending_actions_status` gains `'executing'`
and the partial index's predicate widens from `status = 'pending'` to both open
states (the index was created in migration 0017 and is also declared on the model).
It is the first migration applied through the runner of
[[ADR-181 — A Database Records Which Migrations It Has Had]].

**What it costs.**

- **A stuck `executing` row has no automated way out.** It needs a person and, today,
  SQL. That is the honest price of refusing to guess whether an action ran.
- **Two commits per approval instead of one** — claim, then finalise. A crash between
  them is precisely the stuck case above.
- **Every consumer that enumerated the five statuses must learn a sixth** — filters,
  templates and the React client alike.

Nothing else in §4 changes: the held action still lives in the platform, the inbox and
audit trail are still the ones shared with ADR-141, email and push are still
notification only, and expiry still applies to whatever action declares a deadline.

## Addendum 2026-09-29 (second) — a held request's subject must belong to its brand

Prompted by task-9, reproduced by a test the same day and decided by the user on
2026-09-29. §4's *"the platform holds the pending action"* stands; what changes is
which subjects the platform will hold an action for.

**How a held request is raised.** A machine integration without unattended sending
that calls `POST /delivery/send-instances/{send_instance_id}/send` meets
`ApprovalRequired` in the generic API guard, `enforce_api_policy` in
`backend/app/auth/dependencies.py`, which runs before any service has resolved the
addressed row. The handler `_approval_required` in `backend/main.py` then creates the
held request and answers 202, taking `brand_id` from the caller's declared brand and
`subject_id` from the path parameter by convention (`<subject_type>_id`). Nothing on
that path asks whether the subject belongs to that brand.

**What that allowed.** A credential on brand A naming brand B's send id received a 202
and a pending row branded A whose subject is B's send. The content was already
protected since 2026-09-20: `summarise` and `describe` resolve within the row's brand
and report the subject as no longer present, and `execute` is handed the row's brand,
so approving refuses. The queue entry therefore called the residue *noise, not risk*.

**That was wrong, and the reason is the open-request index.**
`ux_pending_actions_one_open_per_subject` is keyed on (action_key, subject_type,
subject_id) with no brand. A's row occupied B's send's slot. When B's own machine then
asked to fire its own send, it hit `DuplicateRequest`, and the handler's retry branch —
which looked the held row up without a brand filter — answered brand B with brand A's
`pending_action_id`. B's orchestrator believed its send was held for review, in an
inbox where nobody could see or approve it, for as long as A's row lived; and A could
re-occupy the slot whenever it lapsed. That is one brand blocking another's sending,
which is the boundary [[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]]
draws.

**1. A held request's subject must resolve within the brand the request is raised in,
or nothing is held.** The handler asks the action before it creates any row. A subject
outside the declared brand is answered 409 with the same `SendInstance {id} not found`
detail the unattended path gives for a foreign or nonexistent send — there
`send_send_instance` raises `ValueError` and the route in `backend/app/delivery/router.py`
maps it to 409. The two paths answer identically, so the refusal is not itself an
oracle for *exists in another brand*.

**2. The check lives on the action, not on the route map.** Actions gain an optional
hook, `subject_in_brand(db, subject_id, *, brand_id) -> bool`, which `send_fire`
implements. Action modules already resolve their subject within a brand for
`summarise` and `describe`, so that is where the knowledge is, and `APPROVABLE_ROUTES`
stays a plain route-to-action map. The queue entry had suggested making
`APPROVABLE_ROUTES` name a resolver; this is the same fix, placed where the knowledge
already lives rather than duplicated beside the route table.

**3. It fails closed.** An action that declares a subject but has no hook is refused
from the guard rather than held — the same posture as a route with no approvable action
mapped to it.

**4. The retry lookup is brand-filtered**, so one brand is never answered with another
brand's `pending_action_id`. If the slot is held by another brand's request — possible
only for rows created before this fix — the answer is a neutral 409 that carries no id.

**5. The unique index is unchanged.** Its key still carries no brand. Once a foreign
row cannot be created, adding brand to the key would be a migration with no
behavioural gain.

**6. [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] point 5 is
narrowed, not contradicted.** Point 5 holds an integration without unattended sending
at 202 rather than refusing it. That governs the sends the caller may address; a
subject outside the caller's brand was never one of those.

**What it costs.**

- **An action added later that declares a subject but forgets the hook is refused from
  the guard.** That is intended, and the message says why.
- **Pre-existing foreign rows, if any, still occupy their slot until they expire.** They
  are answered 409, not mis-attributed.
- **One extra lookup per held request.**

Nothing else in §4 changes: the inbox, the audit trail shared with ADR-141, the
notification-only rule for email and push, and the state-based claim of the addendum
above are untouched.

## Addendum 2026-09-29 (third) — every held request names its subject

Prompted by task-15, from the 2026-09-19 code review's P2-03, and decided by the user
on 2026-09-29. §4's *"the platform holds the pending action"* stands; what changes is
that the platform no longer holds one for nothing in particular.

**The contract admitted a request with no subject, and the index could not see it.**
`pending_actions.subject_type` and `subject_id` are both nullable, and the model in
`backend/app/approvals/db_models.py` documented that as *"the ADR-142 §10 answer: a
proposed settings change has no record to point at, so the contract accommodates it by
requiring a subject of nothing rather than inventing a fake one."*
`ApprovableAction.subject_type` in `backend/app/approvals/actions/base.py` defaults to
`None`. But `ux_pending_actions_one_open_per_subject` is keyed on (action_key,
subject_type, subject_id), and Postgres treats NULLs as distinct in a unique index. Two
open subject-less requests for the same action never collide, so the `IntegrityError`
that `request_approval` relies on for idempotence never fires, and a retrying caller
raises a second held request instead of being answered with the first.

**There is a second path into the same hole.** An action that *does* declare a subject
type can still produce `subject_id = NULL`: the handler `_approval_required` in
`backend/main.py` lifts the id from the path parameter by the `<subject_type>_id`
convention, so a route whose parameter is named otherwise yields NULL, equally invisible
to the index.

**The hole is dormant, not closed.** The registered actions both declare subjects —
`send_fire` on `send_instance`, `ai_subject_apply` on `ai_run` — and no caller passes a
NULL subject. But because the dataclass defaults to `None`, an action whose author
forgets to declare a subject becomes subject-less by omission, not by choice.

**1. Every held request names its subject.** `request_approval` in
`backend/app/approvals/service.py` — the one place every held row is created — refuses a
request whose action declares no subject, and a request whose subject id is missing. The
guard's handler answers that refusal with the same fail-closed 403 it gives a route with
no approvable action mapped to it.

**2. Refusing, rather than choosing an identity, is deliberate.** The two fixes the task
named each decide what identifies a settings proposal. Uniqueness per action when there
is no subject — `NULLS NOT DISTINCT`, available on the Postgres 16 in use — would make
*at most one pending settings proposal of any kind* the rule, so two proposals about
different settings would block each other. A caller-supplied idempotency key would hand
the same question to the caller. Either one is exactly the mechanism §10 declines to
design before 1.0, and neither closes the second path, a subject type with a NULL id.
Refusing NULLs where rows are made makes *one open request per thing* true for every
request that can exist.

**3. The model's accommodation is withdrawn, not deleted.** The columns stay nullable;
the contract no longer admits a subject-less request. When §10 is designed, it decides
what identifies a settings proposal and lifts the refusal with that answer — so §10
inherits an explicit question rather than a silent default.

**What it costs.**

- **§10 cannot ship without first answering the identity question.** That is intended.
- **The dataclass default of `None` still exists**, so a forgotten declaration now fails
  at the first request rather than at registration.
- **One more refusal path for action authors to learn**, beside the brand hook of the
  addendum above.

Nothing else in §4 changes: the inbox, the audit trail shared with ADR-141, the
notification-only rule for email and push, the state-based claim and the brand check of
the two addenda above are untouched, and §10 remains direction only.

## Related ADRs

### Depends On
- [[ADR-140 — AI Capability Layer]]
- [[ADR-141 — In-App Assistive AI Actions]]
- [[ADR-144 — AI Data and Model Governance]]
- [[ADR-002 — API First Architecture]]
- [[ADR-091 — Automation Layer Is Orchestration, Not a Workflow Engine]]
- [[ADR-092 — Automation Layer Receives Triggers, It Does Not Own Trigger Sources]]
- [[ADR-094 — Campaign Execution May Be Started by Scheduler or Automation]]
- [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]]
