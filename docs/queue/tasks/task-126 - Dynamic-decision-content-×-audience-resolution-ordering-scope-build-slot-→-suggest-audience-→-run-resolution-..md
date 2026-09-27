---
id: TASK-126
title: >-
  Dynamic decision content × audience: resolution ordering + scope (build slot →
  suggest audience → run resolution?).
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-09-27 14:29'
labels:
  - needs-adr
  - backend
dependencies: []
type: decision
ordinal: 301000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
📋 **Dynamic decision content × audience: resolution ordering + scope (build slot → suggest audience → run resolution?).** Surfaced 2026-07-26. When a campaign's content is *dynamic* (decision slots resolving per recipient, ADR-083), the plan-a-send flow has an unresolved ordering/scope question that the current build papers over. **(A) The circular dependency.** "Suggest audience" derives the audience *from* the campaign's content categories — `campaign_category_scores` (`audience/service.py`) reads module content records **plus already-resolved decision picks** (`DecisionResolutionDB.content_record_id`). But decision-slot content is chosen *per recipient*, so the content's categories depend on *who is in the audience* — which is the thing we're trying to suggest. Chicken-and-egg. Today it's masked: suggest-audience just reads whatever resolutions already exist (seeded/prior); for a fresh campaign whose content is *only* decision slots with no resolutions yet, it sees only the direct module content and ignores the slot's candidate pool entirely. **Candidate fix to break the loop:** suggest the audience from the slots' **candidate-pool** categories (the `candidate_filter.category_ids` + the categories of candidate content) rather than from already-resolved picks — i.e. target people interested in what the campaign *could* show, then resolve per person *within* that audience. **(B) Resolution scope — on segment / on every person / both?** Two scopes exist *implicitly* today via a strategy's `requires_recipient` meta (`decision/service.py`): personalized strategies (e.g. `recipient_top_score`) resolve **per recipient** (one row per (slot, recipient), new row only when the pick changes); non-personalized (e.g. `top_score`) resolve **once per slot** (recipient_id=NULL, single row updated in place). What does **not** exist is a first-class **per-segment** scope — "audience group A gets pick X, group B gets pick Y" as one resolution per segment rather than per individual. Options to decide: (i) per-person only (max personalization, but O(recipients) resolutions + the snapshot/storage cost already flagged in the rendered-HTML Needs-ADR item); (ii) per-segment (one resolution per audience group — far cheaper, coarser, loses individual personalization); (iii) both, selectable per slot (most flexible, most surface area). Interacts with the "freeze vs re-run at send" audience mode already built (`488c837`) and with batching (per-person resolution favors small batches; per-segment favors one blast). **(C) The meta-question the user is really asking: guide vs. implement.** Do we (1) document this as a **playbook guide** — "these are the steps: build slot → resolve → suggest audience → send, and here are the scope trade-offs" — leaving adopters to wire their own order/scope (max flexibility, fits the reference-architecture + playbook ethos, less turnkey); or (2) **implement** an opinionated codified flow in the product (a wizard-like build-audience → resolve → send path) that accepts **less flexibility** for a working out-of-the-box experience? Likely answer is a mix (a documented recommended flow + a sensible default implementation with escape hatches), but it needs deciding as an ADR before more of the plan-send/suggest-audience surface hardens around an unstated assumption. Ties to: ADR-083 (per-recipient decision personalization), the rendered-HTML/snapshot storage Needs-ADR item (per-person resolution multiplies stored artifacts), the batching/send-timing Needs-ADR item, and the freeze/re-run audience mode. Source: user, 2026-07-26 (Phase 3 audience/send session).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 453, section "Needs ADR", position 10 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
