---
type: interview-prep
topic:
  - ai
  - automation
  - design
created: 2026-07-27
status: closed
---

> **Progress (2026-07-31):** Clusters 1, 2, 5 are settled **and written up as ADRs**
> — **[[ADR-140 — AI Capability Layer]]** (Cluster 1), **[[ADR-141 — In-App
> Assistive AI Actions]]** (Cluster 2), **[[ADR-144 — AI Data and Model
> Governance]]** (Cluster 5), **[[ADR-142 — Autonomous Workflows and the Automation
> Boundary]]** (Cluster 3) and **[[ADR-143 — AI-Assisted Development Boundary]]**
> (Cluster 4). **✅ All five clusters closed — the AI layer is fully specified.**
>
> Cluster 3 also spun off work outside the AI ADRs: a **suppression/opt-out
> data-model ADR** and an **A/B-component + random-split POC feature** (both in
> `docs/backlog.md`), and a **granularity-vs-authorship clarification** to
> [[ADR-021 — Variants Are Human Created Versions]].

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
   **Refined 2026-07-31 (surfaced during Cluster 3):** input arrives in **three**
   layers, not two — the **dev task file** (goal → where it lands, e.g. "put the
   suggestion in a new variant"); the **manager-owned settings prompt** (general
   output shape: copy, images, header + content ids with layout key); and **ad-hoc
   runtime input** (the *specific* goal a manager types when clicking the button).
   **Anti-proliferation rule:** a minor ad-hoc change of intent is **runtime
   input**, *not* grounds for a new task file + prompt setting — otherwise the
   registry grows one entry per phrasing. Recorded in ADR-141 §1.
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

## Cluster 3 — Autonomous Workflows & the Automation Boundary (Mode B ADR) → ✅ [[ADR-142 — Autonomous Workflows and the Automation Boundary]]

12. **The platform/n8n line.** → **Confirmed + decided.** The platform exposes
    **triggerable-action APIs** (build group, create campaign, send, precompute
    content) + an **approval surface**; **n8n (or any orchestrator) owns the flow
    logic**. (Confirmation only — already backed by [[ADR-091 — Automation Layer
    Is Orchestration, Not a Workflow Engine]], [[ADR-092 — Automation Layer
    Receives Triggers, It Does Not Own Trigger Sources]] and [[ADR-002 — API First
    Architecture]].)
    **Ship scope = one worked example, not a workflow library.** A starter library
    of 4–5 flows would become a maintained integration surface *and* silently
    bless n8n as the one orchestrator. Instead:
    - **No custom n8n node** — the "connector" **is** the documented REST API
      (n8n's generic HTTP node calls it). Publishing a community node would be a
      maintained vendor integration, exactly what the provider layer refuses.
    - The workflow is **documented vendor-neutrally** as a sequence of API calls;
      the **n8n JSON is the one concrete instance** — same shape as the provider
      layer (neutral contract + `resend.py` as the worked example). A company on
      Make / Zapier / Logic Apps / plain cron reads the same doc.
    - **If time allows, two examples:** a **"quick win"** (simple, immediately
      demo-able) **plus one more complex — the automated audience suggestion**
      ("here's a group of people we can send an email to"), i.e. the *autonomous*
      counterpart of the existing in-app system-suggested audience, landing in the
      approval surface.
13. **Approval back into the system.** → **Decided.**
    - **Surface:** the **same approval inbox as Mode A** (Q9) — not a second
      mechanism.
    - **The platform holds the pending action; approving executes it.** n8n calls
      the action, gets "pending approval", and **finishes** — it does *not* park a
      long-running execution on a Wait node. This reuses Mode A's draft→publish
      mechanism (ADR-141) exactly: same object, same inbox, same audit trail, and
      it survives orchestrator restarts.
    - **Email/push is notification only — a link *into* the inbox, never one-click
      approve/reject.** Project-specific reason: [[ADR-132 — Signal Layer
      Implementation Event-Sourced Contributions with Decay-on-Read]] already
      establishes that **security scanners and MPP prefetch links in email**. An
      approve-link is a bearer credential in an inbox — a scanner could auto-trigger
      it and approve a full-audience send with no human involved. (Also forwardable,
      and logged by mail gateways.)
    - **Pending actions expire** — a held "send the morning campaign" is worthless
      three days later.
    - **An action history/log is required** — approved, rejected *and* expired
      requests stay inspectable so anyone can check older requests. Should **extend
      the ADR-140 audit surface, not become a second log.**

    **Ownership context (→ its own section in the Mode B ADR).** Automation is
    typically **not marketing's department**. Two mirror-image expectations meet
    here: the **automation/IT team owns the flows** and "just wants the system to
    send the right email", while **marketing owns the platform** and "just wants the
    platform to do the flow". Flows always need real expertise on the orchestrator
    side, and there is **no way to "prompt" a flow into existence** from our
    architecture — that's platform-specific and explicitly out of scope.
    **Principle adopted: whatever lets the platform work independently wins.** Where
    a capability could sit either side, it goes in the **platform**. The
    orchestrator decides *when*; the platform owns the *actions* — so marketing is
    never blocked on another department for routine work, and the platform stays
    fully usable with **no orchestrator at all**. (Sharpens ADR-092/094: triggers
    may come from anywhere, the actions are always ours.)
14. **Minimal-data contract for external AI.** → **Decided: IDs + non-personal
    metadata; never anything that helps identify the recipient.**
    - **Generalized from ADR-144:** the rule is not "no raw PII *to the model*" but
      **"no identifying data to anything outside the platform"** — models and
      orchestrators are two cases of one rule. (Q13 established the orchestrator may
      literally be *another department's* system, so it is external even when no AI
      is involved at all.)
    - **Non-personal metadata is fine and wanted** — campaign/group **labels,
      counts, statuses** — so a flow's Slack/email notification is actually readable
      ("Campaign *Autumn Hiking* — 1,240 recipients in *Hiking enthusiasts*"). The
      test is simply: **does it help identify the recipient?** If yes, it stays home.
    - Personalization stays with **merge variables resolved locally at render**
      (ADR-005 / ADR-144).
    - **Same opt-up mechanism** as ADR-144 — a flow that genuinely needs a raw field
      (e.g. pushing a record into another system) is a deliberate, per-action,
      **logged** opt-up, not a special orchestrator rule.
    - **Hosting (self-hosted vs cloud n8n) stays the company's call** — ADR-144 §3;
      no residency judgement from us.
    - **Each triggerable action declares its own minimum payload**, mirroring
      ADR-141's task-file contract (declared inputs, PII-filtered by default) — no
      single global payload spec to maintain.
    - ⚠️ **Wording caution for the playbook:** recipient IDs are **pseudonymous, not
      anonymous** — they still point to a person for anyone holding the platform. So
      the accurate claim is "**no directly identifying data leaves the platform**",
      not "no personal data leaves the platform." (Accuracy note, not a legal call —
      ADR-144 §3 stands.)
15. **Reference workflows to ship.** → **Decided: two artifacts, chosen to prove
    two *different* value stories.**
    - **Quick win = deliverability-anomaly alert.** Read-only (schedule → read
      stats → notify): no approval, no send, so nobody can break anything by
      importing it, and it proves the platform→orchestrator direction in minutes.
      **Value story = "it improves daily business too."** And it addresses a real
      market gap: **not seeing deliverability issues for too long is a huge problem
      with current platforms** — unless you build your own workaround, you simply
      never learn there *is* an issue. (Fits pillar #1: "I can't see what the system
      is doing and why.")
    - **Complex = automated audience suggestion → approval inbox.** **Value story =
      the marketer's** — this is where a marketing manager sees the value. It also
      exercises the whole Q13 loop end-to-end: autonomous trigger → platform holds
      the action → approval inbox → human approves → platform executes.
    - **Everything else — fatigue, precompute "next content", morning campaign —
      documented as vendor-neutral call sequences in the playbook, no shipped
      JSON.** Prose costs nothing to keep current and still gives the "starter
      library" feel, while the maintained artifact count stays at **two**.
    - (Fatigue is additionally blocked on the temporary-exclusion concept — Q16.)
16. **Temporary exclusion — new concept.** → **Decided (Cluster-3 scope); modeling
    deferred to a data-model ADR.**
    **Mechanism:** a **`suppressed_until`-style recipient-level gate**, checked at
    audience resolution beside the consent floor — **one place, not several
    tables/fields** — always paired with a **log of *why*** the recipient is being
    held back.
    **Deliberately broader than fatigue.** One gate, many reasons: **fatigue**
    (system-set, short); **a manual or AI decision** — e.g. *"recipient is in cycle
    XXX, shouldn't get any emails"*, especially useful for **reactivation** cycles;
    and recipient-set **pause/snooze** (§M2 backlog). Only the reason/source differs.
    **Not a consent value** — that would break `detect_consent_drift` (a
    platform-only value reads as CRM divergence), the same reasoning that already
    keeps `suppress_recipient` out of `ConsentSyncLogDB`. **Not a rule-block** — a
    rule-block is per-*audience*, but suppression is a property of *the person* and
    must hold across every campaign.
    **Three-tier precedence (answers "how soft is soft"):**
    1. **Consent** — hard floor, never overridable (legal).
    2. **Suppression** — **soft**: not easy to overwrite, but overridable by an
       **explicit, logged** act.
    3. **Include/exclude rule-blocks** — normal audience logic.
    **External systems must reach it (the Cluster-3-relevant part).** A website form
    ("signed up for the masterclass") fires **"this recipient must get this"** — an
    explicit, per-communication override of the soft suppression. That is a
    **triggerable-action API** like any other, and it is the **pin** mechanism
    already in `resolve_audience` (`… ∪ pins`), now callable from outside.
    **What Cluster 3 actually needs is only:** flows and external systems can
    **read**, **write**, and **explicitly override** this gate.
    **→ Deferred to a data-model ADR (not AI/Mode B):** the concrete table/field
    shape, and an **opt-out code / reason taxonomy** covering "opt-out because
    bounce / active unsubscribe / block / …". The **GDPR-block case is just a
    general opt-out**, with the GDPR information itself owned by the **CRM**
    (ADR-120/122). Open modeling question for that ADR: a *cycle-scoped*
    suppression ("while in cycle XXX") has no known end date, so it does not map
    cleanly onto a plain `until` timestamp.
17. **Champion/challenger (the 5%).** → **Decided: drop the per-email 5% feature;
    move testing up to the *strategic* level.**
    **Why it doesn't fit.** You cannot A/B a *rendering* when there are N
    renderings — in a personalized send there is no "version B", there are 80. So
    "how much system-generated content before it stops making sense — 25%? 50%?
    75%?" has no answer **by construction**, which was itself the tell. The unit of
    experimentation must move from **the email** to **the strategy** (which
    categories, what cadence, which audience, how much exploration). It is also
    strategically wrong to build: it only pays off for **fully manual content** —
    the state the product exists to move companies *out of* — and every ESP already
    ships A/B testing, so it is effort spent competing on a commodity feature in the
    pre-personalization world.
    **ADR-021 was *not* the blocker (correction).** [[ADR-021 — Variants Are Human
    Created Versions]] constrains **granularity** (don't spawn one variant per
    resolution — dynamic selection stays *inside* one variant), **not origin**. An
    AI-drafted challenger variant reviewed by a human was always legitimate. But its
    *Decision* wording ("a variant is a human-created version") overshoots its own
    *Context* and has now misled **two independent readings** (this session, and the
    shadow-variant backlog entry) → **small clarification worth making**: restate the
    rule around granularity, not authorship.
    **Considered and rejected:** materializing the N renderings as N real variants
    (storage is no longer the constraint). Rejected because it needs a new level
    (`Campaign → Variant → Version`) purely to distinguish "the human's version"
    from "what each recipient got" — a distinction **variant vs.
    resolution/snapshot already draws** (ADR-083). Complexity to re-express
    something already expressed.
    **What we build instead — three answers for three real needs:**
    1. **Cold-start / first-time recipients** (no signal yet): managers build
       **welcome cycles/emails** and use the **Mode-A suggestion button** — *"here's
       what brings the **most diverse engagement** across other recipients."* Note
       the optimization target is **information gain (data/engagement), not
       conversion**. This is the parked **anti-bubble / exploration** concept
       (ADR-132 Notes) surfacing as a concrete first use case, complemented by
       capturing **subscription-form context** as the first *Anhaltspunkt*.
    2. **Long-term strategic suggestions:** the **same Q15 "suggest audience +
       content" workflow, re-aimed** — less *"here's an audience to reactivate / the
       timing is perfect to sell category X"*, more **"history shows this needs a
       shift in strategy — here's a campaign to challenge it."** Same flow,
       **different goal + prompt**. → **Build the operational goal; document the
       strategic goal** — which doubles as a live demonstration of ADR-140's
       frontend-editable-prompt design (same dev scaffold, manager swaps the prompt,
       different product capability).
    3. **Managers who just want A/B:** ship a **simple A/B component + random
       split** → new backlog Feature. Every marketer will ask for it, even if AI
       flows make it redundant over time (**rebranding stays a genuine exception**).
    **On significance (revised).** A significance gate is **optional when the output
    is accumulated learning**, and **mandatory only when rollout is automated**. Not
    every send needs a statistically significant result — it's a process over time.
18. **Fatigue: deterministic first?** → **Decided: yes — deterministic,
    engagement-*rate*-based, and relative to the recipient's *own* baseline.**
    **Not an absolute threshold.** "Open/click rate below X%" punishes a recipient
    whose *normal* is engaging with every 10th email. Fatigue is a **downward trend
    against their personal engagement profile** — was every 3rd, now every 10th. Not
    proof, but the asymmetry is decisive: sending less costs nothing, and nobody
    sends *more* hoping to revive engagement.
    **Computed from existing tables — no new table.** It does, however, need the
    **denominator**: `SignalContributionDB` records *engagements*, not *sends*, so
    "1 of 10" and "1 of 2" look identical, and a quiet sending month would flag the
    entire list as fatigued. So: **rate = engagements (`SignalContributionDB`) ÷
    sends (`DeliveryExecutionDB`)**, bucketed over a window.
    **⚠️ Must use *undecayed* contribution counts, not the decayed signal score.**
    ADR-132 decays on read — comparing "score now" against "score 90 days ago" would
    let **decay itself manufacture a downward trend for every recipient**. Same
    table, different read: raw counts per time bucket.
    **Dependency (noted, not settled): the retention window.** ADR-132 bounds local
    contributions to "a few operational half-lives", and the retention/prune policy
    is still an open Needs-ADR item. The configured fatigue window (e.g. 90 days)
    must fit inside whatever retention is chosen, or the trend silently cannot be
    computed. **→ the two should be decided together.**
    **Manager-adjustable in settings:** the trend threshold as a **relative %**
    ("dropped 30% in the last X days"), the **time frame**, and **how many days a
    fatigued recipient stays excluded**. Writes to the Q16 suppression gate.
    **AI's role is tuning, not prediction — a third kind of AI action.** Over time
    AI proposes threshold changes — *"try 20% instead of 30%"* — through the
    **approval inbox**, writing to **settings**. That is neither content generation
    nor audience suggestion but **AI tuning the system's own parameters**: arguably
    the purest expression of the trust layer, and worth naming as its own capability
    class in the Mode B ADR.

## Cluster 4 — AI-Assisted Development Boundary (Mode C ADR) → ✅ [[ADR-143 — AI-Assisted Development Boundary]]

19. **The never-prod mechanism.** → **Decided: structural enforcement, DEV/PROD
    separation, human-only deployment.**
    - **Structural over procedural.** "AI is *told* not to touch prod" depends on
      compliance and fails under a mistake or an injected instruction — it **did**
      fail once in this very project (the `backend/.env` grep, caught and corrected
      2026-07-26). The robust form is that **the prod credential is simply not
      present in the environment the AI can reach.** Procedural rules stay as a
      backup layer, never the primary one.
    - **DEV/PROD separation always makes sense**, and **deployment DEV → PROD is a
      human task.**
    - **Invariant at every tier: the AI's output is a *proposal* (branch/PR), never
      a deployment.** Mode C is not a different philosophy — it is ADR-140's "AI
      proposes, human governs" pointed at the repo.
    - ⚠️ **Known limit — environment isolation does not contain outbound email.** As
      long as DEV holds a working send-provider key (which development and testing
      need), an AI change in DEV can still send real mail to real people.
      Environment separation limits **system** blast radius, not **outside-world**
      blast radius; its real value is that if something breaks, not the whole system
      fails. **Existing mitigations, to be named as Mode-C safety properties rather
      than mere dev conveniences:** `MockProvider` as the DEV default
      (`send_instance_create` already hardcodes `provider="mock"`), the recipient cap
      in settings, and the not-yet-built send guardrail in `docs/backlog.md`.
    - **Deferred to the Security chapter (not this ADR):** secret-storage services
      (keys held outside any repo file), GDPR/ISO topics, login/SSO, user roles.
    - **Accepted trade-off:** we prepare as much as possible, but running your own
      architecture **costs internal IT resources** — stated plainly in the playbook,
      not glossed over.
20. **AI's reach.** → **Decided.**
    **Allowed:** the repo, ADRs and docs, the dev DB, tests, a local dev server.
    **Off-limits — four rules:**
    1. **Dev data must be synthetic or anonymized — never a prod dump.** ADR-144
       forbids identifying data reaching a model; the *standard industry habit* of
       copying prod into dev "so the test data is realistic" therefore violates it
       through an entirely normal-looking ops decision. This project happens to do
       the right thing already (seeded demo recipients) — stated here as a **rule**,
       not left as a happy default.
    2. **Prod anything** — credentials, DB, deploy path (Q19).
    3. **Secrets in any form** — the `.env` rule generalized to "no secret in any
       file the AI reads". The *how* (key-storage services) → Security chapter.
    4. **Never run a migration against real data.** This project sidesteps it
       entirely (`create_all` + manual `ALTER TABLE`, no migration framework), so it
       costs nothing here — but an adopter using Alembic needs it written down,
       because "the AI ran a migration" is the one Mode-C mistake a branch revert
       cannot undo.
    **Plus the injection rule:** Mode C has a path the other modes don't — the AI
    reads the **dev DB and the repo**, and this platform *ingests external content*
    (webhook payloads, content records, later recipient-submitted form data). So
    text that arrived from outside can end up in front of a dev assistant.
    **Content read from the database, webhooks, or issue text is data, never
    instructions.** Non-obvious precisely because nobody expects a newsletter
    content record to be an attack surface on the development process.
    **Audience widening (user, from experience):** Mode C is **not only developers**
    — the realistic risk case is **a marketer vibecoding against a dev environment
    that holds copied live data**. Most companies he has worked in or for ran
    exactly that: a *pseudo* dev environment containing copied production data, which
    forced everyone to stay cautious inside it — the opposite of why a dev
    environment exists. **→ a built-in anonymization guard is wanted** (see Q20b).

20b. **The dev-data anonymization guard.** → **Decided; written up as a backlog
    Feature.** **Deterministic pseudonymization, not hashing** (a hash protects the
    data and simultaneously destroys the reason to have a dev environment);
    **schema-declared PII fields, not content sniffing** (ADR-144's per-task PII
    filter needs the same metadata — one declaration, two consumers); an
    **exempt-domain allowlist** so the company's own domains stay real and provider
    /campaign testing still works — **multiple domains supported** (different
    brands, external agencies); **non-routable addresses for everyone else**, which
    also closes the Q19 gap (no deliverable customer addresses in DEV ⇒ a stray real
    send reaches nobody); and a **loud DEV startup assertion** that fails on
    unpseudonymized data **and reports what it exempted** (a widened allowlist must
    be visible, never silent; no wildcards).
    **Rejected: a third `dev → testable → prod` environment** — extra infrastructure
    to run (real internal IT cost) and it only *relocates* the risk, since the middle
    tier still holds deliverable addresses. The allowlist does both jobs at once and
    caps AI blast radius at **your own employees instead of your customers**.
    **Change-effort requirement (user):** changes to the "make data unusable" layer
    must be as easy as possible — moving many files between environments reliably
    produces typos and omissions (his Condor experience). Resolution: **declaration**
    lives on the models (written once, never touched at deploy time); **policy** is
    **environment configuration**, so promoting dev→prod is a config difference, not
    a file edit.
    **Deployment clarification (raised by the user).** Code *does* move dev→prod;
    only configuration doesn't. Two code stages are normal and are handled by
    **pointing each environment at a version** — DEV tracks `main`, PROD is pinned to
    a tag — so a promotion (and a rollback) is a pointer change, not a hand-edit.
    **This is not vendor lock-in: git is a protocol, not a vendor** (identical on
    GitHub, GitLab, Gitea, Forgejo, or a bare self-hosted repo). Lock-in would come
    only from making a *provider-specific* CI system the sole promotion path — so the
    usual rule applies: **neutral mechanism (git tags/commits) + one worked example
    (e.g. a GitHub Actions workflow) + documented as swappable**, the ADR-100/101
    pattern pointed at deployment. **Mode C only requires that a human-gated
    promotion step exists and that the AI has no path to it** — never which tool
    implements it.
21. **Supported vs ad-hoc dev tasks.** → **Decided: supported tasks are
    first-class; ad-hoc is best-effort at the same review bar.**
    **Why this is more than documentation hygiene: the seams AI can generate
    against are the same seams a *human* can extend.** What makes a seam usable — a
    declared contract, a worked example to pattern-match, tests that verify it — is
    exactly what makes it AI-generatable. **AI generatability is therefore a
    byproduct of good seam design, not a separate feature**, and the "supported
    tasks" list is simply the **seam list the playbook must publish anyway**, so it
    costs almost nothing extra.
    **Diagnostic that falls out of it:** if AI cannot reliably generate against a
    seam, **that seam is probably underspecified for humans too** — a generation
    failure is a signal about the architecture, not only about the model.
    **Criterion for "supported" — three observable things:** (1) a declared contract
    (ABC, registry, or config manifest); (2) at least one **worked example in-repo**
    to pattern-match; (3) **tests that verify the contract holds**. `DeliveryProvider`
    already satisfies all three (ABC + `resend.py` + tests), so this describes what
    exists rather than an aspiration.
    **Supported list today:** provider adapters (inbound/outbound); decision
    strategies (registry + `ConfigField` manifest); MJML email modules (ADR-131); AI
    task files (ADR-141's contract).
    **Ad-hoc** — bugs, features, performance — stays **best-effort**: same review
    bar, no reliability promise. Playbook line: *"here's where the architecture
    guarantees a shape; everywhere else, normal engineering judgement applies."*
22. **Same discipline.** → **Decided: yes — same bar, plus an ADR-flagging duty.**
    - **Same bar — not higher, not lower.** Mode C output is a PR (Q19), so **the
      review gate is where discipline lives**: same tests, same ADR compliance, same
      review. A *stricter* bar for AI code would encode distrust as policy and slow
      everything down; a looser one is obviously wrong.
    - **Provenance = the commit trailer, nothing in the code.** Already practised —
      every commit in this session carries `Co-Authored-By: Claude`, which is a
      queryable audit trail ("is AI-authored code more defect-prone?"). **No in-code
      marking:** "AI generated this" comments are noise, violate the project's own
      comment discipline, and imply a different standard to the reader.
    - **Tests are the load-bearing part, and the framing matters:** the rule is
      **"the contract must be tested, regardless of who writes the code"** — a
      property of the architecture, not a rule about AI. For supported seams, Q21's
      criterion 3 *is* the enforcement: a tested contract cannot be silently
      violated.
    - **The ADR-flagging duty — and it is a *capability*, not a guardrail.** AI must
      **flag when a request contradicts an ADR instead of silently implementing it**
      (already codified in `docs/CLAUDE.md`). **Key reframe (user):** a human
      developer will never track 60+ ADRs as reliably as AI can — silently
      implementing against a rule happens with human developers too, **probably more
      often**. So this is not a constraint imposed *on* AI to make it as safe as a
      human; it is something **AI does better than humans**, and it is what turns the
      ADR set from aspirational documentation into an **active, enforced
      constraint**. `docs/CLAUDE.md` is therefore the live Mode-C configuration
      artifact — the concrete instance of the "AI-open package" idea in playbook §4D.

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
