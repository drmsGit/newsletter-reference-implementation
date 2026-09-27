---
id: TASK-56
title: >-
  Subscribe (double opt-in) and unsubscribe do not exist as surfaces, and
  `List-Unsubscribe` is never sent.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
type: feature
ordinal: 200900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature] — the most concrete piece of the missing flow layer, and it blocks the beta's first send. Raised by the user 2026-09-18.** **Subscribe (double opt-in) and unsubscribe do not exist as surfaces, and `List-Unsubscribe` is never sent.** Verified 2026-09-18: `unsubscribe` exists only as a *string* — an engagement event type (`app/recipients/db_models.py:182`) and a consent source. There is no public unsubscribe route, no landing page, no DOI confirmation flow, and the Resend adapter's payload is `from / to / subject / html` with no `List-Unsubscribe` or `List-Unsubscribe-Post` header (`app/delivery/providers/resend.py:40-64`). One-click unsubscribe (RFC 8058) is a **hard requirement for bulk senders at Gmail and Yahoo**, so this is not a lifecycle nicety — it is a deliverability failure with a delay on it, the same shape [[ADR-106 — Bounce and Complaint Feedback Is Mandatory]] warns about. Scope per the user: **global opt-out plus per-channel**, email-only in practice. **Do not build it as a one-off script** — it is the first consumer of the flow/journey question in Needs ADR, and the shape of that answer decides where it lives. Probably deserves to be a launch gate of its own in `docs/business/LAUNCH-GATES.md`; **not added there without the user's call.**
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 160, section "Features", position 9 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
