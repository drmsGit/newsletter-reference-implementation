---
id: TASK-303
title: >-
  The provider webhook accepts a correctly signed event of any age, so a
  captured one can be replayed
status: To Do
assignee: []
created_date: '2026-10-08 20:54'
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
- [ ] #1 verify_signature refuses an event whose svix-timestamp is more than the tolerance away from now, in either direction
- [ ] #2 Tests cover an old, a future and a current timestamp; the existing signature tests sign with a current one
<!-- AC:END -->
