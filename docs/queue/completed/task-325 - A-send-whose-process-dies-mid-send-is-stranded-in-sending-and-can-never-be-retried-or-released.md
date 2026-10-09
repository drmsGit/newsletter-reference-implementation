---
id: TASK-325
title: >-
  A send whose process dies mid-send is stranded in 'sending' and can never be
  retried or released
status: Done
assignee:
  - '@claude'
created_date: '2026-10-09 14:01'
updated_date: '2026-10-09 14:15'
labels:
  - backend
dependencies: []
type: bug
ordinal: 100050
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Bug: a send whose process dies mid-send is stranded in "sending" for good, and nothing can resume or release it.** Found 2026-10-09 while finishing task-318 (AC #3, uncertain provider outcomes). Filed at the user's request.

**What happens.** send_send_instance (backend/app/delivery/service.py:791):
1. sets the parent to "sending" and commits (:909) before delivering;
2. delivers recipient by recipient;
3. derives the final status at the end.
If delivery raises an exception, the except block marks the parent "failed" (:924), and failed is retryable. But if the PROCESS dies (killed, out of memory, a deploy restart, the machine going down), that except block never runs: the parent stays "sending".

**Why it cannot recover.** The send's own guard refuses an instance already "sending" or "sent" (:826), and so does the held-send approval (backend/app/approvals/actions/send_fire.py:161). That guard is what stops two schedulers or two clicks from double-sending (the row lock plus the status check). So a stranded send can never be retried, by a person, the scheduler or an approval. Since task-318:
- its recipients already sent stay "sent";
- the one whose provider call was in flight stays "sending" (maybe sent);
- the rest stay "created" (never attempted).
A retry would handle all three correctly (skip, mark uncertain, send), but no retry is allowed in.

**Reachable today?** In this local proof of concept, a crash mid-send is rare. It becomes ordinary in any deployment: restarts during a long send, a worker timeout. Today the only way out is editing the database by hand.

**Options for the fix:**
1. **A lease.** The parent records when it was claimed (a new column, sending_since, or reuse updated_at), and a send "sending" for longer than a deployment setting (say 30 minutes with no execution progress) counts as stranded. The guard then lets a retry in. Automatic, but it needs a heartbeat or progress signal to be safe: a genuinely slow send must not be mistaken for a dead one.
2. **A person releases it.** An explicit action, "Release this stuck send", moves a "sending" send to "failed" after showing what it holds (sent, sending and created counts). It is authorised like sending itself (sends.execute) and audited. Nothing automatic can misjudge a slow send, but it needs a person to notice.
3. **Both:** detect a likely-stranded send (monitoring flags it after the threshold) and let a person release it.

Whatever is chosen, a released send's retry then follows task-318's rules: "sending" executions become uncertain and are not resent, and "created" ones are sent.

**Related:** task-318 (retry rules, done), task-124 part (c) (a queue with a log), task-81 (provider-side reconciliation, which could later turn "uncertain" into sent or not-sent by asking the provider), ADR-183 (delivery evidence).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A send left 'sending' by a dead process can be recovered (by the chosen mechanism) without editing the database
- [x] #2 Recovery cannot be mistaken for a live send: two runs never deliver the same send at once
- [x] #3 A recovered send's retry follows task-318: sent stays sent, sending becomes uncertain, created is sent
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-09: decided (option 3) and built (commit d7a3090; CI green; ADR-192 in 50db60f).

Design, per the user's choice of option 3: detection flags, a person releases.
- "Stranded" means a send with status "sending" and no activity for 30 minutes (STRANDED_AFTER). Activity is the newest updated_at of the send instance or of any of its executions. Since task-318 every execution is written just before its provider call, so a living send keeps showing activity per recipient.
- Release is priced sends.plan, not sends.execute. That deviates from my first description to the user, and the ADR records why: sends.execute means exactly "can mail a person", asserted both ways in backend/tests/test_api_guard.py (MAILS_A_PERSON), and release mails nobody. The retry that could mail someone is still sends.execute. Release is people only (require_person).

Change:
- backend/app/delivery/service.py: _last_activity (one grouped query, "sending" sends only), _with_stranded, and release_send_instance. Release re-checks stranded under a FOR UPDATE row lock, refuses with ValueError otherwise (LookupError if not found), sets "failed" and returns the executions by status.
- list_send_instances and send_instance_detail fill stranded and last_activity_at (backend/app/delivery/models.py SendInstance).
- POST /delivery/send-instances/{id}/release (backend/app/delivery/router.py): require_person, 409 unless stranded, audited as send.released (new constant in the ADR-153 vocabulary) with {"executions": counts}.
- require_person's docstring now names release as its second use.
- React (frontend/src/screens/DeliveryDetail.tsx): a "This send looks stranded" section with the last activity time, an explanation and a "Release this send" button (useReleaseDelivery in frontend/src/api/resources.ts), with the refusal shown as an alert. schema.d.ts was regenerated.

Tests:
- backend/tests/test_stranded_send.py, 8 tests:
  - the flag in detail and list;
  - recent activity is not flagged;
  - a living send whose executions keep moving is not flagged;
  - a finished send is never flagged;
  - a person releases, the audit holds the counts, and the retry follows task-318 (sent stays sent, sending becomes uncertain, created is sent, one mailed);
  - a live send is refused with 409;
  - a machine gets 403;
  - the service refuses what is not stranded.
- 3 client tests in frontend/src/screens/Deliveries.test.tsx: flagged and released; a refusal is shown; nothing is offered when not stranded.
- Mutation check: backend 6 of 6 caught. The first run missed two mutants (execution activity ignored; finished sends flagged), and two cases were added. Client: hiding the notice fails 2.
- Full suite: 1592 backend, 227 client.

Live check, on scratch data: scratch send 5, "SCRATCH task-325 stranded", left "sending" with one "sending" execution and timestamps two hours old. The React screen showed the notice and the time of last activity. Release returned 200, the status became "failed", the notice disappeared, the execution stays "sending" until a retry, and the audit entry is send.released by the user with {"executions": {"sending": 1}}.

Found by the adr-author, not built and not filed: if a process dies while an approval runs send_fire, the send is stranded and its held request stays "executing". Releasing the send does not touch that request, and "executing" counts as open, so no new held request can be raised for that send until the row is cleared by SQL. A person can still retry the send directly.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
A send left 'sending' by a dead process is now flagged as stranded after 30 minutes without activity. A person releases it from the delivery screen: people only, refused unless stranded at that moment, audited. It becomes failed, and the retry follows task-318's rules. Decided as option 3 (ADR-192). Verified by 8 backend and 3 client tests (all mutants caught), the full suites, CI green and a live release of a scratch send.
<!-- SECTION:FINAL_SUMMARY:END -->
