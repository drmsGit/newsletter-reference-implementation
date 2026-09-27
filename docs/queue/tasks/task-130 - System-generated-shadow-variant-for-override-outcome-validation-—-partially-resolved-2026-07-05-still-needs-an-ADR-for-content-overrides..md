---
id: TASK-130
title: >-
  System-generated "shadow variant" for override-outcome validation — partially
  resolved 2026-07-05, still needs an ADR for content overrides.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - needs-adr
  - backend
dependencies: []
ordinal: 301400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
📋 **System-generated "shadow variant" for override-outcome validation — partially resolved 2026-07-05, still needs an ADR for content overrides.** The override-outcome-comparison concept ("70% of overrides didn't outperform the system's pick," `docs/playbook-strategy.md` Decision Log 2026-06-24) needs a real counterfactual to compare against, not a hypothetical "the system would have chosen X" that was never actually sent to anyone. [[ADR-021 — Variants Are Human Created Versions]] frames A/B testing as human-initiated, which is what originally raised the conflict. **Resolved — audience overrides via addition or full acceptance:** confirmed 2026-07-05 — since engagement is tracked per recipient, the manager-added cohort and the system-proposed cohort within one real send are their own natural comparison group; no parallel system-built send needed, no ADR-021 conflict here. **Still open — audience overrides via deletion/exclusion:** people the system proposed but the manager removed never receive anything, so there's no real engagement data for them either — same underlying problem as content overrides, below. Flagged as rare in practice (deletion expected far less often than addition), so deprioritized rather than solved. **Still open — content overrides:** when a manager replaces the system's chosen content, the rejected pick is never sent to anyone, so there's no way to get real engagement data validating "the system's pick would have done just as well" without an actual shadow send or equivalent — this still directly conflicts with [[ADR-021 — Variants Are Human Created Versions]] and needs an ADR amendment or companion ADR before implementation, exactly as originally flagged. See `docs/playbook-strategy.md` Decision Log, 2026-07-05, item 1. Original context: [[Interview Prep - Decision, Overrides, Insight]] → Overrides Q1 (addendum). **Update 2026-07-31 (AI-layer interview, Cluster 3 / Q17):** the champion/challenger feature — *"manager hits send → system builds a version → send it to 5%"* — was evaluated and **dropped**. It had briefly looked like the counterfactual mechanism this item needs. Reasoning: you cannot A/B a *rendering* when personalization produces N renderings per send, so the unit of experimentation moves up to the **strategy** level. **Consequence: this item currently has no candidate solution — do not re-propose the per-email 5% test.** The shadow-variant *concept* may still return inside a **future AI workflow** (strategy-level challenge campaigns generate comparative data over time), just not as a button-triggered 5% send. Also note **[[ADR-021 — Variants Are Human Created Versions]] is not the blocker it was assumed to be here** — it constrains *granularity*, not *authorship*; clarified in that ADR on 2026-07-31.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 461, section "Needs ADR", position 14 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
