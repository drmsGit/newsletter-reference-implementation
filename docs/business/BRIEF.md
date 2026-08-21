# Brief

## What it is
A vendor-neutral **reference architecture for email marketing systems** — soon
broader: content management and orchestration for any API-reachable channel
(email, push, letter via a letter shop, personalized paid social). It ships as a
runnable modular-monolith reference implementation (FastAPI backend, server-side
Jinja UI, Postgres) plus ~150 ADRs that explain *why* every part is built the way
it is. The code is "usable as-is, but meant to be tailored": every hard part is a
declared seam — send/feedback providers, decision strategies, AI capabilities,
email module templates — with **one worked example each**, never a library of
integrations. The people who tailor it are developers, technically-skilled
designers, and BI teams inside the adopting company, or an agency doing it on the
company's behalf; the marketing manager operates it and never touches code.
The deliverable is the architecture and the teaching material around it (playbook,
optional starter package, workshops/consulting) — not the software alone.

## What it is not
- **Not a fixed commercial product.** No polished SaaS, no feature roadmap owned by us.
- **Not a hosted service.** One install = one company, on the company's own
  infrastructure. Single-tenant, definitively — no tenant filter anywhere, and an
  agency never runs multiple clients on one system.
- **Not a second ESP.** We don't rebuild Mailchimp/Klaviyo/Sendy/Listmonk/Mautic.
- **Not a maintained connector library.** No shipped provider plugins (Salesforce,
  Braze, …), no custom n8n node, no workflow library. The connector *is* the
  documented REST API; a specific integration is paid client work, not a product.
- **Not no-code.** "Modularity" means convention-based extension — drop a file that
  honours a contract — not removing developers.
- **Not competing on production speed.** Klaviyo + an AI agent already wins on raw
  output (templates, copy, basic segments) and we deliberately cede that ground.
  We compete on control, transparency, portability and teachability.
- **Not a compliance guarantee.** We take no data-protection liability; the adopter
  chooses provider, residency and retention. We supply the mechanisms.

## Where it stands
Public beta blocked on: positioning statement.
Early publishing is the SEO strategy — content is not marketing for the
launch, it is the launch.

**Build state (2026-08-20).** The end-to-end path is real and proven live: build
campaign → editable modules → suggested/edited audience → prepare send (audience,
provider, freeze-or-rerun, scheduling, recipient cap) → real Resend delivery from a
verified domain → signed inbound webhooks → per-category signals with decay-on-read.
Phases 1–3C done; the AI layer is designed (ADR-140–144) with Mode A shipped against
a real Claude adapter under a pre-call spend gate; security is designed (ADR-150–154)
with the base built (passwordless sign-in, roles/permissions as rows, one router-level
guard).

**Actual blockers before anything is public**, from the 2026-08-07 external review:
a **P0 consent bug** (a frozen audience is consent-gated at plan time and never again;
the decision layer's consent guard is swallowed by a bare `except ValueError`), **P0
machine authentication** for the inbound/JSON surface, and the **auth enforcement flag
built but shipped off**. The omni-channel design interview (~5 clusters, a ~160-block
of ADRs) is deferred by the user, though it overlaps the P0 consent fix and the
not-yet-started React frontend.

**Note:** `CLAUDE.md` points at `docs/business/POSITIONING.md` for the gate state.
That file does not exist — `docs/business/` holds only an empty `decisions/`
directory. The live strategy record is `docs/playbook-strategy.md` (§5 Decision Log),
with `docs/backlog.md` for the queue and `docs/weekly-summary.md` for the digest.

## Audience
- **Primary (economic buyer):** agencies and freelancers serving mid-market clients.
  They have the technical capacity to act on the architecture and are the workshop
  and consulting audience.
- **Secondary (the end customer, and the story):** German Mittelstand / KMU that have
  outgrown Mailchimp but won't accept Salesforce Marketing Cloud's cost and lock-in.
- **Sharpened by the Klaviyo+MCP shift (2026-07-12):** organisations where "sync
  everything into one vendor's AI surface" is a governance risk rather than a
  convenience; teams needing cross-source or multi-provider orchestration a
  single-vendor agent structurally cannot reach; and people who want to *learn* how
  this is built.
- **Explicitly not the audience:** a single-shop owner who wants good-looking
  newsletters fast, and any prospect whose stated pain is "we can't produce emails
  fast enough." That pain is solved better and cheaper elsewhere.

The three pillars, each a client complaint answered by an architectural choice:
1. *"I can't see what the system is doing or why"* → explainable decision resolution,
   snapshot reconstruction, signals instead of black-box ML.
2. *"Anything complex needs developers"* → convention-based extension points; drop a
   file that follows a contract and the system picks it up.
3. *"Standards don't fit my workflow"* → principles over a fixed tech stack; omni-channel
   is the sharpest expression of this, since an adopter can connect a *local* letter shop
   or regional service no SaaS vendor will ever integrate.

## Related
Condor use case — separate; learnings flow one direction, from here to there.

## Constraints
**What will not be built (decided, do not re-litigate):**
- A full second ESP; maintained provider/CRM connectors; a workflow library or n8n node.
- Multi-tenancy — the one thing that cannot be retrofitted, ruled out deliberately.
- Cross-brand GDPR separation in one install; a company needing it runs two installs.
- Per-recipient LLM *selection*. Ranking governed candidates against a computed
  preference vector is arithmetic, not language: the deterministic strategy is faster,
  auditable and A/B-testable, and the LLM version costs ~€9–12k per 1M-recipient
  campaign. Direction: **AI touches the rules, rules touch the recipients.**
- Organic/broadcast social; SSO/SCIM (documented as the upgrade path, not shipped);
  passkeys (on hold — seven transitive dependencies onto a nine-line `requirements.txt`).
- ADRs committed to unvalidated detail. Name a capability, don't spec a mechanism
  before a real deployment can invalidate it.

**Working constraints:**
- **One worked example per seam** — Resend for send/feedback, Claude for AI, MJML for
  templates. Enough to prove the contract, never a vendor catalogue.
- **Open forks are noted as options now and implemented in the final MVP package**,
  not chased one-by-one. Current deferred set: decision-content × audience resolution
  scope, batching/send-timing, snapshot storage strategy, suppression-list + CRM opt-out
  relay, brand/theming, data lifecycle/retention.
- **AI spend is gated, not reconciled** — a pre-call token gate with a warn/hard-stop
  cap and a $5 reference budget on the ledger. The whole live Claude verification cost
  ~$0.02.
- **Money is the reason some things are late, not the reason they're skipped** — the
  real provider integration was sequenced last precisely because it needs a paid ESP
  account and a verified sending domain.
- **Time is one person's, part-time, alongside freelance consulting** — the long-term
  hope is that the consulting work shifts *into* this project rather than funding it
  from the side. There is no dated deadline in the repo; sequencing is by blocker,
  not by calendar.
- **Architecture decisions are made in this repo**, written as an ADR before
  implementation. Business decisions go to `docs/business/decisions/`, never into an ADR.
