---
id: TASK-100
title: 'Progress indication while an AI task runs, plus double-submit protection.'
status: Done
assignee:
  - '@claude'
created_date: '2026-09-27 13:57'
updated_date: '2026-10-16 18:39'
labels:
  - frontend
dependencies: []
type: feature
ordinal: 200750
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — LOW priority, deferred to the React frontend.** **Progress indication while an AI task runs, plus double-submit protection.** Surfaced 2026-08-02 (user, first live Claude run). The *Suggest subject & preheader* button is a plain server-rendered form POST, so the page just sits there for the several seconds a real model call takes — no spinner, no disabled button, nothing. The user only noticed the request was in flight from the **browser tab's** loading indicator. **Not purely cosmetic:** with no feedback the natural reaction is to click again, and every click is a *paid* generation — so the missing indicator is also a spend bug. Deferred by the user to the final React frontend, where request state is already in hand and this is trivial. **Cheap interim mitigation if the current server-rendered UI lives longer than expected:** disable the button and swap its label on submit — a few lines of inline JS, no architecture involved. Applies to every future Mode-A action, not just this one, so the React implementation should solve it once at the action level rather than per button. Source: user, 2026-08-02.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. One AIButton component (frontend/src/components/AIButton.tsx) for every model call: React Aria Button with isPending, so presses are ignored while focus stays; reads Asking the model… and, after 2 s, a running seconds count (aria-hidden, so the accessible name does not change every second); a polite live region says it once when the call starts. 2. SubjectSuggestions (task-367) uses it; task-368 to task-370 will. 3. Tests first (AIButton.test.tsx with fake timers; the editor test asserts one POST under repeated presses), mutation-checked. 4. Decided 2026-10-16 with the user: label plus seconds, no cancel (tokens are spent either way); the server-side guard against two runs at once (two tabs, a script) is filed as its own backend task, not built here; no interim JS on the Jinja page.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 281, section "Features", position 53 in that section (top = do next). The description is the original entry, verbatim.

2026-10-11, the user set the November 2026 presentations as the focus (docs/business/PRESENTATIONS-2026-11.md): wanted with the AI abilities the demo shows (task-367 to task-370), so a multi-second AI call never looks broken on stage.

Built 2026-10-16 (7ba05a1). frontend/src/components/AIButton.tsx: React Aria Button with isPending (presses ignored, focus kept, aria-disabled), label Asking the model… plus an aria-hidden seconds count from 2 s, counted by a child mounted only while pending so each call starts at zero; a VisuallyHidden status line says Asking the model… once. SubjectSuggestions (task-367) uses it; tasks 368 to 370 carry a note to. Tests: AIButton.test.tsx (3, fake timers) plus the editor test asserting one POST under a repeated press; 6 mutations, all killed. vitest, tsc, eslint (no new warnings), build and CI green. Live check on scratch variant 23 with the page fetch stood in for the suggest call (5 s delay, a 409 answer; no model called, nothing written): the button read Asking the model… 3 s, kept focus, a second press sent nothing (one request), then it returned to Suggest with AI and showed the refusal. Not done, by decision: no cancel; no interim JS on the Jinja page; the server-side guard against two concurrent runs filed as task-387.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
One AIButton for every model call: while a call runs it ignores presses but keeps focus, reads Asking the model… with a seconds count after 2 s, and tells screen readers once. Used by the subject suggestions; tasks 368 to 370 will reuse it. Verified by component and editor tests (mutation-checked), CI, and a live check with a stood-in call. Server-side guard filed as task-387.
<!-- SECTION:FINAL_SUMMARY:END -->
