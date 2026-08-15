# Project Context

This is the Newsletter Blueprint — a vendor-neutral reference architecture for email marketing systems.

## ADR Location
All architecture decisions are in `docs/architecture/ADR/`.
Before implementing anything, check relevant ADRs for prior decisions.

## Key Decisions
- One campaign = one email
- Content is referenced, never copied
- Structure is stored separately from content
- Delivery layer is provider-agnostic

## Before any code change
State, before touching any file — whether asked to review, suggest, or implement directly:
1. Which file(s) will change
2. What the change does
3. Which ADR (by number) this implements, extends, or is constrained by — if none applies, say so explicitly
4. What could break or is unverified

This applies to every edit, including direct implementation requests, not only review requests.

## Review Instructions
When reviewing code or suggesting implementations:
1. Check ADRs for relevant decisions
2. Flag any implementation that contradicts an ADR
3. Suggest fixes — do not implement without explicit approval