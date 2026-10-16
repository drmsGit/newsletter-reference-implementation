---
id: TASK-382
title: >-
  The send screen says Sent when the send failed, partly failed or had no
  recipients
status: Done
assignee:
  - '@claude'
created_date: '2026-10-16 11:31'
updated_date: '2026-10-16 11:43'
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
- [x] #1 A failed, partly failed or no-recipients send is never worded as Sent
- [x] #2 Codex's SendVariant.outcome.test.tsx is on main and passes
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Built 2026-10-16 (commit b2f085c). One wording function (outcome in frontend/src/screens/SendVariant.tsx) is used right after "Send" and when the page is opened later, so a reload never says something different: sent "Sent."; partial_failed "Partly sent: some recipients failed."; failed "Not sent: the send failed."; no_recipients "Nothing sent: nobody was eligible."; any other status "This send is …" as before. The four outcomes are the ones FireResult documents (backend/app/delivery/models.py:140); the fire route has no approval-hold answer, so none is worded. The notice stays role="status" for every outcome, as Codex's test expects; whether a failure should be an alert instead is left open.

Codex's SendVariant.outcome.test.tsx came in adapted, said in its header: it found the notice by the raw status words ("partial failed", "no recipients"), which any truthful wording drops. It now asserts each outcome's exact sentence, keeps the rule (never starts with Sent unless sent), and adds sent and the reopened page (8 cases). All 8 failed before the fix. SendVariant.test.tsx expected "Sent: sent." and now "Sent.".

Verification: vitest 308 passed, tsc, build, eslint (no errors); pytest 1985 passed (backend untouched); 5 mutations, all caught; live check, read-only, on existing scratch sends: send 5 (SCRATCH task-325, failed) reads "Not sent: the send failed.", send 9 (SCRATCH task-109, sent) reads "Sent.".
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The send screen now words each outcome truthfully, the same after sending and on a reopened page: Sent. / Partly sent: some recipients failed. / Not sent: the send failed. / Nothing sent: nobody was eligible. Codex's outcome test came in adapted (asserts each sentence; adds sent and the reopened page). Verified: vitest 308, pytest 1985, 5 mutations caught, live check on scratch sends 5 (failed) and 9 (sent), CI green on b2f085c.
<!-- SECTION:FINAL_SUMMARY:END -->
