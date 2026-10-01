---
id: TASK-116
title: The audience-groups list shows a recipient count that is silently email-only.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-10-01 20:54'
labels:
  - backend
  - frontend
dependencies: []
priority: parked
type: bug
ordinal: 206900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🟡 **[Bug] — P3 while the Jinja UI lives, P1 as a lesson for the screen that replaces it. Found 2026-09-27 while closing the `resolve_audience` channel default.** **The audience-groups list shows a recipient count that is silently email-only.** `app/frontend/router.py`'s `audience_groups_list` resolves each group to produce `recipient_count`, and consent is keyed `(recipient, brand, channel, purpose)` — so the number is *"people who consented to email"*, displayed as though it were *"people in this group"*. **A group built for push shows an email number**, and nothing on the screen says so. The call is now channel-explicit rather than relying on a default, so the assumption is visible in code; **the display is still wrong**. **Two things make this worth keeping after the Jinja UI is deleted.** The React audience list will need the same number and faces the same choice — one count per channel, a count plus the channel it is for, or no count at all — and [[Variant Editor - design interview]] question 1.1 already settled the analogous case for variants: **channel grouping is real and cross-channel roll-ups are not meaningful**, because strategies differ by channel. A single blended figure would be the same mistake. Second, it is **an N+1 in a list view**: one `resolve_audience` per group, each of which is several queries, on a project `docs/backlog.md` separately notes has **no scale benchmark at all**. **Do it with the audience screens**, not before — the right answer depends on what the list is for, which the audience cluster of the manager-workflow interview settled and the screen has not yet been built against.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 406, section "Features", position 69 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Dropped 2026-10-01 in the Parked-task ranking, at the user's decision: it concerns the Jinja audience-groups list, a screen ADR-170 retires with the Jinja UI. The underlying rule — no channel-less count on screen (ADR-176 point 5) — carries into the React audience screen, where task-213 (the resolution arithmetic) is ranked.
<!-- SECTION:FINAL_SUMMARY:END -->
