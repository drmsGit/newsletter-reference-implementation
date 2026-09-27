---
id: TASK-36
title: >-
  The brand switcher returns you to the URL you were on, which belongs to the
  brand you just left.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
  - frontend
dependencies: []
priority: p2
type: bug
ordinal: 103600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — P2, and partly a design call.** **The brand switcher returns you to the URL you were on, which belongs to the brand you just left.** `switch_brand` redirects to `safe_next(next)` (`app/frontend/router.py:95`), and `next` is whatever detail page you were looking at. On a content record that produces a red *"That content record does not exist in this brand"* — technically accurate, but the user did nothing wrong and the message accuses them of following a dead link. On a campaign it produces the 500 above. **The switch itself is correct; the landing is not.** Direction to decide before coding: when the current page is a detail-by-id route, a brand switch should land on that section's **collection** (`/ui/content`, `/ui/campaigns`) rather than on a stale id — the section is what the user was doing, the id was only where they happened to be. Fixing the 500 alone would leave this as a silent redirect to a red banner. Source: user, 2026-09-16. **Done 2026-09-17** — `SWITCH_LANDINGS`, a table next to `switch_brand`, for the same reason `WRITE_POLICY` is a table: the nested routes do not follow a strippable pattern (`/ui/decisions/slots/{id}` would reduce to a page that does not exist). **Recipients and categories are deliberately excluded** — the row survives the switch because it carries no brand, and what changes is the consent shown against it, which is exactly what someone switching brand there wants to see. The rewrite is applied unconditionally rather than only on an accepted switch, so the response still cannot differ by outcome. Verified live: sitting on a content record or a campaign in brand A and switching to brand B now lands on that section's list with no banner.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 108, section "Bugs", position 36 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
