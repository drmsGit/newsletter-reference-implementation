---
id: TASK-396
title: A campaign's status and its delivery's status are told apart
status: To Do
assignee: []
created_date: '2026-10-17 16:13'
labels:
  - frontend
dependencies: []
type: feature
ordinal: 211000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
From the UX audit of 2026-10-17 (docs/design/ux-audit-2026-10-17/FINDINGS.md, UX-19; screenshot screenshots/03-campaigns.jpg beside it). Triaged with the user the same day as a task of its own, because it needs a design choice before it is built; the small fixes from the same audit are TASK-392 items 7 to 21. Campaigns lists Familienherbst, Hüttensaison-Finale and others as draft (the status column, frontend/src/screens/Campaigns.tsx:57) while Monitoring shows the same campaigns as Sent. Both are probably right, as the editing state of the campaign and the outcome of its latest delivery, but nothing says so, and a manager sees one campaign as unfinished in one place and sent in the other. The meaning comes first: check what campaign status means in the backend and the ADRs before changing anything (the audit warns against changing the status logic before confirming its meaning). Then the labels say which state they are, or the list shows both.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 What campaign status and delivery status each mean is written down, with the ADR that governs it
- [ ] #2 The Campaigns list and Monitoring label their status so the two cannot be read as contradicting each other
<!-- AC:END -->
