---
id: TASK-319
title: Webhook deduplication prevents a failed consent suppression from being retried
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 08:02'
updated_date: '2026-10-09 08:51'
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
- [x] #1 Retrying a recorded complaint whose suppression previously failed eventually writes the correctly scoped opt-out.
- [x] #2 A crash after raw-event persistence cannot permanently suppress processing of mandatory effects.
- [x] #3 Completed retries are idempotent and do not duplicate consent or signal effects.
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: promoted from ChatGPT's code review (docs/queue/docs/doc-1, draft-7) by the user's decision, ordered by severity. Claude verified the core evidence against the code the same day: create_engagement_event commits the raw event (backend/app/insight/service.py:50-51) before any effect, and the provider ingest returns duplicate on a seen provider_event_id (backend/app/providers/service.py:95-106) without resuming effects.

2026-10-09: fixed (commit c06f1ba; CI green, run 37907021733).

Design: the draft's first option, the event committed atomically with its mandatory effects. No processing-state table and no resume logic. It needed no new decision, because ADR-106 already makes bounce and complaint feedback mandatory, and the simplest way to make it unlosable is one transaction.

Change:
- process_provider_webhook_event (backend/app/providers/service.py) runs _record_with_effects (ingest, then signal contributions, then the opt-out) without committing, then commits once. On any exception it rolls back and re-raises, so the provider's retry finds no event and processes it from the start.
- The writers take a keyword-only commit switch whose default is unchanged for their other callers: create_engagement_event and apply_event_to_signals (backend/app/insight/service.py), record_contribution (backend/app/insight/signals.py), suppress_recipient (backend/app/recipients/service.py, passed on to record_consent), and ingest_provider_event.
- The quarantine path for an unmatched event still commits on its own: nothing follows it.
- A completed event retried is still answered "duplicate" and writes nothing. Signals were already deduped by event id.

Tests: backend/tests/test_webhook_effects.py, reusing test_render_skip's world fixture.
- A complaint whose suppression raises leaves nothing behind, and the provider's retry then opts the person out. This failed before the fix: the retry was answered "duplicate".
- A completed complaint retried is a duplicate, and the consent event count does not change.
The test deliberately does not roll the session back itself, so the handler's own rollback is tested: a caller reusing its session would otherwise see the half-written event.
Mutation check: 2 of 2 caught (the event committing on its own again; no rollback). Full suite: 1546 passed.

No live check. Exercising the webhook live needs a signed provider request (RESEND_WEBHOOK_SECRET, which lives in .env), and it would write consent events for a real recipient. The tests drive the same handler end to end with the real database.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A provider event and its mandatory effects (signals, and for a complaint or hard bounce the opt-out) now commit as one transaction. A failed effect rolls everything back, so the provider's retry processes the event again instead of being answered duplicate, and a completed retry still changes nothing. Verified by two tests (one failing before the fix), 2/2 mutants caught, the full suite and CI green.
<!-- SECTION:FINAL_SUMMARY:END -->
