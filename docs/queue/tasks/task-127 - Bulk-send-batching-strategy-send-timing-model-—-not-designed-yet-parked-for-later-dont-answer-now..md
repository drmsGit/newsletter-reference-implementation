---
id: TASK-127
title: >-
  Bulk send: batching strategy + send-timing model — not designed yet, parked
  for later (don't answer now).
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - needs-adr
  - backend
dependencies: []
ordinal: 301100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
📋 **Bulk send: batching strategy + send-timing model — not designed yet, parked for later (don't answer now).** **Update 2026-08-07 (code review P2-04) — the review quantified the shape of the problem.** Per recipient the send path loads the recipient separately, executes every decision slot with its own queries and commits, renders HTML, makes **one blocking 15-second-timeout `httpx.post`**, and commits again. One worker thread can therefore sit occupied for a very long time, and a process restart leaves a half-sent batch with no idempotent recovery. The reviewer's recommendation matches the direction already sketched here and adds two pieces worth carrying into the design: move execution to a **worker/job boundary** rather than a request, and give retries **idempotent semantics** so a restart cannot double-send. Batch-loading recipients, reducing commits and bounded concurrency are the rest. Two linked open questions surfaced 2026-07-26 while reviewing the outbound Resend adapter (interview-prep Q8). **(1) Batching.** Today `send_send_instance` (`delivery/service.py:185-232`) does **one `provider.send()` call per recipient** in a serial synchronous loop (15s-timeout `httpx.post` each), so a real send is O(N × latency) wall-clock. This is fine at demo scale (~40 recipients) but doesn't scale. Open question: send per-recipient vs. in packages (e.g. batches of ~1000) — note that per-recipient rendering (decision-slot personalization, ADR-083) does **not** block batching, since Resend's batch endpoint (`POST /emails/batch`) accepts N *already-rendered* distinct emails; we'd render the batch then submit it as one call. Provider-capability-dependent (ADR-101) — not every provider has a batch API, so the `DeliveryProvider` contract would need an optional batch capability with a per-recipient fallback. Also relates to the async/concurrency direction (a bounded-concurrency `httpx.AsyncClient` is the other way to kill the O(N×latency) cost). **(2) Send timing — how do managers decide *when* a send goes out?** Range of models to think through, not decide now: (a) the classic fixed calendar slot a manager picks ("this Thursday 9:00"); (b) system-chosen optimal time per recipient (send-time optimization — the content is dynamic, so the *time* could be dynamic too); (c) a hybrid where **specific field/content types carry their own cadence** — e.g. a "news" module that must go "every Sunday" regardless of the recipient-optimal time, so a single send may have both fixed-cadence and dynamically-timed components. These interact: send-time-optimization implies many small per-recipient sends (favoring per-recipient calls or small batches), while a fixed calendar blast favors one large batch. No decision needed now — captured so batching and scheduling get designed together rather than separately. Source: user, 2026-07-26 (post-Resend-outbound, interview-prep Q8).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 455, section "Needs ADR", position 11 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
