---
id: TASK-228
title: >-
  No post-render per-recipient "nothing meaningful" skip — and its reason lands
  with the exclusion reasons
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
labels:
  - backend
dependencies: []
priority: parked
type: feature
ordinal: 209300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** No post-render per-recipient "nothing meaningful" skip (`delivery/`). From the resolution:

**The "when" is settled by the fact that this is inherently per-recipient.** For one recipient every slot resolves; for another none do, and they receive a header, a divider and a footer. **Compose time cannot evaluate it** — the slots have not resolved for anybody, and question 4.2 established that preview does not resolve either. So it can only live in the send path, after rendering, per person.

**That also reads [[ADR-086 — Decision Slots Fail Gracefully]] literally.** *"The email must not be sent"* — **that** email, to **that** person. It is a skip, not a failed send, and a send to a thousand people does not abort because one of them resolved to nothing.

**"Meaningful" means at least one module produced output beyond the envelope and the decorative modules.** The alternatives each break on a real case: *no modules rendered* is never true because the header always renders; *no `cms` module rendered* wrongly kills a legitimate all-static announcement email; *fewer than N content modules* requires choosing N. The chosen test needs no threshold — a static announcement passes because its `hero` and `cta` produce output, and a recipient whose every slot came up empty fails because only header and footer rendered.

**The reason lands with the exclusion reasons, and that is the load-bearing half of the answer.** `app/delivery/exclusion.py` already records *why* each recipient was excluded on the execution row, in an ordered stack (addressability → consent → suppression → frequency). This check cannot **join** that stack — the stack runs before the send loop and this one needs the rendered result — so it is a distinct post-render skip. But its reason belongs in the same place, because *"why didn't this person get it?"* must have **one** answer surface. Two places to look is how a compliance question becomes an afternoon.

**Consequence:** the exclusion-reason vocabulary gains a value that is not produced by the exclusion stack, so whatever records it must accept a reason from a later stage.

Source: [[Variant Editor - design interview]] → What Cluster 4 produced, gap 24.

**Verified against the code 2026-09-27:** `send_send_instance` (`backend/app/delivery/service.py:572`) applies only the exclusion stack (`:703-742`); an empty slot is swallowed and the send continues (`:760-766`); nothing checks the rendered result.

Related: task-104 (the pre-send safety-net bundle).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
