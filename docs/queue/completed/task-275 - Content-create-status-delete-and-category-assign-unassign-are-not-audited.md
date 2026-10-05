---
id: TASK-275
title: 'Content create, status, delete and category assign/unassign are not audited'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-04 18:24'
updated_date: '2026-10-05 07:02'
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
- [x] #1 Create, status change, delete (including force), category assign, score change and unassign each write an audit event on both planes, naming the record and what changed
- [x] #2 Tests prove each event is written
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-05.
- Five new audit actions (backend/app/audit/service.py): content.created, content.status_changed (from/to, recorded only when it changes), content.deleted (title, forced, category_assignments and versions counts, modules_unbound ids), content.category_assigned and content.category_unassigned (category id and name, score; the score at removal is the history).
- Both planes record them through record_from_request, so the actor is the person on Jinja and the integration on JSON.
- Service contracts changed to carry what the entry needs: delete_content_record returns a summary dict or None (was True/False); delete_category_assignment returns the removed assignment's summary or None (was bool). New helpers assignment_summary, edited_fields and edit_snapshot. Callers use truthiness, unchanged; test_jinja_brand_crossings updated to the new return values.
- The edit discrepancy the entry asked about: both were wrong. The API listed every key sent (unchanged ones too) and Jinja every key on the record. Both now record the fields the edit changed (title, description, content keys), with empty treated as absent, because the Jinja form posts every email field and the merge stores "" where there was no key.
- Score-change auditing is not here: that route does not exist yet. task-278 already requires it to be audited from the start.
- Tests: tests/test_content_audit.py (15: each write per plane, and the detail of a forced delete, the status from/to and repeat, the unassign score, and changed-fields-only per plane). Mutation-checked against 15 mutants, each caught. Full backend suite 1263 passed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Content create, status, delete, category assign and unassign are audited on both planes with their actor and a useful detail (from/to, what a forced delete removed, the score). Edit entries now name only the fields that changed. Verified by 15 tests mutation-checked against 15 mutants and the full backend suite (1263). The score-change route is audited when task-278 builds it.
<!-- SECTION:FINAL_SUMMARY:END -->
