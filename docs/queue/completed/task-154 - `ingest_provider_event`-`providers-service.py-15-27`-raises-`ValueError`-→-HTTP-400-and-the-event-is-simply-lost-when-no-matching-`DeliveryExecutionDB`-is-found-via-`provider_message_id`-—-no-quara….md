---
id: TASK-154
title: >-
  `ingest_provider_event` (`providers/service.py:15-27`) raises `ValueError` →
  HTTP 400 and the event is simply lost when no matching `DeliveryExecutionDB`
  is found via `provider_message_id` — no quara…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 501800
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `ingest_provider_event` (`providers/service.py:15-27`) raises `ValueError` → HTTP 400 and the event is simply lost when no matching `DeliveryExecutionDB` is found via `provider_message_id` — no quarantine/retry mechanism exists, directly violating [[ADR-129 — Correlate Provider Events to Delivery Executions]]'s "must not be silently discarded" requirement. Fix: store unmatched events (full payload) in a quarantine/dead-letter table for later reconciliation instead of returning an error and losing the data. Source: [[Interview Prep - Delivery, Providers, Recipients]] → Providers Q2. **Done 2026-07-12** — new `ProviderEventQuarantineDB` table + `GET /provider/quarantine` listing endpoint; `POST /provider/events` now returns `{status: "matched"|"quarantined", ...}` instead of raising. Verified live: an unmatched event was stored with its full payload and reason, not lost. The inbound provider-adapter layer itself (event-type normalization, real webhook contracts) remains a separate, larger Feature already logged.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 537, section "Done", position 18 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
