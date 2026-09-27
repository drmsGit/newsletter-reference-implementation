---
id: TASK-144
title: >-
  Decision strategies should declare their expected
  `candidate_filter`/`strategy_config` shape (similar to how email module
  templates already declare a `variables` manifest, `email_modules/registry.py`…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 500800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Feature]** Decision strategies should declare their expected `candidate_filter`/`strategy_config` shape (similar to how email module templates already declare a `variables` manifest, `email_modules/registry.py`), and the UI/API should enforce it: once a manager picks a `decision_strategy` on a decision slot, the config/filter **structure** locks to that strategy's declared shape — only values are editable, not structure — and switching strategies re-derives the structure for the new one. Fixes `update_decision_slot` (`campaigns/service.py:149-164`) currently accepting any shape for any strategy, only failing (or previously crashing) at resolution time. Principle: anything touching human/manager input should be as intuitive and mistake-proof as possible. Ties into the existing decision-strategy plugin contract hardening (commit cf4f745, Phase 1A). Source: [[Interview Prep - Content, Campaigns, Audience]] → Campaigns Q7. **Done 2026-07-15** — `StrategyMeta` now carries a declarative manifest (`candidate_filter_fields`/`config_fields`, each a `ConfigField` with name/type/required/default/description), mirroring the module `variables` manifest. `top_score` declares `candidate_filter.category_ids` + no config; `recipient_top_score` adds `content_score_weight`/`preference_score_weight`. A `normalize_slot_config` helper (in `strategies/base.py`) validates + normalizes at **both** slot create and update: unknown keys rejected, defaults filled in (so the structure is re-derived when a strategy is chosen/switched), types checked. Surfaced as a 400 on the API and an error banner on the decision-slot UI (which also shows the allowed keys per strategy and no longer mutates the slot on a rejected edit). Verified live: valid config accepted with `preference_score_weight` auto-filled; unknown key, a config key on config-less `top_score`, and a wrong-typed `category_ids` all rejected with clear messages via API and UI; a rejected UI edit left the slot's stored config untouched.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 517, section "Done", position 8 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
