---
id: TASK-17
title: >-
  `campaign_detail` has no `campaign is None` guard, so switching brand while
  viewing a campaign gives a black-screen internal error.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
  - frontend
dependencies: []
priority: p1
type: bug
ordinal: 101700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — P1, a 500 on an ordinary click.** **`campaign_detail` has no `campaign is None` guard, so switching brand while viewing a campaign gives a black-screen internal error.** `app/frontend/router.py:609` scopes the query to `working_brand_id(...)` and then hands the result to `campaign_detail.html`, which reads `{{ campaign.name }}` unguarded. Before brand scoping the row could not be missing — the id came from a list the caller had just been shown — so scoping made absence reachable and nothing was added to meet it. **This is the exact defect already fixed in `content_detail` on 2026-09-15, in the sibling route that was missed**; the fix there is the template to copy, including the reasoning that another brand's campaign must be indistinguishable from one that does not exist. Worth sweeping the other detail-by-id routes for the same shape in the same pass (`decision_slot_detail`, `delivery_detail`, `audience_group_detail`, `category_detail`, `recipient_detail`) rather than fixing one and waiting for the next report. Source: user, 2026-09-16. **Done 2026-09-17.** The sweep was worth doing and also smaller than expected: probing every detail-by-id route with a nonexistent id found **two** crashes, not five. `campaign_detail` was the reported one; **`recipient_detail` was a second, unreported 500** on any mistyped id — not a brand case at all, since recipients carry no brand, but the same missing guard. `categories`, `decisions/slots` and `deliveries/send-instances` already answer 200, and `audience-groups` redirects (silently, which is acceptable). `/ui/recipients` had to learn to accept and render `?error=` first — the same silent-drop defect found on `/ui/content` the day before.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 70, section "Bugs", position 17 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
