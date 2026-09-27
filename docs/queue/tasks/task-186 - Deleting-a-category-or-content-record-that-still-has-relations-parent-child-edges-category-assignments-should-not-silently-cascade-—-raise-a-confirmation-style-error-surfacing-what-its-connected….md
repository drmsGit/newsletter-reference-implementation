---
id: TASK-186
title: >-
  Deleting a category or content record that still has relations (parent/child
  edges, category assignments) should not silently cascade — raise a
  confirmation-style error surfacing what it's connected…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 505000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** Deleting a category or content record that still has relations (parent/child edges, category assignments) should not silently cascade — raise a confirmation-style error surfacing what it's connected to ("related to N parent(s) / M child(ren) — delete anyway?") so a manager can re-parent/re-assign first if needed. Applies once delete endpoints for content records/categories are built (none exist yet); pairs with the FK/cascade design from Content Q5. Does not cover the harder historical-data question below — see the 📋 Needs ADR item. Source: [[Interview Prep - Content, Campaigns, Audience]] → Content Q6. **Done 2026-07-12** — built `DELETE /content/{id}` and `DELETE /content/categories/{id}` (they didn't exist before this). Split relations into two tiers: decision-resolution/override history is a **hard block**, never force-deletable (consistent with the "never hard-delete anything with historical usage" leaning already in the data-lifecycle Needs-ADR item below — this doesn't build the archive mechanism itself, just refuses to destroy history in the meantime); category assignments, versions, and module instances are **soft/reassignable** — without `force`, a 409 lists counts and asks "delete anyway?"; with `force=true`, they cascade-delete (module instances get `content_record_id` cleared rather than being deleted, so campaign structure survives). Added matching UI: a Delete button on both detail pages, and a "Yes, delete anyway" button that appears once the soft-relations error is shown. Verified live end-to-end via the API (hard block, soft block + counts, force bypass, cascade correctness) and via the actual HTML form-post delete flow.

---
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 601, section "Done", position 50 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
