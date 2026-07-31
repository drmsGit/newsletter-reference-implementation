---
type: interview-prep
topic:
  - ai
  - automation
  - design
created: 2026-07-27
status: open
---

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

## Cluster 1 — AI Capability Layer (foundational ADR)

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
3. **Audit shape.** *(needs clarification — background:)* Every AI action should
   leave a record so a human can answer "what did it do, and why?" Open question
   is *which fields*: minimum = inputs, model, output, timestamp, who approved (if
   gated); richer = the exact prompt + prompt/model **version**, so behaviour is
   reproducible and a prompt change is traceable. **Decision needed:** minimal log
   vs full prompt/version capture (the latter costs storage, buys debuggability).
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

## Cluster 2 — In-app Assistive Actions (Mode A ADR)

6. **The task-plugin contract.** "One file per AI task" (like a decision
   strategy): what's the declared shape — inputs it reads, the prompt, the
   output type, and where the result lands (which proposal record)? *Lean:
   mirror the decision-strategy registry.*
7. **Build the registry now, or start hardcoded?** Ship 2–3 actions wired
   directly first and extract the plugin pattern once we've seen a few, or design
   the registry up front? *Lean: 2–3 first, then extract (same as how strategies
   grew).*
8. **First actions, in priority order.** Candidates: subject/preheader,
   auto-tag, content-suggestion-with-reasons, translate, write-draft-content,
   category-restructure-report, refine-segment. Which 2–3 lead?
9. **Preview/approval UX.** Per-suggestion accept/reject **with a reason** (like
   overrides), side-by-side diff, inline? Consistent across all actions?
10. **Generated content = drafts.** Confirm AI-authored content records are
    created **unpublished**, requiring a human publish (never auto-live).
11. **Cost visibility.** Show an expected cost/token estimate before a run
    (the backlog cost-feedback item)? Per-run, or just a running total?

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

## Cluster 5 — AI Data & Model Governance (cross-cutting ADR)

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
26. **PII line.** → **Decided (partial):** in-system AI (Mode A) may see more
    (those deployments usually have extra contracts / DPAs); external (Mode B)
    stays minimal. **Still open:** can PII exposure be set **per AI action**?
    Nuances to resolve — first/last name may be fine *unless* combined with email;
    a subject-line suggestion might need the name, *or* should use **merge
    variables** (`{{first_name}}`) instead of the real value. → needs its own pass.
27. **Cost governance.** → **Decided:** a **spend cap** is primary — **warn first,
    then hard stop** (like Claude's own usage) — ideally **per role/user**. A
    per-run cost estimate is nice-to-have *if feasible*, lower priority once a cap
    exists.
28. **"One file per task" — v1 or nice-to-have?** *(needs clarification —
    background:)* Should the clean "drop a file = new AI task" shape (like decision
    strategies) be a **firm v1 contract**, or an **aspiration** we relax when a
    task genuinely needs bespoke wiring (multi-step calls, model quirks, big
    prompts don't always fit one tidy file)? *Lean: aspiration — aim for it, but
    this is the one area where real complexity is acceptable, not forced into a
    template.* **Decision needed:** contract vs aspiration.

---

## How we'll use this
Work through cluster by cluster (like `interview-review`): each answer becomes a
decision logged to `docs/playbook-strategy.md`'s Decision Log; once a cluster is
settled, its ADR gets written from the answers. Order: **1 → 5 → 2 → 3 → 4**
(foundation + governance first, since they constrain the rest).
