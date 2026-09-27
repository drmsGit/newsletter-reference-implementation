---
id: TASK-37
title: >-
  `campaign_detail.html:72` labels a variant with its global row id — "Variant
  981 — Variant A".
status: Done
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - frontend
dependencies: []
priority: p3
type: bug
ordinal: 103700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — P3, cosmetic but actively misleading.** **`campaign_detail.html:72` labels a variant with its global row id — "Variant 981 — Variant A".** That number is a database sequence, not a count: it reads as *the 981st variant* to anyone looking at a system with a handful of campaigns, and it climbs every time anybody tests anything. The user's proposal is to show the **campaign id** there instead (or, once the channel work lands, the email id) — the identifier the manager actually has a use for, since it is what appears in the URL and in a support conversation. Check the same pattern in the other detail headers before changing just this one. Source: user, 2026-09-16. **Partly done 2026-09-17 — the misleading NUMBER is gone, the NOUN turned out to be a bigger question and is parked.** The label was first changed to `Email {{ campaign.id }}`, and the user corrected it the same day on two counts. First, **a campaign id is not an email id**: [[ADR-160 — Channel Model and Composition]] point 4 has one campaign carry email, push and social variants, so "Email {campaign id}" becomes a false statement about an asset that is not an email. Second, and sharper, **`Campaign 1048 — Variant A` is accurate and less useful** — it drops the one thing the manager needs from that row, which is that this is the email. It now reads `Campaign {{ campaign.id }} — {{ variant.name }}` as a holding position only. The other `#{{ x.id }}` labels were checked and left alone: on campaigns, modules, executions and recipients the id *is* the reference someone would quote, which is exactly what a variant id is not. **See the identifier item at the top of Features — and note it is blocked on code, not only on taste.**
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 110, section "Bugs", position 37 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
