---
type: adr
status: accepted
topic:
  - architecture
  - ai
  - automation
  - governance
created: 2026-07-31
modified: 2026-07-31
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
