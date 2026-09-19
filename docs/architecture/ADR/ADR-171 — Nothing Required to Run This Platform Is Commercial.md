---
type: adr
status: proposed
topic:
  - architecture
  - governance
  - operations
created: 2026-09-19
source:
  - "User question on stack lock-in, 2026-09-19"
depends_on:
  - "[[ADR-100 — Provider Layer as Send and Feedback Adapter]]"
  - "[[ADR-101 — Provider Capabilities Are Explicit]]"
  - "[[ADR-140 — AI Capability Layer]]"
  - "[[ADR-144 — AI Data and Model Governance]]"
  - "[[ADR-152 — Secret and Credential Handling]]"
---

## Status
Proposed

## Context

The repository prescribes more stack than its own posture suggests: Python, FastAPI, Postgres, MJML, and — since [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] — React and Vite. That accumulation is defensible decision by decision and looks like drift in aggregate, and [[ADR-170 — The Manager Client Is a Plain React SPA, Not Next.js]] books it as a cost in its own `### Negative`.

The question that clarified it, asked 2026-09-19: **is prescribing a stack actually a problem, or is the real constraint something narrower?** The answer offered with the question is the useful one — a company that wanted to rewrite this in PHP could, taking the decisions and the structure rather than the code, and that is a strange thing to want but not a thing the architecture forbids. What would genuinely damage the project is different: **a component you cannot run without paying somebody.**

That distinction has never been written down. [[ADR-101 — Provider Capabilities Are Explicit]] comes close for send providers and [[ADR-144 — AI Data and Model Governance]] for models, but nothing states it about the stack as a whole, so each new dependency is judged on its own merits with no rule to fail.

It matters most for a reference architecture, because the thing being published is the *decisions*. A decision an adopter cannot act on without a subscription is not a decision they have been given.

## Decision

**1. Every component required to run this platform is open-source and self-hostable.**
Required means: with it absent or unpaid, the platform does not work. Python, FastAPI, Postgres, MJML (MIT), React, Vite and React Router are all of them today.

**2. A commercial service may be an adapter. It may never be a requirement.**
Resend and Anthropic are commercial and are reached only through [[ADR-100 — Provider Layer as Send and Feedback Adapter]]'s provider interface and [[ADR-140 — AI Capability Layer]]'s AI interface — each of which ships a mock, and the mock is the default. That is the shape every future commercial dependency takes: an implementation behind an interface, chosen by configuration, with something free on the other side of the same seam.

**3. The check is that the platform runs end to end with no commercial account at all.**
Not a principle to be agreed with — a state to be verified. Compose the campaign, resolve the audience, render, snapshot, send, ingest engagement, and run an AI task, with no provider key and no model key configured. Everything resolves to a mock and nothing refuses.

This is deliberately the same shape as [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §2's *"the platform stays fully usable with no orchestrator at all"*, and for the same reason: a claim about what is optional is worth exactly as much as the test that proves it.

**4. Prescribing a stack is not the thing being avoided.**
An adopter is free to reimplement this in another language, taking the ADRs and the structure; that is what a reference architecture is for, and nothing here is arranged to prevent it. What is being avoided is narrower and harder to escape: **a dependency whose absence is a bill.**

## Consequences

### Positive

- **A rule exists that a future dependency can fail**, where before each was judged alone and none could be refused on this ground.
- **The claim becomes checkable rather than asserted**, which is the difference between this and a README sentence.
- **It explains the mock-first defaults retroactively.** The mock provider and the zero-cost AI mock were each argued locally; this is the principle they were instances of, stated once.
- **It bounds ADR-170's cost.** Prescribing React is a constraint on style; prescribing something unpayable would be a constraint on possibility, and only the second is forbidden.

### Negative

- **Point 3's check does not exist yet**, so this record ships as a rule with its verification owed — the exact shape this repository has criticised elsewhere, and it is named here rather than discovered later.
- **"Self-hostable" is doing real work in point 1 and is weaker than it sounds.** Postgres is genuinely swappable in principle and not in practice: partial unique indexes, `with_for_update`, `DO $$` blocks and timezone-aware defaults are relied on throughout, and `docs/architecture/Code/testing.md` records that SQLite silently changes behaviour rather than failing. "Open source" is satisfied; "portable" is not, and the two are easy to conflate.
- **[[ADR-144 — AI Data and Model Governance]] §1 committed to two worked model adapters** so that "GDPR-friendly is possible" is demonstrated rather than claimed, and the second, EU-hosted one is not built. Until it is, the escape hatch in point 2 is one worked example plus a mock.
- **A rule invites lawyering.** Every future dependency will be arguable as "an adapter", and the honest test is point 3 rather than the label: if the platform stops working end to end without it, it is a requirement whatever the module is called.

## Notes

- **Not about avoiding vendors.** Resend is a real integration, proven live against a verified domain, and Anthropic runs the only built AI task. The rule constrains what happens when the bill is not paid, not whether a bill is ever paid.
- **The adjacent gap this does not cover:** the JSON API cannot currently run the product — 73 UI write routes against 33 JSON ones, measured 2026-09-19 — so "take the backend and bring your own client" is blocked by completeness rather than by licensing. Logged separately in `docs/backlog.md` against [[ADR-002 — API First Architecture]], because it is a different failure with a different fix.

## Related ADRs

### Depends On
- [[ADR-100 — Provider Layer as Send and Feedback Adapter]]
- [[ADR-101 — Provider Capabilities Are Explicit]]
- [[ADR-140 — AI Capability Layer]]
- [[ADR-144 — AI Data and Model Governance]]
- [[ADR-152 — Secret and Credential Handling]]
