---
id: TASK-285
title: The React record page marks readiness per channel and machine ready
status: Done
assignee:
  - '@claude'
created_date: '2026-10-05 18:10'
updated_date: '2026-10-05 19:08'
labels:
  - frontend
dependencies:
  - TASK-283
type: feature
ordinal: 200130
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-282 design session (2026-10-05); see [[Channel Readiness - final design pass]]. The React record page (`frontend/src/screens/ContentDetail.tsx`), where the placeholder comment for readiness sits in each channel section (from task-279). Depends on the storage task.

**Each channel section shows:**
- a "Ready for <Channel>" switch;
- who marked it and when;
- the server's warning, when the record can fill no module of that channel ("Marked ready for Push, but Notification text is empty"; for email, "no email module can use it: Hero banner needs Hero headline; image modules need Headline").

A warning informs and never blocks (ADR-174 point 2).

**A "Machine ready" switch** sits next to the status, with a one-line explanation: "may a decision slot pick this without a person choosing it". Only people may change it; the server refuses integrations.

**After any change, re-read the record.** Marking moves no version token (it is a separate table), but the warning and the who/when come from the detail. Keyboard-first: the switches are reachable and operable from the keyboard, with no new shortcut needed.

Tests per screen convention with a stub server, mutation-checked; a live check on a scratch record (memory: live checks on scratch data only).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Each channel section has a Ready switch with who/when and the server's warning; a Machine ready switch sits by the status
- [x] #2 Changes re-read the record; refusals show in place
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first in ContentDetail.test.tsx against a stub server that keeps marks apart from the version (as the real one does) and moves the version on machine ready.
2. resources.ts: useMarkReady (PUT/DELETE readiness) and useSetMachineReady, in the record's write queue (scope composer-content), re-reading the record on settle — after a refusal too.
3. ContentDetail.tsx: ReadyFor in each channel section (not the 'other' group) with who/when and the server's warning; MachineReady next to the status with its one-line meaning; SaveState under each for refusals.
4. Minimal switch indicator CSS so the state is visible; no other styling (layout session later).
5. Mutation-check, client suite, types, contract; live check on scratch records 116 and 117, by keyboard.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Choices made in building (within the design pass): the switch shows what is stored and moves after the re-read, not optimistically; the 'other' field group (fields with no channel) gets no switch; who/when reads 'Marked ready by <who> · <local date-time>'; the warning is a plain paragraph — it informs and never blocks, fields stay editable.
Found live and fixed: a switch disabled while its change saved dropped keyboard focus to the page body, so a keyboard user lost their place after every toggle. Now read-only while pending (RAC isReadOnly), which keeps focus; a test holds the stub's answer to see the pending state and asserts the switch stays enabled and focused.
An older test counted every <label> in the Email section as a field; the switch is a label too, so it now selects field labels only (field order unchanged).
Validation: 9 new tests, failing first; 16 mutants all caught (one survivor — 'machine ready always sent false' — led to the turn-on test). Client 175 passed, tsc clean, contract matches. Live on scratch 116 (keyboard: Space marks Push and Email, unmark, machine ready off/on, focus kept) and 117 (empty: both server warnings shown in place, e.g. 'Marked ready for Push, but Notification title and Notification text are empty'). Both restored: machine ready on, no marks.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The React record page now has a 'Ready for <Channel>' switch in each channel section, showing who marked it, when, and the server's warning, and a 'Machine ready' switch beside the status with its meaning. Every change re-reads the record (machine ready moves the version token, so the next field save stays valid); refusals show in place. Switches stay focused while saving. Verified by 9 new tests, 16 caught mutants, 175 client tests, the contract check, and a keyboard live check on scratch records 116 and 117, both restored.
<!-- SECTION:FINAL_SUMMARY:END -->
