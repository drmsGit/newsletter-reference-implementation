---
id: TASK-325
title: >-
  A send whose process dies mid-send is stranded in 'sending' and can never be
  retried or released
status: To Do
assignee: []
created_date: '2026-10-09 14:01'
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
- [ ] #1 A send left 'sending' by a dead process can be recovered (by the chosen mechanism) without editing the database
- [ ] #2 Recovery cannot be mistaken for a live send: two runs never deliver the same send at once
- [ ] #3 A recovered send's retry follows task-318: sent stays sent, sending becomes uncertain, created is sent
<!-- AC:END -->
