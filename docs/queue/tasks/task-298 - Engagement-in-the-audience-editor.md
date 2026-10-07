---
id: TASK-298
title: Engagement in the audience editor
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-06 19:59'
updated_date: '2026-10-07 21:09'
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
- [ ] #1 A rule can be given an engagement field (what, which mailing, when) in the editor
- [ ] #2 The did-not hint is shown
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Client tests first (AudienceEditor.test.tsx): add an engagement field to a Who's-in rule (clicked, one send, last N days) with the did-not hint shown in that form and the one-line summary naming it; a campaign with two dates; any send, any time; an existing engagement read, then removed; a leave-out rule's form without the hint; a refused value shown.
2. resources.ts: useSentSends - the brand's sent sends, newest 50 (GET /delivery/send-instances?status=sent).
3. AudienceRules.tsx: an engagement draft (what, which mailing, when) in RuleForm with Add engagement / Remove engagement, written as the server's shape (event; send_instance_id or campaign_id; within_days, more_than_days or from/to); the summary line reads it in words.
4. Mutation check, client suite, build, contract, commit, live check on a scratch audience, finalize.
Design choices noted: one engagement field per rule (as stored); the send choice lists the 50 newest sent sends (no search on that route; an older one is reachable through its campaign); any send means the channel the audience resolves on.
<!-- SECTION:PLAN:END -->
