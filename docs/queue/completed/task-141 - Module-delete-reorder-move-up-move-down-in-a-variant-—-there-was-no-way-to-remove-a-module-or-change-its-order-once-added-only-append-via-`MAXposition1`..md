---
id: TASK-141
title: >-
  Module delete + reorder (move up / move down) in a variant — there was no way
  to remove a module or change its order once added (only append via
  `MAX(position)+1`).
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: feature
ordinal: 500500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Feature]** Module **delete** + **reorder** (move up / move down) in a variant — there was no way to remove a module or change its order once added (only append via `MAX(position)+1`). Requested as backend-first (service + API), not just UI. **Done 2026-07-15** — `delete_module` (cascades the module's content overrides, which are meaningless without it; leaves a position gap, which is fine — `(variant_id, position)` only requires uniqueness, not contiguity, and rendering orders by position) and `move_module(direction)` (swaps the position value with the adjacent module via a temporary slot so the unique constraint doesn't trip mid-swap; no-op at top/bottom). REST: `DELETE /campaigns/modules/{id}`, `POST /campaigns/modules/{id}/move?direction=up|down`. Campaign-detail UI got an Actions column (↑ ↓ disabled at the edges, ✕ delete with a confirm). This is the swap-on-reorder behavior the Campaigns Q6 bug (above) flagged as future work. Verified live: move swaps order and no-ops at the ends, bad direction → 400, delete removes the module and cascades both its overrides (active + reverted history), delete of a missing id → 404.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 511, section "Done", position 5 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
