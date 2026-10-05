---
id: TASK-287
title: >-
  The Jinja content screen shows readiness read-only, and the claims readiness
  made false are removed
status: Done
assignee:
  - '@claude'
created_date: '2026-10-05 18:10'
updated_date: '2026-10-05 19:31'
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
- [x] #1 The Jinja record page shows readiness, warnings and machine ready, without forms
- [x] #2 The "no readiness verdict" text, its test and the ADR-161-rider comments are gone or corrected
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Verify each cited place still says what the task claims (all did).
2. Tests first: replace TestNoReadinessVerdictIsClaimed with TestReadinessIsShownAsMarked — filled fields make nothing ready; a mark shows who/when and the server's warning; machine ready yes/no; no form, input or button in the block, and it says where readiness is marked; a mark on a channel switched off since is still shown.
3. router.py: _readiness_rows (available channels plus any marked one) passed to content_detail.html; a read-only Readiness section near the top.
4. Remove the 'no readiness verdict' comment; correct the ADR-161-rider reasons in router.py, content.html, content/service.py, test_content_presence.py and test_channels.py — the empty-push-field rule stays, its reason is now that absent means nothing was written for push (the Jinja page's 'Nothing written for this channel yet' reads key presence).
5. Mutation-check, full suite, live read-only check.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Choices made in building: the Readiness block sits near the top of the page, above the content card; channels shown are those this deployment may select plus any marked channel switched off since (a mark is a fact, so it is shown); channel names as the React page heads them ('Email', 'Push'); no link to the React client (no Jinja page links there yet), just 'Readiness is marked in the manager client.'
The old test's real point — filled fields make nothing ready — is kept as the first new case. A second test (the push read tab must not speak of readiness) stays, with its reason corrected.
Validation: 4 new tests failing first; 9 mutants all caught (one survivor, 'marked-but-switched-off channel dropped', led to the fourth test). Backend 1316 passed. Live, read-only: /ui/content/65 shows 'Email: ready — Marked ready by migration 0032 …', 'Push: Not marked ready', 'Machine ready: yes'; 117 shows both not marked; the old text is gone.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The Jinja record page shows a read-only Readiness block: per channel whether a person marked it ready, who and when, the server's warning, and machine ready, with no form and a line saying readiness is marked in the manager client. The 'no readiness verdict' text and its test are gone; the comments citing ADR-161's falsified rider now give the empty-push-field rule's real reason. Verified by 4 new tests, 9 caught mutants, 1316 backend tests and a read-only live check of records 65 and 117.
<!-- SECTION:FINAL_SUMMARY:END -->
