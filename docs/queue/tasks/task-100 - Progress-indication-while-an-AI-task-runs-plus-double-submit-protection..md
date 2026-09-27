---
id: TASK-100
title: 'Progress indication while an AI task runs, plus double-submit protection.'
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - frontend
dependencies: []
type: feature
ordinal: 205300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — LOW priority, deferred to the React frontend.** **Progress indication while an AI task runs, plus double-submit protection.** Surfaced 2026-08-02 (user, first live Claude run). The *Suggest subject & preheader* button is a plain server-rendered form POST, so the page just sits there for the several seconds a real model call takes — no spinner, no disabled button, nothing. The user only noticed the request was in flight from the **browser tab's** loading indicator. **Not purely cosmetic:** with no feedback the natural reaction is to click again, and every click is a *paid* generation — so the missing indicator is also a spend bug. Deferred by the user to the final React frontend, where request state is already in hand and this is trivial. **Cheap interim mitigation if the current server-rendered UI lives longer than expected:** disable the button and swap its label on submit — a few lines of inline JS, no architecture involved. Applies to every future Mode-A action, not just this one, so the React implementation should solve it once at the action level rather than per button. Source: user, 2026-08-02.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 281, section "Features", position 53 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
