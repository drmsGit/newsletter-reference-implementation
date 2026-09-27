---
id: TASK-72
title: >-
  Recall past AI suggestions after one has been applied — a manager-visible run
  history.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 202500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Feature] — Done 2026-09-19.** **Recall past AI suggestions after one has been applied — a manager-visible run history.** Built as option (2), the history view, which this entry already preferred: `/ui/campaigns/{id}/variants/{id}/suggestions` lists every run for a variant with all its options, the prompt version, the model and the token cost, and each option keeps its "Use this" button — a manager coming back is usually coming back to change their mind. A reply that yielded no readable options is shown verbatim instead, which is how the empty-variant refusal reaches the person who paid for it. The approvals screen gained an `?source=ai` filter over the same data, brand-scoped through variant → campaign. **Found independently by the user from the UI**, three days after this entry was written and without reading it. Original text follows. ---  Surfaced 2026-08-02 (user, first live Claude run). Today the Mode-A suggestion flow is write-once from the manager's point of view: campaign → *Suggest subject & preheader* → pick one → the chosen text lands on the variant and **the other two options vanish**. Re-opening the variant shows only the applied subject line; the discarded alternatives are unreachable through the UI — even though `AIRunDB` already persisted the full model output, the prompt version that produced it, and the token cost. The data is there; only the surface is missing. **Two options considered; the user prefers (2).** *(1) Always allow re-selecting the other suggestions* — keep the option list visible on the variant after one is applied, so a manager can switch. Cheapest, but only ever covers the most recent run. *(2) A history view* — a separate page listing past runs with their prompt version and all suggestions, so a manager can look back later instead of reading the database by hand. Preferred: it covers *every* run rather than the last one, it is where "which prompt version produced this?" naturally belongs, and it serves the audit purpose the data is already being kept for. The two aren't exclusive — (1) is a subset of (2) — but (2) is the target. **Audit angle worth noting:** [[ADR-140 — AI Capability Layer]] §3 requires these runs to be recorded, and they are — but today the only way to *read* them is SQL, so the audit trail exists without being usable by the person it is meant to serve. Source: user, 2026-08-02 (post first real Claude generation).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 220, section "Features", position 25 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
