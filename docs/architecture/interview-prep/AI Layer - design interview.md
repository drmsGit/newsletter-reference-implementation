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

1. **Approval is universal, but is it uniform?** Does *every* AI action require
   explicit human approval before it takes effect, or do low-risk actions
   (translate, auto-tag) **auto-apply with undo**, while high-risk ones (send,
   audience change, publish) require approval? *Lean: tiered by risk, not
   one-size.*
2. **Where do AI outputs land?** Always as **proposals in the existing trust
   layer** (the override/suggestion mechanism), never a direct write? Is there a
   single unified "AI proposal" record (like `ContentOverrideDB`) that all
   suggestions flow through for audit/accept/reject — or per-capability records?
3. **Audit shape.** What must every AI action log for the trust trail — inputs,
   prompt, model, output, who approved, timestamp? Is the model/prompt version
   part of the record?
4. **Kill switch / scoping.** Can a company disable AI entirely, and per-
   capability? Where does that live — the settings/`AppConfig` layer?
5. **What is explicitly NOT AI.** Confirm the restraint line: rule-based
   audiences, threshold scoring, calendar scheduling, consent gating stay
   deterministic. Anything else that should be fenced off from AI on principle?

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

23. **The model adapter.** Confirm an `AIProvider`-style adapter (like
    `DeliveryProvider`): swap/add a model by changing a file. One worked example
    shipped — which model as reference (Claude, given the project)?
24. **Per-task model choice.** Can different tasks use different models (cheap
    model for tagging, strong model for content), configured in settings? Or one
    model per deployment to start?
25. **Data residency = company's call.** We default to **data minimization**;
    the company may point the adapter at any provider incl. US cloud, accepting
    the residency implication. Do we surface a warning/《data leaves EU》flag when
    they do?
26. **PII line.** Do we ever send raw emails/names to a model, or always
    minimized/pseudonymized (IDs + signals + content, not identities)? Where
    exactly is the line, and does it differ Mode A vs B (in-system may see more)?
27. **Cost governance.** Per-run estimate + a spend cap in settings (like the
    recipient cap)? Hard stop or warn?
28. **"One file per task" — v1 or nice-to-have?** If the clean plugin shape
    fights the reality of prompts + model quirks, is complexity acceptable *here*
    specifically (the one place expertise is warranted)? *Lean: nice-to-have;
    don't force it.*

---

## How we'll use this
Work through cluster by cluster (like `interview-review`): each answer becomes a
decision logged to `docs/playbook-strategy.md`'s Decision Log; once a cluster is
settled, its ADR gets written from the answers. Order: **1 → 5 → 2 → 3 → 4**
(foundation + governance first, since they constrain the rest).
