---
id: TASK-298
title: Engagement in the audience editor
status: Done
assignee:
  - '@claude'
created_date: '2026-10-06 19:59'
updated_date: '2026-10-07 21:15'
labels:
  - frontend
dependencies:
  - TASK-296
  - TASK-297
  - TASK-300
type: feature
ordinal: 200391
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-293 interview (2026-10-06, with the user); [[ADR-188 — Audience Rules Are Flat, and May Read Engagement History]] points 4 and 5. Fourth of four build tasks; depends on builds 2 and 3.

**Build** in the rule editor of build 3: an engagement field — what (received, opened, clicked), which mailing (a send chosen from the brand's sends, a campaign, or any send), when (between two dates, within the last N days, more than N days ago) — and the "did not" hint shown where an engagement field is used in "Who's in" ("To reach people who did not click, include who received it and leave out who clicked").

Tests per screen convention, mutation-checked; a live check on a scratch audience.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A rule can be given an engagement field (what, which mailing, when) in the editor
- [x] #2 The did-not hint is shown
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Client tests first (AudienceEditor.test.tsx): add an engagement field to a Who's-in rule (clicked, one send, last N days) with the did-not hint shown in that form and the one-line summary naming it; a campaign with two dates; any send, any time; an existing engagement read, then removed; a leave-out rule's form without the hint; a refused value shown.
2. resources.ts: useSentSends - the brand's sent sends, newest 50 (GET /delivery/send-instances?status=sent).
3. AudienceRules.tsx: an engagement draft (what, which mailing, when) in RuleForm with Add engagement / Remove engagement, written as the server's shape (event; send_instance_id or campaign_id; within_days, more_than_days or from/to); the summary line reads it in words.
4. Mutation check, client suite, build, contract, commit, live check on a scratch audience, finalize.
Design choices noted: one engagement field per rule (as stored); the send choice lists the 50 newest sent sends (no search on that route; an older one is reachable through its campaign); any send means the channel the audience resolves on.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-07, commit d7d7473.

Client only; the server shape is task-296's. frontend/src/screens/AudienceEngagement.tsx holds the field: What happened (Received it, Opened it, Clicked in it), Which mailing (Any send - "counts any send on the channel this audience is sent on"; Any send of a campaign; One send), When (Any time, In the last N days, More than N days ago, Between two dates), Remove engagement, and the did-not hint inside a Who's-in rule's form. Draft and stored shape convert both ways (engagementDraftOf, engagementOf); a value left out is sent as it is and the server refuses it by name. The one-line view reads it in words ("Clicked in Spring send in the last 30 days", "Received a send of Spring edition between ..."). frontend/src/api/resources.ts useSentSends: the brand's sent sends, newest 50.

Design choices taken in the final pass (within ADR-188 points 4-5, not asked): one engagement field per rule, as the server stores it - several mailings in one field ("clicked A or B") is open under point 1 and not built; the send choice lists the 50 newest sent sends because the route has no search - an older send is reachable through its campaign, and a stored older send still shows as "send #id"; "any send" is the channel the audience resolves on.

Tests: AudienceEditor.test.tsx +5 (27); 18 mutants, all killed. Client suite 223, build and contract clean.

Live check, scratch audience only (zz-scratch task-298, deleted): Who's in "received Edition 2 (sent by the seed)" matched 8; Leave out "clicked in Demo send" removed 6, leaving demo-001 and demo-004 - recomputed directly from delivery_executions and engagement_events: the same two. The leave-out form showed no hint of its own; the Who's-in form did.

For the keyboard and layout sessions: choosing an option in one of these selects can scroll the page, so the controls move under the pointer (seen in the pane on 2026-10-07).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A rule can now say what people did with a mailing: received, opened or clicked; any send on the audience's channel, any send of a campaign, or one send; any time, the last N days, more than N days ago, or between two dates. A Who's-in rule with one shows the did-not hint, and the rule's one line reads it in words. Verified by 5 new editor tests (18 mutants killed), the client suite, build and contract, and a live reminder audience (received Edition 2, leave out clicked Demo send) whose result matched the delivery tables exactly.
<!-- SECTION:FINAL_SUMMARY:END -->
