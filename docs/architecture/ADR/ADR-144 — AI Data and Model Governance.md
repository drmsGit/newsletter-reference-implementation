---
type: adr
status: accepted
topic:
  - architecture
  - ai
  - governance
  - privacy
created: 2026-07-31
modified: 2026-07-31
source:
  - "AI Layer design interview (interview-prep, 2026-07-27 – 31), Cluster 5"
depends_on:
  - "[[ADR-140 — AI Capability Layer]]"
  - "[[ADR-004 — Privacy Operations as a First-Class Architectural Concern]]"
  - "[[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]"
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
  - "[[ADR-101 — Provider Capabilities Are Explicit]]"
enables:
  - "[[ADR-141 — In-App Assistive AI Actions]]"
---

## Status
Accepted

## Context

ADR-140 established AI as a pluggable capability. Four concerns cut across *every*
AI capability — Mode A now, Modes B and C later — and belong in one place rather
than being re-decided per task: **which model** runs a task, **what data** the
model sees, **what it costs**, and **where a task's configuration lives**. This
ADR fixes those cross-cutting rules so individual task ADRs (starting with
ADR-141) inherit them.

A guiding constraint: we are building a reference architecture, **not offering
data-protection or legal advice**. Where a choice is a legal/compliance judgement
(model provider, data residency), the platform's job is to make the safe default
easy and the exposed choice explicit — not to make the call for the company.

## Decision

**1. The model is an adapter — `AIProvider`, mirroring the send adapter.**
Add or swap a model by a file, exactly as the outbound `DeliveryProvider`
(ADR-100/101) makes the ESP swappable. Ship **two worked examples — Claude and one
EU-hosted model** — so "a GDPR-friendly setup is possible" is *demonstrated*, not
merely claimed. (The Claude integration here is Claude-the-model via the Anthropic
API with its own key — distinct from Claude Code, the dev-time assistant of Mode
C.)

**2. Per-task model choice is the documented direction; the POC ships one model +
a guide.**
The POC uses one model plus a **"how to add and connect more models" guide** (the
same shape as the swap-send-provider guide). Per-task / expert-model selection
(a creative model for copy, a coding model for dev tasks, a cheap model for
workflow steps) is real and goes in the ADR as the **direction**, not the POC
build.

**3. No EU / residency warning flag.**
We are not data-protection experts and will not take on that liability. Provider
and data residency are the **company's call**; the platform defaults to data
minimisation (point 4) and stays out of the legal determination. We do not ship a
UI flag that purports to tell a company whether a given provider is
"GDPR-compliant."

**4. PII is a per-task setting, default "no raw PII to the model."**
By default the AI works on **IDs, signals, and content**, and personalises via
**merge variables** (`{{first_name}}`, reusing the merge context of ADR-005): the
platform fills the real value **locally at render**, so identities never leave the
system. A task may be **explicitly opted up** to see raw fields (e.g. an in-system
Mode-A task operating under a DPA) — that is the company's deliberate,
**logged** choice. Safe by construction; more exposure is always a deliberate act,
never a default. (This is the AI-facing expression of ADR-004.)

**5. Cost governance = a spend cap with a configurable, role-bound buffer,
enforced as a pre-call gate.**
A **spend cap is primary** — **warn first, then hard stop** — scoped **per
role/user**. Enforcement (detail carried from Cluster 2 / Q11b):
- Each task declares its own output ceiling (the model's `max_tokens`), so the
  platform can compute the task's **worst-case total** (`count_tokens(input)` +
  output ceiling) **before running**.
- The hard stop is a **pre-call gate**: the platform **refuses to start** any task
  whose worst-case wouldn't fit under the remaining cap. So a stop always lands
  *between* tasks, never mid-task — nothing is spent on a task that can't finish
  (no "paid, got nothing").
- If a running task hits its own output ceiling, the **partial result is still
  shown** (display ≠ commit), never silently discarded.
- The **buffer is configurable** (the company is filling in its token limit
  anyway) and **strictly bound to user role/permission**.
- There is **no provider "total budget" knob** — the worst-case ceiling is computed
  by us, which is more reliable than depending on a provider feature. (A *soft*,
  model-paced budget exists — `task_budget`, agentic-loop-only — noted as the
  Mode-B direction, not a stage-1 build.)
- The **per-run cost estimate is dropped from the UI** (a manager is unlikely to
  use it; it is open code for any company that wants it). The UI shows **total
  cost/tokens against the cap**.
- **Phase-1 MVP stops here.** An opt-in **overage** mode ("keep going, pay per
  token") and richer controls are a future **"AI extra package."**

**6. The task file is a firm contract for the scaffold; the prompt is config.**
The per-task file is a **firm contract for the technical scaffold** — inputs,
output type, where it writes — and it stays clean *precisely because* the messy,
domain-specific part (the prompt + guards) is lifted OUT of the file into
frontend-versioned settings (ADR-140, point 4). So: **firm contract for the
scaffold, config for the prompt.**

## Consequences

### Positive
- The model is swappable like the ESP; "GDPR-friendly is possible" is proven with a
  shipped EU example, not asserted.
- PII minimisation is the default and safe by construction; more exposure is a
  logged, deliberate opt-up.
- Spend can't overrun: the cap is enforced before a task starts, per role/user,
  and a near-limit stop never wastes an in-flight task.
- The platform takes no legal/compliance liability it isn't qualified to hold.
- Task files stay small and reviewable; prompt churn lives in versioned settings.

### Negative
- Merge-variable personalisation is less flexible than handing the model raw
  fields — a deliberate trade for privacy; tasks that genuinely need raw PII must
  opt up under a DPA.
- Per-task model selection is documented but not built in the POC, so early
  adopters run one model until they wire the guide.
- Default token weights, cap thresholds, and buffer sizes are judgement calls that
  need real usage to tune.
- "No residency flag" means a company must make its own provider/compliance call —
  intentional, but it is work the platform won't do for them.

## Notes

- Applies to all three AI modes. Mode A ([[ADR-141 — In-App Assistive AI Actions]])
  is the first consumer; Mode B
  ([[ADR-142 — Autonomous Workflows and the Automation Boundary]]) and Mode C
  (planned ADR-143) inherit the same model adapter, PII line, and cost cap.
- The cost-cap enforcement here is the governance rule; ADR-141 defines only the
  Mode-A **cost *visibility*** UI (total vs cap).
- **Status.** Decided in the design interview; the model adapter, EU worked
  example, and cap enforcement are phased with the Mode-A build. Accepted as a
  design decision, not as shipped code.

## Related ADRs

### Depends On
- [[ADR-140 — AI Capability Layer]]
- [[ADR-004 — Privacy Operations as a First-Class Architectural Concern]]
- [[ADR-005 — Separate Snapshot State from Recipient Delivery Artifact]]
- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]
- [[ADR-101 — Provider Capabilities Are Explicit]]

### Enables
- [[ADR-141 — In-App Assistive AI Actions]]
