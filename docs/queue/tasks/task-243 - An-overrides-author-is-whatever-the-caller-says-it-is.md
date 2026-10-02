---
id: TASK-243
title: An override's author is whatever the caller says it is
status: Done
assignee:
  - '@claude'
created_date: '2026-10-02 20:01'
updated_date: '2026-10-02 20:06'
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
- [x] #1 An override created over JSON records the authenticated caller as its author, whatever the body says
- [x] #2 An override created through the Jinja page records the signed-in user, not a placeholder
- [x] #3 The request model no longer lets a client set the author, or the API documentation states it is ignored
- [x] #4 A test pins each path, and is mutation-checked
- [x] #5 What happens to rows already written with the placeholder author is stated in the task notes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-02. Decided by the user: overridden_by stays text, filled by the server (no actor-reference columns; audit_events keeps the id-based record, ADR-153). actor_label(principal) now lives in `backend/app/auth/service.py` (moved from duplication.py, which imports it). ContentOverrideCreate has no author field; an old body that still sends overridden_by is ignored, not refused, and the docstring states this. create_content_override takes a required author. JSON: actor_label(request_principal(request)), `backend/app/overrides/router.py`. Jinja: actor_label(user_for_token(...)), `backend/app/frontend/router.py`. FOUND WHILE FIXING: the Jinja override form had raised TypeError since 2026-09-20 (395f8be, ADR-172 stage 6 made brand_id required), so every 'add override' from the UI returned 500 and wrote nothing; nothing tested the route. Fixed in the same call, and the Jinja test is also its regression. Existing rows: the dev DB holds no override rows (counted 2026-10-02), so none needed re-attributing. Elsewhere, a row written with the placeholder cannot be traced to a person and is left as it is. The seed SQL files (`backend/scripts/reset_all_data.sql`, `seed_override_events.sql`) still write authors directly, which is seed data, not a request path. Tests: 2 in TestTheAuthorIsTheCaller (`backend/tests/test_overrides.py`), 4 mutants caught, including restoring the body field as the author. Suite 1011 passed, rc=0; frontend 35.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
An override's author is now always the authenticated caller (a user's email, or integration:<name>), on JSON and on the Jinja page. The request no longer carries an author field. This also fixes the Jinja override form, which had crashed since 2026-09-20. Verified: 2 tests, 4 mutants caught, suite 1011 passed.
<!-- SECTION:FINAL_SUMMARY:END -->
