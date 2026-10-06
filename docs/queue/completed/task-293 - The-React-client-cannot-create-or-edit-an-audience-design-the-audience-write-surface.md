---
id: TASK-293
title: >-
  The React client cannot create or edit an audience: design the audience write
  surface
status: Done
assignee:
  - '@claude'
created_date: '2026-10-06 18:59'
updated_date: '2026-10-06 20:12'
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
- [x] #1 The audience write surface is designed with the user and recorded
- [x] #2 Build tasks are proposed and filed
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Interview held 2026-10-06 with the user, one question at a time (context gathered by a subagent first):
Q1 the group's page is the editor; "New audience" asks name and description; the arithmetic updates after each saved change; channel defaults to the first switched-on one.
Q2 fields: language, status, category interest; values offered from what exists; a category always with a score (1.0, never 0 — the pass extends that to above 0); unknown fields refused. The user: language/status could later extend to CRM attributes.
Q3 flat logic, multi-value fields, no nested groups (the user's Condor example: Beach AND departure airport FRA or BER).
Q4 CRM attributes / related data moved to its own session: task-294 (synced and stored, or pulled when needed); the editor works with today's fields.
Q5 hand-adds: add one with an optional reason, who and when recorded (closes task-217); remove one; no expiry; no "add by criteria" in the editor.
Q6 "Paste people": identifiers or email addresses, any separator, a report first, nobody created, up to 5,000; no CSV wizard.
Q7 engagement in rules: received, opened (the user: include it, the company's call), clicked; a send, a campaign or any; absolute or relative time; "did not" is a leave-out rule, explained once.
Q8 a group a send uses cannot be deleted; an unused one is, audited.
Q9 "Who's in" / "Leave out" wording, no blocklist or suppression words.
Q10 one version for the group, every write audited; "Save rule"; name and description on leaving the field; hand-adds immediate.
Follow-on: "received" = handed to the provider and not bounced (the user). The follow-up send the user cited is not built (ADR-169) and is filed as task-299, with the user's framing (next newsletter, after X days, include rules) and the instruction to check code and interviews first.
Recorded: ADR-188; addenda to ADR-176 and ADR-169; docs/architecture/interview-prep/Audience Write Surface - final design pass.md; playbook 2026-10-06. Build tasks task-295 to task-298; design tasks task-294, task-299.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The React audience editor is designed with the user and recorded: ADR-188 (flat rules with multi-value fields, a category always with a score above 0, engagement — received, opened, clicked — in rules, "did not" as a leave-out), addenda to ADR-176 and ADR-169, and the Audience Write Surface final design pass (the page as the editor, hand-adds with reasons, pasting people, safe delete, one version and audit on every write). Build tasks task-295 to task-298; related data split out as task-294 and the follow-up send as task-299.
<!-- SECTION:FINAL_SUMMARY:END -->
