---
id: TASK-299
title: >-
  Follow-up sends: the next newsletter, after X days, for the people chosen with
  audience rules — design pass before building
status: To Do
assignee: []
created_date: '2026-10-06 20:11'
labels:
  - backend
  - frontend
  - needs-adr
dependencies: []
type: decision
ordinal: 305360
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Follow-up sends: the next send for the people a previous one reached, after a delay, chosen with audience rules.** Filed 2026-10-06 at the user's request during the task-293 interview. The user, verbatim: "check code and interviews before building as the followup feature combines the audience 'builder' and a next send. So not just 'send reminder' but -> select next newsletter, pick after x days, pick include rules".

**What the user means** (to confirm in the design session, not to assume): a follow-up is not only a "did not open" reminder. A manager picks **the next newsletter** (a variant or campaign), **after X days**, and **which people** — with the same rule builder as audiences ([[ADR-188 — Audience Rules Are Flat, and May Read Engagement History]]: received / opened / clicked, a send, a campaign or any, a time window; "did not" as a leave-out rule).

**What is already decided:** [[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]] — flows are sequenced variants with per-variant followup conditions ("if opened, then variant X; if not, then Y"), a followup is a row (point 3), conditions speak the audience rule vocabulary (point 4), a cycle is approved once at setup and corrected by toggling followups (point 6); its 2026-10-06 addendum: the vocabulary has no negated field, so "did not open" is either an "opened" condition with an else branch or "received minus opened" — left to this design pass. ADR-169's Notes leave open whether a followup's offset is relative to the anchor or to the previous step.

**Before building — check, as the user asked:**
- the code: nothing named followup exists in `backend/app/` or `frontend/src/` (checked 2026-10-06); the scheduling mechanism the Manager Workflow interview decided for sends (Cluster 5 Q3: "both, and one mechanism covers both — a schedule") and whatever of it is built;
- the interviews: [[Manager Workflow - design interview]] Cluster 5 (sends, schedule, always recalculate), [[Omni-Channel - design interview]] (cross-channel follow-up, around lines 447 and 837), [[Variant Editor - design interview]] (around line 120, follow-up flows as Salesforce-only work today), and ADR-169's source;
- the audience editor (task-295 to task-298) this builds on.

**Questions for the session** (a starting list): a followup as part of a campaign's sequence (ADR-169) or as a send of its own; how "after X days" anchors (the previous send, or the first); how the rule builder is reused (the same component and criteria, ADR-169 point 4); approval once at setup versus per send; what the manager sees before it fires (the arithmetic, as of now).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The follow-up send is designed with the user, after checking the code and the interviews, and recorded (ADR-169 addendum or final design pass)
- [ ] #2 Build tasks are filed
<!-- AC:END -->
