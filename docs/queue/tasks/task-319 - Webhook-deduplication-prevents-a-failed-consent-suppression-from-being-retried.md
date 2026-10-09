---
id: TASK-319
title: Webhook deduplication prevents a failed consent suppression from being retried
status: To Do
assignee: []
created_date: '2026-10-09 08:02'
updated_date: '2026-10-09 08:23'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Severity: high. A complaint or hard bounce can be recorded while the recipient remains eligible for future mail, even after the provider retries. Reachable today when processing is interrupted or a downstream database operation fails.

Evidence: backend/app/insight/service.py:32-55 commits the raw engagement event at line 51. backend/app/providers/service.py:97-106 returns duplicate if that provider event exists. process_provider_webhook_event then applies signals only for matched events (lines 174-182) and suppresses consent only for matched events (line 192). Thus the raw-event commit is an irreversible retry gate placed before mandatory effects.

Reproducer test to implement in the test database: arrange a consenting recipient and correlated sent execution; patch suppress_recipient to raise once; process a normalized complaint and observe the exception; restore suppression and process the identical provider_event_id. Assert the second result is duplicate and consent remains opted in. Also test interruption between raw-event commit and suppression. This continuation verified the control flow; this new reproducer was not run.

ADR-106 makes bounce/complaint feedback mandatory and ADR-163 requires its correctly scoped consent effect. Either commit the event with its mandatory effects atomically or persist processing state and idempotently resume unfinished effects on duplicate delivery. Apply the same recovery principle to signal updates.

Related: task-135 discusses the suppression explanation model; this is delivery/recovery correctness rather than that product decision.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Retrying a recorded complaint whose suppression previously failed eventually writes the correctly scoped opt-out.
- [ ] #2 A crash after raw-event persistence cannot permanently suppress processing of mandatory effects.
- [ ] #3 Completed retries are idempotent and do not duplicate consent or signal effects.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's code review (docs/queue/docs/doc-1, draft-7) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: create_engagement_event commits the raw event (backend/app/insight/service.py:50-51) before any effect, and the provider ingest returns duplicate on a seen provider_event_id (backend/app/providers/service.py:95-106) without resuming effects.
<!-- SECTION:NOTES:END -->
