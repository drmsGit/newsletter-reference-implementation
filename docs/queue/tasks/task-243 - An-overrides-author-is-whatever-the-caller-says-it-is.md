---
id: TASK-243
title: An override's author is whatever the caller says it is
status: To Do
assignee: []
created_date: '2026-10-02 20:01'
labels:
  - backend
dependencies: []
priority: p2
type: bug
ordinal: 104600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug, integrity]** Found 2026-10-02 while building task-113, which made duplication attribute carried overrides to the authenticated person duplicating (`override_author` in `backend/app/campaigns/duplication.py`). The ordinary paths that create an override do not do the same:

- **JSON:** `POST /overrides/` (`backend/app/overrides/router.py:18-23`) takes `overridden_by` from the request body (`ContentOverrideCreate.overridden_by: str`, `backend/app/overrides/models.py:15`), and `create_content_override` (`backend/app/overrides/service.py:89`) stores it unchecked. A caller holding `overrides.manage` can therefore record an override in anyone's name, or in no real person's.
- **Jinja:** the campaign page's override form hardcodes `overridden_by="manager@example.com"` (`backend/app/frontend/router.py:1663`), so every override made through the UI names the same placeholder, whoever made it.

Why it matters: ADR-040/041 make the override the trust loop's record of a human deviating from the system's pick, and `outcome_delta` (task-114) is meant to judge that deviation later. A record of *who* deviated that the deviator types themselves cannot answer "who did this". It is the same class of defect gate 3 closed for `POST /recipients/` (consent set through the payload, `docs/business/LAUNCH-GATES.md`): a fact the server knows, taken from the client instead.

The server already knows the answer: `request_principal(request)` on the JSON plane, `user_for_token` on Jinja. task-113's `override_author(principal)` is the existing formatter (a user's email, `integration:<name>`, a fixed label when access control is off).

Open for the worker, not decided here: whether `overridden_by` should stay a string or become an actor reference (type + id, as `audit_events` stores actors, ADR-153). Existing rows written as `manager@example.com` cannot be re-attributed; say so rather than guess.

Related: task-113 (done — duplication's half), task-114 (outcome_delta), ADR-040, ADR-041, ADR-150, ADR-153.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An override created over JSON records the authenticated caller as its author, whatever the body says
- [ ] #2 An override created through the Jinja page records the signed-in user, not a placeholder
- [ ] #3 The request model no longer lets a client set the author, or the API documentation states it is ignored
- [ ] #4 A test pins each path, and is mutation-checked
- [ ] #5 What happens to rows already written with the placeholder author is stated in the task notes
<!-- AC:END -->
