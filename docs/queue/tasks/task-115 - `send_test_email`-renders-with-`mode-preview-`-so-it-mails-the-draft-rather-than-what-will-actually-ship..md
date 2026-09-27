---
id: TASK-115
title: >-
  `send_test_email` renders with `mode="preview"`, so it mails the draft rather
  than what will actually ship.
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 206800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — DONE 2026-09-27. A test send shows the one thing it exists to not show. Found 2026-09-26, [[Variant Editor - design interview]] question 4.3.** **`send_test_email` renders with `mode="preview"`, so it mails the draft rather than what will actually ship.** `backend/app/delivery/service.py:519`. `RenderMode` decides which content the renderer reads: **preview** takes the live, mutable `ContentRecordDB.content` — draft edits appear immediately — while **send** takes the latest frozen `ContentVersionDB` and raises `UnpublishedContentError` if none exists. A test send is the one action whose entire purpose is *"show me what recipients will get"*, and it currently shows the opposite: a manager edits a headline, sends a test, sees the new text, and the real send ships the last published version. **Silently**, because a version exists — the refusal only fires when *no* version does. **Interview question 4.3 settled the intended behaviour:** *"if it comes to test sends they should show what actually will be sent in that moment (so if there's a drift, there's a drift) so a manager will notice this"*. A preview is allowed to be a sketch; a test send is not. **The fix is one argument, and the care is in what it exposes:** switching to `mode="send"` means unpublished content now raises where it previously rendered, and this function holds a deliberate rule that **a render failure never blocks the send** — so the refusal needs to become a visible result rather than being swallowed into an email with no body. **Also worth noting the same call passes `recipient_id`**, so a test send resolves decision slots for a real person and therefore shares question 4.2's finding: it reads existing resolutions and falls back silently to the generic one.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 404, section "Features", position 68 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
