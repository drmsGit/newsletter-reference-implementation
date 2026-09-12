# Positioning — gate state

**Status: no statement adopted.** This is the single named blocker on public
beta and on Phase 4C (write & publish). It is not blocked on features.

## What is settled
The *axis* is decided, even though the sentence is not. Recorded across
`docs/playbook-strategy.md` §5 and `docs/business-interview.md` (2026-07-12):

- Compete on **control, transparency, portability, teachability**.
- Do **not** compete on production speed. Klaviyo plus an AI agent wins that
  outright, and the small-shop-wants-speed persona is deliberately ceded.
- The differentiators that survived the Klaviyo/MCP market shift: recipient-projection
  ownership, consent and suppression as a provider-independent enforcement point,
  provider independence, explainable decisioning, and the architecture itself as a
  teaching artifact.
- Since 2026-08-12 there is a candidate sharpening: the product is **content
  management and orchestration for any API-reachable channel**, not an email tool.
  This is the strongest available expression of pillar 3 for the Mittelstand
  segment — an adopter can connect a local letter shop no SaaS vendor will ever
  integrate. The omni-channel interview **closed 2026-09-01 (25/25)** and is
  written up as ADR-160–164, accepted 2026-09-12, with
  [[ADR-165 — Core Scope Is Channel-Neutral Content Orchestration]] superseding
  ADR-001 to make channel-neutral orchestration the formal core scope.
  **It is designed and accepted, not built** — only email is implemented.
  **Decided 2026-09-12: that does not clear rule 2 below, so this sharpening
  stays out of the headline claim until there is code.** The rule's bar is
  *demonstrable in the repo*, and accepted ADRs demonstrate a design, not a
  capability. Revisit when a second channel actually sends.

## What a candidate statement must satisfy
1. Names the primary audience (agencies and freelancers serving mid-market),
   not the end customer, since that is the economic buyer.
2. Makes no claim that cannot be demonstrated in the repo today — check against
   `docs/backlog.md` and the roadmap status table before adopting.
3. Survives `positioning-critic` without the strongest objection being fatal.
4. Does not drift onto the production-speed axis.

## Process
Draft options in `docs/business/decisions/`, one file, several statements, no
winner picked in the same pass. Stress-test each with the `positioning-critic`
agent. Adopt by writing the chosen statement into this file with a date, and
superseding rather than editing when it changes.

## History
- 2026-08-20 — file created; gate still open. `CLAUDE.md` had pointed here since
  before the file existed.
- 2026-09-12 — corrected the stale claim that the omni-channel interview was
  deferred; it closed and its ADRs were accepted. Rule 2 was tested against the
  result and **held**: designed-and-accepted does not count as demonstrable, so
  the omni-channel sharpening stays out of the headline. Gate still open — no
  statement adopted.
