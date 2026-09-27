---
id: TASK-147
title: >-
  No uniqueness constraint on `(variant_id, position)` for `ModuleInstanceDB` —
  duplicate or gapped positions produce ambiguous render order (undefined
  secondary sort stability), and there's no reorder…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 501100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** No uniqueness constraint on `(variant_id, position)` for `ModuleInstanceDB` — duplicate or gapped positions produce ambiguous render order (undefined secondary sort stability), and there's no reordering endpoint for a builder "insert between" UX (`campaigns/service.py:110-146`). Already observed causing real problems in test mode, not just theoretical. Fix: positions should never be entered manually — always auto-generate (e.g. `MAX(position) + 1` within the variant on create). Reordering should swap positions between the two affected modules rather than allow arbitrary/gapped values, so duplicates can never exist. Add a DB-level unique constraint on `(variant_id, position)` as a safety net alongside the application logic. Ranked high — confirmed real-world occurrence, not speculative. Source: [[Interview Prep - Content, Campaigns, Audience]] → Campaigns Q6. **Done 2026-07-12** — auto-generation (`MAX(position)+1`) and the unique constraint are in; the swap-on-reorder behavior remains a future feature since no reordering endpoint exists yet to need it. **Reorder + delete added 2026-07-15** — see the module reorder/delete Done entry below.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 523, section "Done", position 11 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
