---
id: TASK-187
title: >-
  Category picker for the decision-slot `candidate_filter.category_ids` (and any
  other category-ID input) — today a manager has to hand-type raw category IDs
  into the config JSON (`{"category_ids": [1,…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 505100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Feature]** Category **picker** for the decision-slot `candidate_filter.category_ids` (and any other category-ID input) — today a manager has to hand-type raw category IDs into the config JSON (`{"category_ids": [1, 2, 3]}`), which nobody will memorize. Replace with a name-based multi-select/lookup (show category names, store IDs) on the decision-slot edit form. Semantics to preserve and surface in the UI: **a non-empty selection whitelists candidates to only those categories; an empty selection = consider *every* category** (confirmed 2026-07-15 — both `top_score` and `recipient_top_score` do `if category_ids: filter(...in_(category_ids))`, so empty/absent means no filter). Builds directly on the just-shipped decision-strategy config-shape manifest (Campaigns Q7, Done 2026-07-15) — the `ConfigField(name="category_ids", type="list[int]")` declaration is exactly what a picker would bind to, and the same friendlier-input treatment should extend to other ID-typed config fields as they appear. Same "make manager input intuitive and mistake-proof" principle as Campaigns Q7; UX polish, not architecture. Source: user follow-up while reviewing the config-shape enforcement, 2026-07-15. **Done — verified built 2026-09-12.** `app/templates/decision_slot_detail.html:123` is the name-based multi-select the item asks for (shows category names, stores IDs, `multiple size="6"`), bound to `candidate_filter.category_ids`, and :128-131 surfaces exactly the semantics this entry required: "Restrict candidate content to these categories" plus **"Select none = consider every category"** — and literally "no need to type IDs". `playbook-strategy.md` §6 already marked Phase 2D ✅; this entry was stale, and the staleness had propagated into `BETA-SCOPE.md`'s out-of-scope list. Found by the backlog-sequencer pass, 2026-09-12; no completion date was recorded at the time it was built, so the date above is the verification date, not the build date.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 605, section "Done", position 51 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
