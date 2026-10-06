---
id: TASK-297
title: >-
  The React audience editor: rules, hand-added people, paste, delete — with the
  live arithmetic
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-06 19:59'
updated_date: '2026-10-06 20:46'
labels:
  - frontend
dependencies:
  - TASK-295
type: feature
ordinal: 200390
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-293 interview (2026-10-06, with the user); recorded in [[Audience Write Surface - final design pass]] decisions 1, 5, 6, 8, 9, 10 and [[ADR-188 — Audience Rules Are Flat, and May Read Engagement History]]. Third of four build tasks; depends on build 1.

**Build** in `frontend/src/screens/Audiences.tsx` and `AudienceDetail.tsx` (the group's page becomes the editor, no separate edit mode):
- "New audience" on the list (name, description), opening the empty page;
- name and description saving on leaving the field;
- the rules in two sections, **"Who's in"** and **"Leave out"**, with the explanatory line under "Leave out" and the "did not" hint (decision 9); each rule edited in place and saved with **"Save rule"**; language and status chosen from existing values (several allowed), category from `CategoryChoice` with the score (1.0 filled in); "Add a rule";
- the arithmetic (task-213) beside the rules on the chosen channel (first switched-on by default), refreshed after each saved change;
- **hand-added people**: the list with reason, who, when and an exclusion mark; add one with the recipient picker (extract `RecipientChoice` from `frontend/src/screens/Preview.tsx` into a component) and an optional reason; remove one;
- **"Paste people"**: text box, the report, then "Add N";
- **delete** with confirmation, and the 409 shown in place naming the sends;
- **"Suggest from campaign"**, the suggested badge and "Recalculate from campaign" (manual).
Every write states the group's version; "Load their version" on a 409. Layout and keyboard polish stay with their sessions.

Tests per screen convention with a stub server, mutation-checked; a live check on a scratch audience only.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A manager can create an audience and edit its rules and hand-added people, seeing the arithmetic update
- [ ] #2 Paste people, delete (with the used-by refusal) and suggest/recalculate work from the page
- [ ] #3 Writes state the version; a stale one offers Load their version
<!-- AC:END -->
