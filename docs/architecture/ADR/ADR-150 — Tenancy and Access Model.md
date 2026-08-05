---
type: adr
status: proposed
topic:
  - architecture
  - security
  - access
  - governance
created: 2026-08-02
modified: 2026-08-02
source:
  - "Security Chapter design interview, Part 1 (playbook-strategy.md Decision Log, 2026-08-02)"
depends_on:
  - "[[ADR-004 — Privacy Operations as a First-Class Architectural Concern]]"
  - "[[ADR-120 — CRM as Customer Source of Truth]]"
  - "[[ADR-126 — Maintain Local Recipient Projection]]"
  - "[[ADR-144 — AI Data and Model Governance]]"
enables:
  - "[[ADR-151 — Authentication and Sessions]]"
  - "[[ADR-152 — Secret and Credential Handling]]"
  - "[[ADR-153 — Audit and Accountability]]"
  - "[[ADR-154 — Erasure and Retention]]"
---

## Status
Proposed

## Context

The platform has no authentication, no users and no roles. Everything built so far assumes a single trusted operator sitting in front of a server-rendered UI.

Adding access control touches every route, so its shape has to be settled before more surface is built — retrofitting is the expensive path. Two further pressures make it urgent rather than merely due. First, publishing the playbook (Phase 4C) is explicitly blocked until every part is designed, security included. Second, the intended operating model has an external party in it: the target buyer is an **agency or freelancer serving Mittelstand clients**, and the agency does not host the system — it helps the client host it on the client's own infrastructure and then helps operate it. That means people outside the company hold real accounts inside it.

A second question arrives with the first: companies frequently run **several brands**. Whether those are separate systems, separate tenants, or a scope inside one system determines how much of the codebase access control touches.

## Decision

**1. Single-tenant per deployment.**
One installation serves one company. Several brands of the *same* company may share an installation, but no agency runs multiple clients on one system. Consequence: no tenant discriminator on any query, and separation between companies is a **deployment boundary**, not a code path. This is ruled in deliberately rather than by omission, because multi-tenancy is the one decision here that cannot be retrofitted without touching every query in the system.

**2. Brands are a scope, not a hierarchy.**
A brand switcher in the top navigation selects the working context. Content and branding differ per brand; most everything else carries over. No nested organisation machinery, no per-brand duplication of settings, strategies or taxonomy. Brands behave "like categories."

**3. Where GDPR forces brand separation, the answer is two installations — and we ship no alternative.**
If a company must keep brand A's and brand B's people apart, they run two systems. We deliberately do **not** offer a mixed-but-separated mode. Shipping one would imply we had judged that arrangement compliant, which is precisely the data-protection liability [[ADR-144 — AI Data and Model Governance]] §3 already refuses to take. A company that wants it anyway is changing its own code, with its own legal advice.

**4. The visual-only case stays degenerate.**
Many companies use "brand" to mean a logo and a palette. One implicit default brand always exists, and the scoping machinery stays invisible until a second brand is created. A company treating brands as a skin pays nothing for the capability.

**5. Three seeded roles over a real permission model — not a role enum.**

| Role | Surface |
|---|---|
| **Admin** | Settings, user management, credentials, provider and AI model configuration |
| **Manager** | Campaigns, content, audiences, sends, AI actions |
| **Viewer** | Read-only — dashboards, signals, delivery history |

Roles and permissions are **rows, not code**. The three ship as a preset a company can extend, replace or ignore; adding a role or scoping a permission further requires no code change. This is the same convention-based-extension posture the decision strategies and email module templates already use. We explicitly do not model the average company's org chart: companies mostly run everything as admin, or arrive with a scheme of their own, and copying an imagined average serves neither.

**6. Access is assigned as `(user × role × brand)`.**
One mechanism serves both role assignment and brand scoping, rather than a role system with a scoping system bolted alongside it. A user may be Manager on one brand, Viewer on another, and absent from a third.

**7. The agency operator is not a role.**
External staff are Admins or Managers who happen to work for the agency. What distinguishes them is **accountability, not capability** — the audit trail records who acted ([[ADR-153 — Audit and Accountability]]). Introducing an `agency` role would encode an organisational relationship into the schema and immediately be wrong for the next company.

**8. Signals are shared at person level; content candidates are scoped to the sending brand.**
Brands are presentation, so engagement is engagement — a recipient who moves from brand A to brand B arrives with useful history rather than as a stranger. The accident worth preventing is *content* crossing brands through those shared signals, so a decision slot resolves **only the sending brand's content by default**. Safe by construction; widening it is a deliberate and visible act, matching the idiom already used by the mock-provider default, ADR-144's PII line and the governed model list.

**9. `recipient.brand` is the sending brand, not an attribute of the person.**
A person connected to brands A and B *is* brand A in the context of a send from brand A; the brand comes from the navigation context. A brand affiliation may additionally arrive from the CRM as a projected attribute ([[ADR-120 — CRM as Customer Source of Truth]] / [[ADR-126 — Maintain Local Recipient Projection]]) feeding the permission table — a source of the data, not a competing concept.

**10. Brand as a decision-strategy filter is demonstrated, not built.**
Restricting candidates to the sending brand, to a named list of brands, or to none of the above is expressible through the existing `candidate_filter_fields` manifest, so it needs no new machinery. It is **out of scope for the POC and the standard package**; the playbook's obligation is to show *that* it is possible and *how*.

## Consequences

### Positive
- No tenant filter on any query, and therefore no class of cross-tenant leakage bug at all.
- GDPR separation between companies is a deployment decision an adopter can verify by looking at their server list, not an invariant they have to trust our code to hold.
- Role and brand scoping share one mechanism, so there is one place to reason about "may this person do this here."
- Companies with their own role scheme are unblocked without a fork; companies with no scheme get three roles that work.
- Cross-brand content leakage is prevented structurally rather than by care.
- The brand capability costs nothing for the companies who do not need it.

### Negative
- An agency operating twenty clients runs twenty installations. That is real operational weight, accepted because the alternative is the irreversible one.
- A company that genuinely needs brand separation *and* wants one system is told no. Some will consider that a missing feature; it is a deliberate refusal to make a compliance judgement on their behalf.
- Sharing signals across brands is defensible only while brands are presentation. A company using brands as a proxy for separate legal entities is in case 3 and should not be on one installation.
- Introducing users and roles requires an actor on every audited action, which is a change to code written when no actor existed.

## Notes

- **Open, deliberately not decided here:** the **consent purpose-split** (marketing opt-in versus transactional basis as distinct permissions on the same person, with brand carried on the grant) is recorded in the Decision Log as a proposed amendment to [[ADR-122 — Minimal Consent Model Required]]. It is not folded into this ADR because it changes an existing accepted decision rather than adding a new concern, and that amendment has not been written.
- Known implementation cost of that amendment: `RecipientDB.consent_status` is a single field today, with the consent gate built on it in `resolve_audience` and `execute_decision_slot`.
- Interacts with [[ADR-081 — AI Ranks Within Governed Candidate Sets]] and [[ADR-083 — Personalization Happens Inside Variants Through Decision Slots]]: the brand candidate filter composes with the governed candidate set rather than replacing it.

## Related ADRs

### Depends On
- [[ADR-004 — Privacy Operations as a First-Class Architectural Concern]]
- [[ADR-120 — CRM as Customer Source of Truth]]
- [[ADR-126 — Maintain Local Recipient Projection]]
- [[ADR-144 — AI Data and Model Governance]]

### Enables
- [[ADR-151 — Authentication and Sessions]]
- [[ADR-152 — Secret and Credential Handling]]
- [[ADR-153 — Audit and Accountability]]
- [[ADR-154 — Erasure and Retention]]
