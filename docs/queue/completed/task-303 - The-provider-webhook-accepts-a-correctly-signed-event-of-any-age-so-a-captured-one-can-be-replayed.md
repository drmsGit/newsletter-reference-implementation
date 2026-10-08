---
id: TASK-303
title: >-
  The provider webhook accepts a correctly signed event of any age, so a
  captured one can be replayed
status: Done
assignee:
  - '@claude'
created_date: '2026-10-08 20:54'
updated_date: '2026-10-08 21:01'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100350
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**The provider webhook accepts a correctly signed event whatever its age, so a captured genuine webhook can be replayed later.** Found 2026-10-08 while closing task-98's webhook gap.

verify_signature (backend/app/providers/adapters/resend.py, around line 65) checks the Svix signature over id, timestamp and body, and fails closed when the secret is unset (the regression tests/test_provider_webhook_signature.py exists for). It never compares svix-timestamp with the current time. The file's own signing helper uses timestamp 1700000000 (November 2023), and test_accepts_a_correctly_signed_body passes with it.

**Why it matters:**
- POST /provider/webhooks/resend is public. The signature is the only thing between a sender and the suppression logic, and the signal layer.
- A recorded genuine event can be sent again later and is accepted: a duplicate click (affinity signals skewed), or a duplicate bounce or complaint, which can opt a recipient out (ADR-106).
- Svix's own guidance is to reject timestamps more than about five minutes from now, in either direction.

Not checked here: whether processing already makes a replayed event a no-op (for example by event id); if it does, the impact is smaller but the gate is still the place for it.

**The fix it suggests:**
- A tolerance check in verify_signature: refuse when abs(now - svix-timestamp) exceeds a window, five minutes per Svix, written as a named constant.
- Tests: an old timestamp is refused, a future one beyond the window is refused, a current one is accepted.
- The existing tests sign with a current timestamp instead of 1700000000.

Related: ADR-106 (bounce and complaint feedback is mandatory), ADR-166 point 6 (the signed provider door), task-98 (where it was found).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 verify_signature refuses an event whose svix-timestamp is more than the tolerance away from now, in either direction
- [x] #2 Tests cover an old, a future and a current timestamp; the existing signature tests sign with a current one
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Fixed 2026-10-08, commit 89fd4df. backend/app/providers/adapters/resend.py: WEBHOOK_TOLERANCE_SECONDS = 300 (Svix's guidance); verify_signature refuses an svix-timestamp more than that from now in either direction, or one that is not a number, after the header check and before the HMAC.

Severity, checked while fixing (the description left it open): lower than filed. app/providers/service.py ingest_provider_event dedups by (provider, provider_event_id), the id being message id + type + created_at, and process_provider_webhook_event runs both consequences - signal contributions and the bounce/complaint opt-out - only when the result is "matched", never "duplicate". So an exact replay of a stored event was already a no-op. The gate still matters for what dedup does not remember: a quarantined event (not stored as an engagement event) and anything a future retention prune deletes (task-85).

Tests: tests/test_provider_webhook_signature.py signs with the current time (was 1700000000); old, future and non-numeric timestamps refused, within the window accepted. 3 mutants killed. Suite 1508; CI green. No live check: it would need RESEND_WEBHOOK_SECRET from backend/.env, which is not read; the route-level test (test_the_route_refuses_a_well_signed_event_while_the_secret_is_unset) exercises the same path.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The provider webhook now refuses a correctly signed event whose timestamp is more than five minutes from now, so a captured one cannot be replayed later. Checked while fixing: an exact replay of a stored event was already harmless thanks to deduplication; this closes the gap for events deduplication does not remember. Verified by four new tests (3 mutants killed), the full suite and a green CI run.
<!-- SECTION:FINAL_SUMMARY:END -->
