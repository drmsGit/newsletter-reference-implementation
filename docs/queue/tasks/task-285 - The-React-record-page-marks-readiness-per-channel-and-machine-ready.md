---
id: TASK-285
title: The React record page marks readiness per channel and machine ready
status: To Do
assignee: []
created_date: '2026-10-05 18:10'
updated_date: '2026-10-05 18:10'
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
- [ ] #1 Each channel section has a Ready switch with who/when and the server's warning; a Machine ready switch sits by the status
- [ ] #2 Changes re-read the record; refusals show in place
<!-- AC:END -->
