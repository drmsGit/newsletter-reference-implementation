---
id: TASK-326
title: >-
  A held request whose action died mid-run stays 'executing' for good, while its
  send can now be released
status: To Do
assignee: []
created_date: '2026-10-09 14:17'
labels:
  - needs-adr
  - backend
dependencies: []
type: decision
ordinal: 300195
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**Decision: a held request whose approved action died mid-run stays "executing" for good, and since ADR-192 its send can be released but the request cannot.** Found 2026-10-09 by the adr-author while writing ADR-192 (task-325). Filed at the user's request.

**What happens.** Approving a held action moves the request from pending to executing (backend/app/approvals/service.py:307), runs the action, and then moves it to approved or failed (:345-367). If the PROCESS dies while the action runs, for example send_fire delivering a send, the request stays "executing". The open-request index ux_pending_actions_one_open_per_subject (backend/app/approvals/db_models.py:160-166) counts both "pending" and "executing" as open. So no new held request can be raised for that subject (that send) until the row is cleared, which today means SQL.

**This is deliberate today.** [[ADR-142 — Autonomous Workflows and the Automation Boundary]], addendum 2026-09-29, point 6: "A crash during execution leaves the row executing, deliberately, and nothing retries it". Nobody can know whether the action ran, and re-approving would be the double execution that addendum closes; "resolving it is a person's investigation, not a button". It names this "the same shape as a send left in sending".

**What changed.** [[ADR-192 — A Stranded Send Is Flagged, and a Person Releases It]] (task-325) gave the send that shape's answer. A send stranded in "sending" is flagged after 30 minutes without activity, and a person releases it to "failed", safely, because task-318 makes a retry skip what may have been sent. Now the two halves disagree:
- a stranded send can be released and retried by a person directly;
- its held request stays "executing", blocking a machine from asking again for that send.
Releasing the send does not touch the request.

**What has to be decided:**
1. **Keep point 6 as it is.** The stuck request stays a matter for investigation; a person retries the send directly, and a machine cannot re-request it until someone clears the row by hand. Cheapest, but it keeps a SQL-only path.
2. **The same answer as ADR-192, for requests.** Flag a request "executing" for longer than a threshold, and let a person mark it failed (people only, audited). Whether a retry is then safe depends on the action, which is the point 6 reasoning: for send_fire it is, through task-318; other actions (content readiness, applying an AI suggestion) would need checking one by one.
3. **Couple them.** Releasing a stranded send also fails its executing held request, since the send's own release already establishes that the run died.
Any of these amends ADR-142 point 6 through a dated addendum (adr-author), not a rewrite.

**Related:** task-325 and ADR-192 (the send half), task-318 (retry rules), task-124 part (c).
<!-- SECTION:DESCRIPTION:END -->
