---
id: TASK-55
title: >-
  Write the reference deployment — the answer to "how do you do security access,
  where do you host, what servers".
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-10-09 18:13'
labels:
  - docs
dependencies: []
type: docs
ordinal: 200800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Docs] — NOT an ADR, and that is the decision. Scoped 2026-09-18 (user) while accepting [[ADR-152 — Secret and Credential Handling]].** **Write the reference deployment — the answer to "how do you do security access, where do you host, what servers".** The question comes up constantly in conversation and the playbook has no answer to point at. **It is deliberately not an ADR**: how an adopter populates the process environment is infrastructure, and [[ADR-152 — Secret and Credential Handling]] point 1 exists so the architecture never has to know. Writing it as an architecture decision would turn a hosting choice into a commitment and invite adopters to inherit ours instead of using what they already operate. **Shape:** one honest reference deployment that is actually run (a single box with a reverse proxy in front is a defensible answer and survives follow-up questions, which a stack we do not operate would not), plus a named seam for the two things larger adopters will ask about — an **API gateway** in front (TLS, rate limits, request limits, IP allowlists, WAF) and an **egress proxy** behind (destination allowlisting, one outbound log, and the strong version: the proxy injects the provider credential so the application holds no key at all). **The claim to make is the seam, not the product** — "the platform holds no secrets of its own and reads everything from the process environment, so inject them with whatever you already operate" is a stronger sentence to a security reviewer than a vendor name, and it is the same move the architecture makes everywhere else. Belongs in Phase 4 playbook production.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 158, section "Features", position 8 in that section (top = do next). The description is the original entry, verbatim.

2026-10-09 (interview-review triage): two items for the reference deployment. (1) PUBLIC_BASE_URL is a required setting, an https address on a domain the company owns; task-330 makes a real send refuse without it. (2) Business P2-G2: per-integration request budgets belong to the gateway in front of the app, keyed on the API key; inside the app only sends are bounded, by approval holds and the recipient cap. This task's gateway seam is where that lives.
<!-- SECTION:NOTES:END -->
