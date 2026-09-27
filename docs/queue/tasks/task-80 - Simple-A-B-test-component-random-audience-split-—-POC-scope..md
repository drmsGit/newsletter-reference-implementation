---
id: TASK-80
title: Simple A/B test component + random audience split — POC scope.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 203300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** **Simple A/B test component + random audience split — POC scope.** Decided 2026-07-31 (AI-layer interview, Cluster 3 Q17). Every marketer will ask for A/B testing, even though the architecture's own thesis is that personalization makes *content-level* A/B largely redundant over time (**rebranding stays a genuine exception**) — so ship the simple version and let the AI/strategy workflows earn the case for retiring it. **POC scope:** (a) a **random split** function in the segment builder (definitely build); (b) a small A/B component that selects between **variants or subject lines** with a **percentage split**, so one send divides into *x* parts; (c) extend the Mode-A subject suggestion ([[ADR-141 — In-App Assistive AI Actions]]) so that alongside **"use suggestion"** there is **"test suggestions in A/B setup"** — Mode A removes the friction of *writing* a second subject line, this removes the friction of *testing* it (two different problems; conflating them was an error caught in the Q17 discussion). **Sticky assignment for cycle-length tests:** if a test runs across a cycle, a recipient must *stay* in their group — a stateless random split would re-randomize every run. **No new entity needed — reuse the existing pin mechanism** (`resolve_audience`'s `… ∪ pins`): randomize once, materialize the split as pinned groups, subsequent runs read the pins. **Out of POC — library documentation only:** multivariate testing, more complex test designs, automated winner rollout. **Watch item:** **preheader may become irrelevant** as mail providers replace it with AI-generated summaries — worth confirming before investing in preheader-specific testing. Source: user, 2026-07-31 (AI-layer interview, Cluster 3 Q17).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 236, section "Features", position 33 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
