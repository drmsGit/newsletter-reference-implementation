---
id: TASK-83
title: >-
  Anti-bubble / exploration in the decision layer — "even when the engine is
  confident about a recipient's category, every once in a while show a
  *different* category to avoid the filter-bubble trap."…
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 203600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** Anti-bubble / exploration in the decision layer — "even when the engine is confident about a recipient's category, every once in a while show a *different* category to avoid the filter-bubble trap." An explore-vs-exploit behavior in the decision strategies (fed by signals), NOT signal storage — surfaced 2026-07-15 during the [[ADR-132 — Signal Layer Implementation Event-Sourced Contributions with Decay-on-Read]] signal design. A recipient who only ever gets their top category gets stuck; occasional diversity keeps the profile honest and gives new interests a chance to surface. Needs a small design (how often, how the alternative category is picked — random vs. second-ranked vs. least-recently-shown). Depends on the signal layer landing first. Source: user, 2026-07-15 (signal-layer design session). **Update 2026-07-31 (AI-layer interview, Cluster 3 / Q17): this now has a concrete first use case and a named objective.** For **cold-start recipients** (a brand-new subscriber with no signal), the Mode-A suggestion button on **welcome cycles/emails** should surface *"here's what brings the **most diverse engagement** across other recipients"* — i.e. pick for **information gain (data/engagement), explicitly not conversion**. That is exactly this explore-vs-exploit behavior, arriving via the cold-start door rather than the filter-bubble door. Pairs with the DOI/subscription-context seeding item below (which supplies the *first* Anhaltspunkt so exploration starts from something rather than nothing).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 242, section "Features", position 36 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
