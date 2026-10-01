---
id: TASK-28
title: >-
  the deliveries screen has no read surface, and the screen inventory marks it
  ✅.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-10-01 20:58'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 102800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — the deliveries screen has no read surface, and the screen inventory marks it ✅.** Measured 2026-09-20 while building Phase 2. Send instances are reachable **only** through `GET /delivery/snapshots/{snapshot_id}/send-instances`, so listing what has been sent means walking campaigns → variants → snapshots → sends client-side — which is precisely what `docs/react-screen-inventory.md`'s own "Things the SPA must not reimplement" forbids. Worse and less obvious: **there is no `GET /delivery/send-instances/{id}` at all**, so a delivery *detail* screen cannot load a send by id either; the only per-send route is `/executions` beneath it. The inventory's "✅ reads exist" is true of the module and false of the screen. **Two routes close it** — a list and a get-by-id over `SendInstanceDB`, both straightforward against the existing service — and they belong with **C8 (planning a send)** rather than before it: Phase 3 already opens this module, one delivery-shaped change is better than two, and the list's filtering and shape should be decided by the screen that reads it. Until then the SPA's navigation omits Deliveries rather than linking to something broken. Source: React client Phase 2, 2026-09-20.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 92, section "Bugs", position 28 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Two routes: GET /delivery/send-instances (brand-scoped, newest first, paged with limit/offset/status) and GET /delivery/send-instances/{id} (404 across brands), whose detail carries sent/failed/excluded, the execution total and exclusions by ADR-163 stage — the gap the Manager Workflow interview asked to explain. SendInstance exposes the columns it was dropping. Built now rather than with C8 because the interview had decided the screen's shape. Four tests, four mutations caught; inventory corrected; 772 pass. The React screen itself and creating a send (C8) remain.
<!-- SECTION:FINAL_SUMMARY:END -->
