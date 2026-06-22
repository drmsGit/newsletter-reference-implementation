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

## Review Instructions
When reviewing code or suggesting implementations:
1. Check ADRs for relevant decisions
2. Flag any implementation that contradicts an ADR
3. Do not suggest fixes — only flag drift