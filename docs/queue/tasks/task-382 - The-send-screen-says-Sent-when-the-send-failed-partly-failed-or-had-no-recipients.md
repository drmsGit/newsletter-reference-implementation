---
id: TASK-382
title: >-
  The send screen says Sent when the send failed, partly failed or had no
  recipients
status: To Do
assignee: []
created_date: '2026-10-16 11:31'
labels:
  - frontend
dependencies: []
type: bug
ordinal: 100100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Bug]** The React send screen tells a manager a send went out when it did not. After "Send now", `frontend/src/screens/SendVariant.tsx:382` prints `Sent: {fire.data.status}`, so a failed send reads "Sent: failed.", a partly failed one "Sent: partial failed." and one with nobody to send to "Sent: no recipients.". The word a manager reads first is "Sent", which is false in all three cases.

task-323 fixed exactly this at the API: the send endpoint now reports the persisted outcome truthfully (completed in `docs/queue/completed/task-323 - The-send-endpoint-reports-sent-when-the-persisted-send-has-failed.md`). The send screen, built later in task-67/task-378, put the misleading word back on top of the truthful status. Found by Codex's regression batch for source 0fd3332a (pre-stage note doc-22, tests-branch commit 7035896, `origin/codex/regression-tests`).

**Fix:** word the line per outcome, never prefixed "Sent" unless it was: sent → "Sent."; partial_failed → "Partly sent: some recipients failed." (and the link to the delivery, which already follows); failed → "Not sent: the send failed."; no_recipients → "Nothing sent: nobody was eligible.". Check which statuses `FireResult` can carry (`backend/app/delivery/service.py`) and word each; an unknown one shows plainly without "Sent". Matters for the November demo: a failed mock send is shown on screen.

**Test:** bring in Codex's `frontend/src/screens/SendVariant.outcome.test.tsx` from commit 7035896 (read 2026-10-16; its three cases fail on main today, each asserting the notice does not start "Sent:"). It lands together with the fix, failing first, per the handoff rule in CLAUDE.md.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A failed, partly failed or no-recipients send is never worded as Sent
- [ ] #2 Codex's SendVariant.outcome.test.tsx is on main and passes
<!-- AC:END -->
