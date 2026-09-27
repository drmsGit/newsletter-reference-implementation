---
id: TASK-51
title: >-
  `app/approvals/router.py` — list, detail, history, approve, reject and
  `process-expired`.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
  - frontend
dependencies: []
type: feature
ordinal: 200400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Feature] — DECIDED 2026-09-19, BUILT 2026-09-20.** `app/approvals/router.py` — list, detail, history, approve, reject and `process-expired`. `require_person` refuses a bearer on the two decision routes, and `test_there_is_no_way_to_approve_over_the_api` was rewritten rather than deleted: it now mints a held request the honest way, asserts the bearer is refused with a reason that is **not** about permissions, and asserts the row is still pending afterwards — a refusal arriving after the action ran would pass the first two. The row-level gate moved out of the Jinja router into `approvals.service.may_decide`, so both planes ask one function (that was also category-B item B3 from `docs/react-migration-inventory.md`). Original entry: **Approve and reject a held action over the JSON API, accepting a session and refusing a bearer credential.** [[ADR-168 — The Manager SPA Authenticates With Its Session Cookie]] put people on the machine plane, which changed what the existing absolute means: "no approve over the API" was written about *machines* — a machine that can approve its own held request has defeated the mechanism — and with a person on that plane it now says the React client cannot work an approval inbox at all. That matters more since [[ADR-169 — Operational Flows Are Sequenced Variants, Not a Canvas]] made held sends the ordinary way a lifecycle cycle reaches a human. **The property to keep is unchanged**: a machine may **request** approval (ADR-166 point 5) and may never grant it. So the test changes from "no such route exists" to "a bearer credential is refused here" — the sharper assertion, because it tests the property rather than its absence — and `test_there_is_no_way_to_approve_over_the_api` in `tests/test_api_guard.py` is what has to be rewritten rather than deleted. Also needs the expiry sweep (`process-expired`) as a JSON cron seam, for the reason `/delivery/process-due` just got one.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 150, section "Features", position 4 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
