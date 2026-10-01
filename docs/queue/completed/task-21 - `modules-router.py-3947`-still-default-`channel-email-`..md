---
id: TASK-21
title: '`modules/router.py:39,47` still default `channel="email"`.'
status: Done
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-10-01 19:54'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 102100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P2. The fail-closed posture has a hole in the layer a hand-crafted request reaches first.** **`modules/router.py:39,47` still default `channel="email"`.** `migrate_0010` went to the trouble of adding a server default, backfilling with it, and then dropping it — precisely so that a caller who forgets a channel FAILS rather than silently creating an email variant, which is fail-open the moment a second channel exists. The model declares no server default either, so both creation paths agree. A route-level default puts the silent email-by-omission straight back. Same shape as the module-picker miss: the guard existed one line away and this call site was overlooked. Source: [[Interview Prep - Channels, Audit]] → A-Q8.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 78, section "Bugs", position 21 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Both module routes now require channel (422 without it). The default's stated reason — an existing contract — protected no caller: nothing in the client, Jinja UI or tests calls these routes. Three tests; the original router fails both refusal tests; 755 pass.
<!-- SECTION:FINAL_SUMMARY:END -->
