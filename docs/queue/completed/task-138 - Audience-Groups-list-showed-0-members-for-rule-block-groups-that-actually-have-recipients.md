---
id: TASK-138
title: >-
  Audience Groups list showed "0 members" for rule-block groups that actually
  have recipients
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 500200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** Audience Groups list showed **"0 members" for rule-block groups that actually have recipients** (e.g. system-suggested audiences) — the list counted only manual pins (`AudienceGroupMemberDB`), so a suggested/rule-only group with 0 pins read 0 despite resolving to N recipients. **Fixed 2026-07-26 (same day):** `audience_groups_list` now shows the live resolved count (`len(resolve_audience(...))`); column renamed "Recipients (net)", with a secondary "(N pinned)" only when manual pins exist. Verified live: suggested groups #18/#22 went 0 → 31, #17 shows 17 (13 pinned). Source: user, 2026-07-26.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 505, section "Done", position 2 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
