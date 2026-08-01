---
type: adr
status: accepted
topic:
  - architecture
  - ai
  - governance
created: 2026-07-31
modified: 2026-07-31
source:
  - "AI Layer design interview (interview-prep, 2026-07-27 – 31), Cluster 1"
depends_on:
  - "[[ADR-003 — Human-Guided Marketing, AI-Optimized Delivery]]"
  - "[[ADR-040 — Introduce Override Layer]]"
  - "[[ADR-041 — Override Precedence]]"
  - "[[ADR-080 — Human-governed Taxonomy Before AI Selection]]"
  - "[[ADR-082 — AI May Recommend but Not Publish]]"
  - "[[ADR-085 — Decision Resolution Should Be Optionally Explainable]]"
enables:
  - "[[ADR-141 — In-App Assistive AI Actions]]"
  - "[[ADR-142 — Autonomous Workflows and the Automation Boundary]]"
  - "[[ADR-143 — AI-Assisted Development Boundary]]"
  - "[[ADR-144 — AI Data and Model Governance]]"
---

## Status
Accepted

## Context

ADR-003 set the philosophy — human-guided marketing, AI-optimized delivery; **AI
proposes, human governs**. ADR-080/081/082 already govern AI *inside the decision
layer* (a human-governed taxonomy, AI ranks only within governed candidate sets,
AI may recommend but not publish). But those are point solutions. The product now
needs a **general way to add AI capabilities across the whole system** — subject
lines, tagging, content suggestions today; autonomous workflows and dev-time
assistance later — without each one re-inventing trust, audit, prompt ownership,
and governance.

Two failure modes to avoid:

- **AI in the architecture core.** Baking a model into the core makes it
  un-swappable and couples the reference architecture to a vendor — the opposite
  of the provider-adapter stance (ADR-100/101) the rest of the system takes.
- **"Everything is a pending proposal."** Routing every AI action through the
  override/approval layer forces the system to evaluate *all* campaigns rather
  than the one source it acted on — a real token and performance cost — and buries
  managers in approvals. A trust layer does not have to mean an approval queue for
  everything.

A third reality: a company may want **no AI at all** (e.g. a client whose new CDP
already contains AI and who wants none in this architecture). The layer must be
fully optional, per capability.

## Decision

**1. AI is a pluggable capability behind existing seams — never the core.**
AI capabilities plug in through the two patterns the system already uses: the
**provider-adapter** pattern (as `DeliveryProvider`, ADR-100) and the
**plugin-registry** pattern (as the decision-strategy registry). A model is added
by a file, not by editing the core. A company that never enables AI loses nothing
structural — the platform is complete without it.

**2. The trust guarantee is "reversible + audited + a human can interfere" — not
"everything is a pending proposal."**
**Direct write is the default.** Trust comes from the fact that AI actions are
reversible (via the Override Layer, ADR-040/041), fully audited (point 5), and
interruptible by a human at any time — *not* from making every action wait in a
queue. This reframes what "trust layer" means for this architecture: govern the
blast radius, not every keystroke.

**3. Approval is a per-task setting, not one global rule.**
Each task declares its approval behaviour — **auto-apply** vs **require-approval**
— chosen by the task's risk and implementation, not a system-wide switch.
Auto-apply is the default; approval-gating is opt-in per company/task. This gives
**graduated trust**: a company can start a task approval-first and flip it to
auto once it trusts the output.

**4. Prompts are frontend-editable and content-style versioned — the manager owns
them.**
A dev cannot meaningfully *evaluate* a marketing/BI prompt, so "manager writes it,
dev implements it blind" is backwards. Structure:
- **One (minimal) file per AI task = the dev-owned technical *scaffold*** — what it
  reads, the output shape, where the result lands (the firm contract, ADR-144).
- **The prompt + guards live in frontend settings** — manager-owned, versioned and
  published like content. The scaffold *references* them; it never embeds them.

**5. Every AI action is audited with the standard fields plus the prompt-version
id.**
Log inputs / model / output / timestamp / approver-if-gated, **plus the published
prompt-version id** used. Because the live prompt lives in the DB (point 4), the
version id is what makes a decision reproducible — no need to copy the full prompt
text into every row; the id resolves it. (Same event-sourced, re-derivable spirit
as ADR-132 and the explainability of ADR-085.)

**6. Guardrails are a company-editable "DON'T EVER" file plus per-prompt guards —
not a fixed "not-AI" list.**
Companies want full AI capability and add their own limits; a hard-coded list of
things AI may never touch is the wrong shape. Instead, a **global,
company-editable "DON'T EVER" guardrail file** holds negative constraints, and
each prompt carries its own guards in settings. These guardrails also protect
against a bad or unsafe prompt edit (point 4).

**7. A global kill switch always exists; enablement is granular and the company's
call.**
Because the system is open-source, a company that doesn't want AI simply doesn't
enable/implement it — and *how much* AI, per capability, is their decision. On top
of that, a **global kill switch always exists** for emergencies (data breach, a
model behaving unexpectedly).

## Consequences

### Positive
- AI is swappable and optional; the reference architecture stays vendor-neutral
  and complete without it.
- Trust is enforced by reversibility + audit + human interruption, so the default
  path (direct write) is fast and doesn't drown managers in approvals.
- Prompt ownership sits with the people who have the domain expertise; devs own
  only the technical scaffold.
- Every AI action is reproducible from its prompt-version id.
- A company can dial AI from "none" to "fully auto per task" without code changes.

### Negative
- Two moving parts per task (dev scaffold + frontend prompt/guards) instead of one
  — a small coordination cost, deliberately taken to put prompts where the
  expertise is.
- "Reversible + audited" shifts responsibility onto the audit trail and the
  override layer being correct; if either is weak, the trust guarantee weakens.
- A company-editable "DON'T EVER" file is only as good as what the company writes
  in it.

## Notes

- **Three modes.** This foundational layer is shared by all three AI modes:
  **A** — in-app assistive button actions ([[ADR-141 — In-App Assistive AI Actions]]);
  **B** — autonomous workflows / the automation boundary
  ([[ADR-142 — Autonomous Workflows and the Automation Boundary]], mostly n8n);
  **C** — AI-assisted development, never prod
  ([[ADR-143 — AI-Assisted Development Boundary]]). Cross-cutting data,
  model, cost, and PII governance is [[ADR-144 — AI Data and Model Governance]].
- **Client stance.** For a company that wants no AI in its architecture, the honest
  answer is that AI still helps through *different approaches* (recommendations,
  the feedback loop) — but whether to enable any of it stays entirely their choice
  (point 7). This ADR makes "off" a first-class configuration, not a fork.
- **Status.** Decided in the design interview; implementation is phased (Mode A
  first — see ADR-141). Marked accepted as a design decision, not as shipped code.

## Related ADRs

### Depends On
- [[ADR-003 — Human-Guided Marketing, AI-Optimized Delivery]]
- [[ADR-040 — Introduce Override Layer]]
- [[ADR-041 — Override Precedence]]
- [[ADR-080 — Human-governed Taxonomy Before AI Selection]]
- [[ADR-082 — AI May Recommend but Not Publish]]
- [[ADR-085 — Decision Resolution Should Be Optionally Explainable]]

### Enables
- [[ADR-141 — In-App Assistive AI Actions]]
- [[ADR-142 — Autonomous Workflows and the Automation Boundary]]
- [[ADR-143 — AI-Assisted Development Boundary]]
- [[ADR-144 — AI Data and Model Governance]]
