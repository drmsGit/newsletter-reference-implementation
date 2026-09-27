---
id: TASK-3
title: >-
  `list_recipients` now takes the working brand and passes it to
  `to_recipients`; the brand is context rather than authorisation, so
  `recipients.manage` stays platform-level.
status: Done
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: p1
type: bug
ordinal: 100300
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug] — P1. DONE 2026-09-20, together with the consent decision it was waiting on.** `list_recipients` now takes the working brand and passes it to `to_recipients`; the brand is context rather than authorisation, so `recipients.manage` stays platform-level. Pinned by `test_listing_recipients_returns_rather_than_raising`. Original finding: **a plain 500 on a plain list route that nothing noticed.** **`GET /recipients/` has been raising `TypeError` for as long as recipients carried consent per brand.** `list_recipients` (`recipients/service.py:501`) calls `to_recipients(db, records)`, and `to_recipients` (`:148`) requires a third positional `brand_id` — consent is to a sender, so projecting a recipient's consent without a brand is not a thing that can be done. The caller was never updated. **Found 2026-09-19** while writing an unrelated ADR-172 test that happened to be the first thing in the repo to call this route; no test covers it, which is why a route that cannot return has looked fine. **Why it is not a one-line fix:** `recipients.manage` and `view` are both platform-level, so a machine may legitimately arrive with no declared brand and there is then no brand whose consent to project. The honest options are to make the route brand-owned (requiring `X-Brand`, a contract change) or to project no consent at all when no brand is resolved — and that is the **same call** the `recipients.consent` item below is waiting on. Take both together. **The silver lining:** `to_recipients`' required positional is exactly [[ADR-172 — The Working Brand Is Resolved Once and Carried Into Every Query]] point 4's shape, and it did its job — it turned a silent wrong answer into a loud one. The loud one just landed somewhere nobody was listening.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 35, section "Bugs", position 3 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
