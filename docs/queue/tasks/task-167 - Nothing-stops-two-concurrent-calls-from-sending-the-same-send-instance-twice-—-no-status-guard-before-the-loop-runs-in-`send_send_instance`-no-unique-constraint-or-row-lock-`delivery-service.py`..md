---
id: TASK-167
title: >-
  Nothing stops two concurrent calls from sending the same send instance twice —
  no status guard before the loop runs in `send_send_instance`, no unique
  constraint or row lock (`delivery/service.py`).
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 503100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** Nothing stops two concurrent calls from sending the same send instance twice — no status guard before the loop runs in `send_send_instance`, no unique constraint or row lock (`delivery/service.py`). Would produce duplicate sends and last-write-wins on `provider_message_id`. Fix: add a status guard (reject/no-op if already `"sending"`/`"sent"`) plus a row lock or unique constraint to make it safe-by-construction, not just application-level. Source: [[Interview Prep - Delivery, Providers, Recipients]] → Delivery Q5. **Done 2026-07-12** — `SELECT ... FOR UPDATE` on the send_instance row serializes the read-check-write of the status transition; status moves `draft → sending → sent`/`failed`, and a second call while already `sending`/`sent` gets rejected with a 409. Verified live: sent once successfully, second call correctly rejected instead of double-sending.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 563, section "Done", position 31 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
