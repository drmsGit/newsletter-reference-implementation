---
id: TASK-77
title: >-
  Documented escape hatch for a model that cannot count tokens — "what to do if
  your AI provider has no counting endpoint".
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - docs
dependencies: []
type: feature
ordinal: 203000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** **Documented escape hatch for a model that cannot count tokens — "what to do if your AI provider has no counting endpoint".** Surfaced 2026-08-02 (`/interview-review`, AI Q2). `count_input_tokens()` is a **required** abstract method on `AIProvider`, deliberately: ADR-144's spend cap is a pre-call gate, and an adapter that cannot report a worst case cannot be gated, so making it optional would let some models silently bypass the cap (ADR-101, capabilities are explicit). The requirement stays. **But a company whose chosen model has no counting endpoint currently has no path at all** — the contract simply refuses the adapter, which is the wrong failure for a reference architecture whose whole pitch is "swap the vendor." Needs: a documented way to add such an adapter, an explicit statement of **what is lost** (the pre-call gate — the cap degrades to post-hoc, or the company sets a hard run-count limit instead), and ideally a structural seam so opting out is a visible, deliberate configuration rather than a fork of the contract. Judged unlikely to bite — a model sold into the EU that cannot tell you what a call cost is hard to imagine — but the cost of being wrong is an adopter who cannot use their own provider. Fits alongside the per-feature model selection item and the still-unbuilt EU-hosted adapter that ADR-144 §1 committed to; write it with those. Source: [[Interview Prep - AI]] → AI Layer Q2.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 230, section "Features", position 30 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
