---
id: TASK-156
title: >-
  `create_snapshot_for_variant` (`snapshots/service.py:96-138`) derives its HTML
  and its `render_context` metadata from two independent, sequential
  `DecisionResolutionDB` queries (inside `render_varian…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
  - frontend
dependencies: []
type: bug
ordinal: 502000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `create_snapshot_for_variant` (`snapshots/service.py:96-138`) derives its HTML and its `render_context` metadata from two independent, sequential `DecisionResolutionDB` queries (inside `render_variant_html` and `build_render_context` respectively) instead of one shared resolution pass — if a new decision resolution is inserted for the same slot+recipient in the narrow window between the two calls, the snapshot's metadata can describe different content than what's actually baked into the HTML file, undermining ADR-062's audit-trust guarantee. Fix: derive both from one resolution pass — have `render_variant_html` return/expose the resolution details it used, and have `build_render_context` reuse them instead of re-querying. Source: [[Interview Prep - Snapshots, Rendering, Email Modules]] → Snapshots Q3. **Done 2026-07-12** — `render_variant_html(..., collect_resolutions=True)` now returns the `DecisionResolutionDB` rows it actually used per module; `create_snapshot_for_variant` passes them straight into `build_render_context` instead of it re-querying. Also removed the dead throwaway `render_context` assignment in the same function (Snapshots Q1, trivial, fixed in passing). Verified live: the fix even caught a pre-existing bug — the seeded `content_card` module type has no matching email-module template and never actually renders, and the render_context now correctly reports `"no_resolution"` for it instead of the old code's misleading "resolved" (which cited a resolution that was never actually used in the HTML).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 541, section "Done", position 20 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
