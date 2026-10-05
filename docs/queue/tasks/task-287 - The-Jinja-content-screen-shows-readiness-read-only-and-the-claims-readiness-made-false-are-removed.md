---
id: TASK-287
title: >-
  The Jinja content screen shows readiness read-only, and the claims readiness
  made false are removed
status: To Do
assignee: []
created_date: '2026-10-05 18:10'
updated_date: '2026-10-05 18:10'
labels:
  - backend
dependencies:
  - TASK-283
type: chore
ordinal: 200145
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decided in the task-282 design session (2026-10-05): the Jinja content screen shows readiness read-only, and marking happens in the React client (the ADR-174 addendum 2026-10-05, point 7). Depends on the storage task.

**Show:**
- which channels the record is ready for, with who and when;
- the server's warning per marked channel;
- machine ready.

All on `backend/app/templates/content_detail.html`, with no forms.

**Remove what readiness made false:**
- **"No readiness verdict here, deliberately … 'Ready' has no meaning until a module is named"** (`content_detail.html`, around 128-141), and the same argument in `backend/app/frontend/router.py` (around 689-696 and 2174-2177) and `content.html:69`;
- **the test pinning it,** `TestNoReadinessVerdictIsClaimed` in `backend/tests/test_channels.py` (around 1201-1218). It contradicts ADR-174 point 1 (2026-09-24);
- **the comments still citing ADR-161 point 7's rider** ("catalogue readiness is 'push fields not empty'"), which that ADR's 2026-09-24 addendum declared false:
  - `backend/app/content/service.py` (around 150-155 and 172-175);
  - `backend/tests/test_channels.py` (around 1216 and 2620);
  - `backend/tests/test_content_presence.py:3`.

  The empty-push-field rule itself (`without_empty_presence_fields`) stays; only its stated reason changes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The Jinja record page shows readiness, warnings and machine ready, without forms
- [ ] #2 The "no readiness verdict" text, its test and the ADR-161-rider comments are gone or corrected
<!-- AC:END -->
