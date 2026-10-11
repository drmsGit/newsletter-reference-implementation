---
id: TASK-59
title: >-
  Nothing marks a dead push token invalid, because there is no inbound push
  adapter.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
updated_date: '2026-10-11 18:49'
labels:
  - backend
dependencies: []
priority: parked
type: feature
ordinal: 201200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — the half of the push channel that is genuinely missing, and it is not the provider.** **Nothing marks a dead push token invalid, because there is no inbound push adapter.** Checked 2026-09-18 after the user asked whether a push mock provider was missing. It is not: [[ADR-161 — Channel Execution Shapes]] point 2 requires a mock **per interface**, not per channel, and email and push share the *addressed* interface — so `MockProvider` declaring `channels = frozenset()` (every channel) is the complete answer, and `get_provider("mock", channel="push")` returns it.

  **What is absent is on the OTHER side of the provider boundary.** `app/providers/adapters/` holds one adapter, `resend.py`, which is inbound email feedback. [[ADR-163 — Per-Channel Consent and Addressability]] point 2 says "tokens expire and APNs reports dead ones, so **a status you can mark invalid beats a value you overwrite**" — and `AddressabilityDB.status` exists for exactly that. But nothing writes it for push, so a dead token stays `active` forever and the addressability stage keeps handing it to the provider on every send. The consequence is quiet: the send reports success, the notification goes nowhere, and the recipient looks reachable.

  **Needs a real vendor before it can be built or tested** — APNs/FCM credentials, which is also why the real outbound push adapter does not exist. Worth sequencing with that one, since both are the same vendor integration seen from two directions, and [[ADR-100 — Provider Layer as Send and Feedback Adapter]] treats send and feedback as one adapter concept for that reason. Source: found while answering the user's provider-structure question, 2026-09-18.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 166, section "Features", position 12 in that section (top = do next). The description is the original entry, verbatim.

2026-10-11, the user: parked until there is a real push provider. Inbound push feedback cannot be built or tested against the mock alone.
<!-- SECTION:NOTES:END -->
