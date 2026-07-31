---
type: interview-prep
topic:
  - ai
  - automation
  - design
created: 2026-07-27
status: in-progress
---

> **Progress (2026-07-31):** Clusters 1, 2, 5 are settled and written up as ADRs
> — **[[ADR-140 — AI Capability Layer]]** (Cluster 1), **[[ADR-141 — In-App
> Assistive AI Actions]]** (Cluster 2), **[[ADR-144 — AI Data and Model
> Governance]]** (Cluster 5). Still open: **Cluster 3** (Mode B → ADR-142) and
> **Cluster 4** (Mode C → ADR-143).

# AI Layer — design interview (forward-looking)

Unlike the other interview-prep files (which review *implemented* code), this one
gathers the **decisions** we need before writing the AI ADRs. Five clusters, one
per planned ADR. Each question that already has a steer carries a **Lean:** —
confirm or overturn it; the rest are open.

Established up front (don't re-litigate): AI is a **trust layer** — every AI
decision has a human feedback/approval path; **AI proposes, human governs**; AI
is **pluggable behind existing seams** (provider-adapter + plugin-registry
patterns); three modes — **A** in-app button actions, **B** autonomous workflows
(mostly n8n), **C** dev-time (never prod). The company owns its data and chooses
its model.

---

## Cluster 1 — AI Capability Layer (foundational ADR) → ✅ [[ADR-140 — AI Capability Layer]]

1. **Approval — uniform or per-action?** → **Decided:** approval behaviour is a
   **per-task setting** (auto-apply vs require-approval), declared in the task
   file / prompt / settings — flexes by risk + implementation, not one global rule.
2. **Where do AI outputs land?** → **Decided: direct write by default**, with an
   *opt-in* override/proposal mode per company. Rationale: forcing every AI action
   through the override layer would make it evaluate *all* campaigns rather than
   one source — a token/performance cost. **The trust guarantee is "reversible +
   audited + a human can interfere," not "everything is a pending proposal."**
   (Reconciles with Q1: auto-apply is the default; approval-gating is opt-in.)
   *→ This reframes the foundational ADR — worth a clear statement there.*
3. **Audit shape.** → **Decided** (via Q3b — prompts are frontend-editable +
   versioned): log the standard fields (inputs / model / output / timestamp /
   approver-if-gated) **plus the published prompt-version id** used — the live
   prompt lives in the DB, not git, so the version id is what makes a decision
   reproducible. No need to copy the full prompt text per row; the id resolves it.
3b. **Where prompts live / who edits them.** → **Decided: frontend-editable,
   content-style versioned — prompts are the manager's (marketing/BI) domain.**
   Rationale: a dev lacks the marketing/BI expertise to *evaluate* a prompt, so
   "manager writes it, dev implements it (blind)" is backwards. Structure: **one
   (or minimal) file per AI task** = the dev-owned technical **scaffold** (what it
   reads, output shape, where the result lands); the **prompt + guards live in
   frontend settings**, manager-owned and versioned/published like content.
   Guardrails against a bad/unsafe prompt edit = the global "DON'T EVER" file (Q5)
   + per-prompt guards in settings.
4. **Kill switch / scoping.** → **Decided:** it's open-source — a company that
   doesn't want AI simply doesn't enable/implement it (how much is their call, per
   capability). **A global kill switch always exists** for emergencies (data
   breach, a model behaving unexpectedly).
5. **What is explicitly NOT AI.** → **Decided:** don't rule AI out on principle —
   companies want full AI even if they add limits later. Instead of a fixed
   "not-AI" list, a global, company-editable **"DON'T EVER" guardrail file** holds
   negative constraints. (Context: Tuesday's client has AI in their new CDP and
   doesn't want it in the architecture; our stance is AI still helps via different
   approaches + the feedback loop — but it stays their choice.)

## Cluster 2 — In-app Assistive Actions (Mode A ADR) → ✅ [[ADR-141 — In-App Assistive AI Actions]]

6. **The task-plugin contract.** → **Decided:** the task *file* (dev-owned
   scaffold) declares — **name/id**, **inputs** (platform-gathered, filtered by
   the Q26 PII policy), **output type** (subject / tag list / content-suggestions-
   with-reasons / draft record…), **where it lands** (which record it writes),
   **references** to the frontend-owned prompt id + model (Q24) + guards/PII policy
   (Q26), and **approval mode** (Q1). Technical wiring + pointers; everything a
   marketer touches (prompt, guards) is referenced, not embedded.
7. **Build the registry now, or start hardcoded?** → **Decided:** wire **2–3
   tasks directly first, then extract** the registry (as the decision strategies
   grew). The Q6 contract is already designed, so extraction is light.
8. **First actions, in priority order.** → **Decided: three, built in order
   2 → 1 → 3:**
   1. **Subject/preheader** (easiest — it's the email's own content; suggest 3
      subject/preheader combos, manager approves). Showcases merge-variable PII.
   2. **Auto-tag** (more complex input *and especially output* — the system must
      route tags to the right places). ADR-080 propose-govern loop.
   3. **Content-suggestion-with-reasons** (most important, most complex here).
   Good enough for the POC / MVP package.
   **Implementation note:** first model integrations for testing = **Claude
   (Anthropic API)** + **ChatGPT (OpenAI — user has a Pro account)**, to prove the
   model adapter across two providers. The Anthropic API is Claude-the-model (its
   own key), distinct from Claude Code the coding assistant. The EU-model worked
   example from Q23 (the GDPR "it's possible" proof) is the additional documented
   one. API keys go in `.env`, added by the user; never touched by Claude Code.
9. **Preview/approval UX.** → **Decided:** one **consistent accept/reject
   component in a dedicated UI** (an AI-suggestions / approval inbox), reused
   across tasks — shows output(s) + reason; accept/reject per item, pick-one for
   options; logged either way. **Optional notifications** (desktop push and/or
   email), configurable. This dedicated UI = the same **approval surface** Mode B
   autonomous workflows use (Q13). **Watch item:** accept/reject is the slim
   default, but some tasks may need a short **feedback/iteration flow** ("make it
   punchier" → regenerate); log the need and see whether accept/reject stays
   sufficient or a feedback loop is warranted.
10. **Generated content = drafts.** → **Decided:** AI-authored content is
    direct-written as an **unpublished draft**; going live is the publish step,
    governed by the **per-task manual/auto setting (Q1)** — approval-first by
    default, and a company may flip a task to **auto-publish** once it trusts it
    (graduated trust *is* the point of the trust layer). **Architectural guard
    against the "80 records to approve" problem:** AI generates a **bounded set of
    *shared* variants/drafts, never per-recipient content on the fly** (cost, risk,
    approval-scale) — per-recipient personalization stays with the **decision
    engine + merge variables**, not generative AI. So the approval surface never
    explodes and "always approve" stays practical.
11. **Cost visibility.** → **Decided:** show **total cost/tokens against the cap**
    in the AI UI; **drop per-run estimates** from the UI (a manager likely won't
    use them; it's open code if a company wants them). → raised Q11b below.
11b. **Cost-cap enforcement — what happens near the limit?** → **Decided:** a
    **spend cap with a configurable safety buffer, enforced as a pre-call
    gate.** The company sets its token limit; the buffer is **configurable**
    (they're filling in the limit anyway) and **strictly bound to user
    role/permission**. Each task declares its own `max_tokens` output ceiling,
    so the platform computes the task's worst-case total (`count_tokens(input)`
    + `max_tokens`) *before* running and **refuses to start** any task whose
    worst-case wouldn't fit under the remaining cap — the stop always lands
    *between* tasks, never mid-task, so nothing is spent on a task that can't
    finish (no "paid, got nothing"). If a running task hits its own output
    ceiling, the **partial result is still shown** (display ≠ commit), never
    silently discarded. There is **no API "total budget" knob** — the worst-case
    ceiling is computed by us, which is more reliable than a provider feature.
    (`task_budget` — a *soft*, model-paced budget, 20k-token minimum,
    agentic-loop-only — is noted as the **Mode-B direction**, not a stage-1
    build.) **Phase-1 MVP stops here.** An opt-in **overage** mode ("keep going,
    pay per token") + richer controls are a future **"AI extra package."**

## Cluster 3 — Autonomous Workflows & the Automation Boundary (Mode B ADR)

12. **The platform/n8n line.** Confirm: the platform exposes **triggerable-action
    APIs** (build group, create campaign, send, precompute content) + an
    **approval surface**; n8n (or any orchestrator) owns the flow logic. How much
    do we ship as reference workflows vs just connector files?
13. **Approval back into the system.** When an autonomous flow needs sign-off,
    how? An in-app **approval queue** + an email with approve/reject links? What
    does approving actually trigger (the held action runs)?
14. **Minimal-data contract for external AI.** Does n8n operate on **IDs only**,
    with the platform resolving PII internally? Define the minimum payload per
    action. *Lean: yes — external stays ID-level.*
15. **Reference workflows to ship.** Morning-campaign (build → approve → send),
    fatigue → temporary exclusion, precompute "next content" into the decision
    table, deliverability-anomaly alert. Which are in the starter library?
16. **Temporary exclusion — new concept.** Time-boxed suppression distinct from
    consent opt-out: modeled how — an exclude rule-block with an expiry, or a
    recipient status with a "until" date?
17. **Champion/challenger (the 5%).** AI composes a full variant → sends to a
    slice → measures → rolls out the winner. Is rollout **auto or approval-
    gated**? Reuse the hold-out/control-group mechanism for measurement?
18. **Fatigue: deterministic first?** Start with a rule (>N sends in M days),
    add AI prediction later? *Lean: yes — don't AI what a threshold solves.*

## Cluster 4 — AI-Assisted Development Boundary (Mode C ADR)

19. **The never-prod mechanism.** AI works on the **repo (branches/PRs)**;
    humans review → merge → deploy; prod credentials never reach AI; dev DB only.
    Confirm, and is a separate isolated dev environment the enforcement?
20. **AI's reach.** Repo + ADRs + dev DB + dev-only deploy? Anything explicitly
    off-limits beyond prod (e.g. `.env`, migrations against real data)?
21. **Supported vs ad-hoc dev tasks.** "Supported" = generates against a
    contract (MJML modules per ADR-131, decision strategies per the registry).
    "Ad-hoc" = bugs/features/perf. Do we document the supported ones as first-
    class, ad-hoc as best-effort?
22. **Same discipline.** AI-generated code held to the same ADR + tests-as-
    guardrails bar as human code (must pass tests, reference ADRs)? *Lean: yes.*

## Cluster 5 — AI Data & Model Governance (cross-cutting ADR) → ✅ [[ADR-144 — AI Data and Model Governance]]

23. **The model adapter.** → **Decided:** `AIProvider`-style adapter (swap/add a
    model by a file). Ship **two worked examples — Claude + one EU model** — so
    "GDPR-friendly is possible" is demonstrated, not just claimed.
24. **Per-task model choice.** → **Decided (POC):** one model for the POC + a
    "how to add & connect more models" guide (like the swap-send-provider guide).
    Per-task/expert-model selection (creative vs coding vs workflow models) is
    real — goes in the ADR as the direction, not the POC build.
25. **EU / residency warning flag?** → **Decided: no.** We're not data-protection
    experts and won't take on that liability. Provider + residency is the company's
    call; we default to data minimisation and stay out of the legal call.
26. **PII line.** → **Decided:** PII exposure is a **per-task setting**, default
    **no raw PII to the model** — the AI works on IDs, signals, and content, and
    personalizes via **merge variables** (`{{first_name}}`, reusing ADR-005 merge
    context); the platform fills the real value locally at render, so identities
    never leave. A task can be **explicitly opted up** to see raw fields (e.g. an
    in-system Mode-A task under a DPA) — the company's call, logged. Safe by
    construction; more exposure is a deliberate choice.
27. **Cost governance.** → **Decided:** a **spend cap** is primary — **warn first,
    then hard stop**, **per role/user** (now firm via Q11b). Enforcement detail —
    configurable buffer, pre-call gate so stops land *between* tasks, partial
    results still shown — lives in **Q11b**. Per-run estimate is dropped from the
    UI (Q11); overage / richer controls = future "AI extra package".
28. **"One file per task" — v1 or nice-to-have?** → **Decided (via Q3b):** the
    task **file is a firm contract** for the *technical scaffold* (inputs / output
    / where it writes) — and it stays clean precisely because the messy part (the
    prompt + guards) is lifted OUT of the file into frontend-versioned settings.
    So: **firm contract for the scaffold, config for the prompt.**

---

## How we'll use this
Work through cluster by cluster (like `interview-review`): each answer becomes a
decision logged to `docs/playbook-strategy.md`'s Decision Log; once a cluster is
settled, its ADR gets written from the answers. Order: **1 → 5 → 2 → 3 → 4**
(foundation + governance first, since they constrain the rest).
