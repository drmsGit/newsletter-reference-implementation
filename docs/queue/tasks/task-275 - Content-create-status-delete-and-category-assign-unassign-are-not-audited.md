---
id: TASK-275
title: 'Content create, status, delete and category assign/unassign are not audited'
status: To Do
assignee: []
created_date: '2026-10-04 18:24'
labels:
  - backend
dependencies: []
type: bug
ordinal: 104600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found 2026-10-04 by the task-274 design session (the content write surface), verified against the code that day. Decided with the user: filed as a bug ahead of the build tasks, the D3 pattern of the campaign write surface.

[[ADR-153 — Audit and Accountability]] point 4 makes writes the floor of what is audited. Content writes are audited unevenly. The API audits `content.updated` (PATCH and PUT), `content.published` and `content.duplicated` (`backend/app/audit/service.py:52`, `:74-75`). These write nothing to the audit log, on either plane:
- create: `create_content_record` (`backend/app/content/router.py:295`) and Jinja `content_create` (`backend/app/frontend/router.py:2132`);
- status: `set_content_record_status` (`router.py:252`) and Jinja `content_set_status` (`frontend/router.py:2087`);
- delete: `delete_content_record_by_id` (`router.py:269`, including `force`, which deletes assignments and versions and unbinds modules) and Jinja `content_delete` (`frontend/router.py:2107`);
- category assign: `assign_category` (`router.py:333`) and Jinja `content_assign_category` (`frontend/router.py:2354`);
- category unassign: `delete_content_assignment` (`router.py:553`) and Jinja `content_category_delete` (`frontend/router.py:1151`).

Category assignments matter most here. They feed slot ranking and every recipient's interest profile ([[ADR-080 — Human-governed Taxonomy Before AI Selection]]: humans define the scoring), and since the 2026-10-04 addendum to ADR-080 a score can also be changed in place. That new route must be audited from the start.

A machine integration holding `content.manage` can make every one of these writes; it is an integration principal under [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]]. So "who did this" is not only a person's question.

Also noted, smaller: the Jinja edit audits `content.updated` with every merged key, while the API audits only the keys sent (`router.py:158-164`). One of the two is wrong; say which in the fix.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Create, status change, delete (including force), category assign, score change and unassign each write an audit event on both planes, naming the record and what changed
- [ ] #2 Tests prove each event is written
<!-- AC:END -->
