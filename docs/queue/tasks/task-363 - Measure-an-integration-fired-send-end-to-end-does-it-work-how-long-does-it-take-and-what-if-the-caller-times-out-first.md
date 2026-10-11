---
id: TASK-363
title: >-
  Measure an integration-fired send end to end: does it work, how long does it
  take, and what if the caller times out first
status: To Do
assignee: []
created_date: '2026-10-11 12:26'
labels:
  - backend
dependencies: []
type: chore
ordinal: 210100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Test / investigation]** Raised by the user on 2026-10-11: does an integration firing a send directly (POST /delivery/send-instances/{id}/send), which in turn calls the provider's API, actually work end to end? What is the time delay, and is it a problem that one API call triggers further API calls?

**What the code does today** (read 2026-10-11, not yet measured):
- The send runs inside the HTTP request. `send_send_instance` (backend/app/delivery/service.py, the loop around :1213) renders each recipient's email and calls `provider.send()` once per recipient, one after another (:1368). The Resend adapter makes one blocking `httpx.post` with a 15-second timeout per email (backend/app/delivery/providers/resend.py:79).
- So the request takes roughly recipients × (render + provider round trip). The company cap is 1000 by default (250 in dev); an integration's unattended ceiling (task-341) bounds it further.
- An orchestrator calling this (n8n, a webshop) waits for the whole send. Orchestrators and proxies have their own request timeouts, so a long send can outlive the caller's patience.

**Questions this task answers, by measuring rather than guessing:**
1. Does it work end to end for an integration: allowed under its ceiling, the provider called, deliveries recorded, the response returned?
2. How long does it take per recipient and in total, at 1, 50, 250 and the cap? With the mock provider plus an injected delay that matches a measured provider round trip; no real provider calls in testing (agent memory: mock only, never Resend). A real-provider measurement belongs to the live tests, when the webhook is reactivated.
3. What happens when the caller gives up first: the client disconnects or times out while the send continues server-side. Does the send finish? Does a retry by the orchestrator get "already sending/sent" (the row lock, ADR-192's stranded-send handling) rather than a second send?
4. What happens when the provider is slow or failing mid-send (timeouts per call add up; partial sends; ADR-192).
5. Whether chaining is a problem in itself: one inbound request holding a worker thread for the whole send, and how many concurrent sends a deployment can carry.

**Outcome:** a short written result (numbers, what broke, what held) and, if the delays are a real problem, evidence for task-127, which owns the fix (worker/job boundary, batching through the provider's batch endpoint, bounded concurrency). This task does not change the send path itself.

Related: task-127 (bulk send batching and send timing, parked, needs ADR), task-341 (the unattended ceiling), ADR-192 (stranded sends), ADR-100/ADR-101 (provider adapter and capabilities), task-103 (performance notes).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An integration-fired send is run end to end with the mock provider at several sizes, with timings written down
- [ ] #2 A caller that times out or disconnects mid-send is tested: the send's outcome and a retry's answer are recorded
- [ ] #3 The result names whether task-127's worker boundary is needed now, with the numbers
<!-- AC:END -->
