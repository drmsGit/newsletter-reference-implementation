---
id: TASK-293
title: >-
  The React client cannot create or edit an audience: design the audience write
  surface
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-06 18:59'
updated_date: '2026-10-06 19:04'
labels:
  - frontend
  - backend
  - needs-adr
dependencies: []
type: decision
ordinal: 200387
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The React client cannot write an audience.** Raised by the user on 2026-10-06 while task-292 was being started: "the whole 'edit' audience part is missing yet (creating new audiences, using filters etc)". The same gap the content screens had before task-274 ("did we skip the edit part in content?"), and it gets the same treatment: a design interview, one question at a time, before any build.

**What the React client has today** (`frontend/src/screens/Audiences.tsx`, `AudienceDetail.tsx`): a paged list of groups and one group's reach per channel — the arithmetic (task-213), reachable count, a sample and a search. Nothing writes.

**What the server already offers over JSON** (`backend/app/audience/router.py`): create a group (`POST /api/audience-groups/`), rename or describe it (`PATCH /{id}`), delete it (`DELETE /{id}`); add and remove a hand-picked member (`POST`/`DELETE /{id}/members/{recipient_id}`) and bulk-add by criteria (`POST /{id}/members`); add, change and remove rule blocks — include or exclude, by language, status, preference category and minimum score (`POST`/`PATCH`/`DELETE /{id}/blocks...`); recalculate; and the content-driven suggestion routes (around :332 and :357). The Jinja pages (`backend/app/frontend/router.py`, around :3117-3417) do all of this as forms.

**Questions the interview should settle** (a starting list, not decisions):
- the shape of the editor: blocks as a list beside the live arithmetic (task-213), so every change shows its effect per channel;
- which criteria a manager composes, and how a preference-category block is chosen (the category hierarchy the content screens use);
- hand-picked members: search and add (the recipient lookup task-292 builds), remove — and task-107 (nothing removes a member, a membership cannot expire) and task-217 (membership records no reason);
- the content-driven suggestion (system-proposed blocks for a campaign): offered here, in the campaign, or both;
- delete versus keep: a group used by a planned or sent send;
- the version token and audit on every write (ADR-180 point 2, ADR-153), as on the composer and the content screens — to be verified for these routes;
- how exclusion segments relate to suppression (task-231 is blocked on that model).

**Records to read first:** [[ADR-176 — A Negative Decision Outranks a Positive One]] (precedence, per channel), [[ADR-093 — Audience Intelligence Is Derived, Not Authoritative]], [[ADR-163 — Per-Channel Consent and Addressability]] (and its 2026-10-06 addendum: counted, never listed), the Manager Workflow interview Cluster 4.

Produces: decisions recorded (ADR addenda or a final design pass, like [[Content Write Surface - final design pass]]) and proposed build tasks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The audience write surface is designed with the user and recorded
- [ ] #2 Build tasks are proposed and filed
<!-- AC:END -->
