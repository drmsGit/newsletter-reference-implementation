---
id: TASK-2
title: >-
  Closed in `send_send_instance`'s own `FOR UPDATE` query and across every other
  by-id write; mutating the predicate out of that query makes approving return
  `ok=True` and genuinely fire another brand'…
status: Done
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: p1
type: bug
ordinal: 100200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — P1, the sharpest finding in the review. DONE 2026-09-20 ([[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]], stages 1-7).** Closed in `send_send_instance`'s own `FOR UPDATE` query and across every other by-id write; mutating the predicate out of that query makes approving return `ok=True` and genuinely fire another brand's mail, which is what pins it. The residue — a held request naming another brand's send — is logged separately as P3. Original finding: **a credential for brand A can fire brand B's mail.** **The permission is checked against one thing and the row is addressed by another.** `enforce_api_policy` verifies a brand-scoped permission against the declared `X-Brand` and writes that brand onto `request.state.current_brand` (`auth/dependencies.py:424-454`) — but `POST /delivery/send-instances/{id}/send` passes only the id (`delivery/router.py:133-143`) and `send_send_instance` loads the instance by id alone (`delivery/service.py:363-379`). An integration holding `sends.execute` on brand A sends `X-Brand: A`, names a send instance belonging to brand B, and the guard agrees. Unattended it mails immediately; gated it creates a held request branded A whose payload points at B, which an A approver then executes in good faith. The same shape runs through the whole by-id JSON write surface: `audience/router.py:60-95` (patch, delete, members), `campaigns/router.py:239-295` (the three PUTs added 2026-09-19), `content/router.py:95-141`. **Fix:** make the authorised brand a required argument of every brand-owned service mutation and put it in the same query that selects the target, walking the ownership chain (`module → variant → campaign → brand`, `group → brand`, `send_instance → brand`); a row outside the authorised brand is a 404, not a 403. **Why P1:** `tests/test_brand_scoping.py` proves isolation thoroughly at the data layer and not once by addressing a row by id over the API — so the layer a hand-crafted request reaches first is the untested one. Distinct from the `brand_id=None` list default below: that leaks reads, this one writes and sends. Source: `CODE_REVIEW_2026-09-19` P1-02, verified 2026-09-19.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 33, section "Bugs", position 2 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
