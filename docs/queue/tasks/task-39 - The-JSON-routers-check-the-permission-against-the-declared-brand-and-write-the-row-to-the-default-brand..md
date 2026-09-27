---
id: TASK-39
title: >-
  The JSON routers check the permission against the declared brand and write the
  row to the default brand.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - backend
dependencies: []
priority: p1
type: bug
ordinal: 103900
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P1, and it is new as of the day gate 3 closed.** **The JSON routers check the permission against the declared brand and write the row to the default brand.** The `brand_id=ensure_default_brand(db).id` calls are at `content/router.py:151`, `campaigns/router.py:57` and `audience/router.py:27`, each under an identical PROVISIONAL comment (starting `:141`, `:48`, `:20`) whose first clause is now false: *"This router is unauthenticated (main.py leaves the twelve JSON routers unguarded — launch gate 3), so there is no session and no working brand to read."* Since 2026-09-18 `_api = [Depends(enforce_api_policy)]` is applied to all twelve, so `enforce_api_policy` reads `X-Brand` and checks the permission against **the declared brand** while the handler writes into **the default brand**. **Do not trust a line number for `main.py` in this entry** — it was 470 when logged, read as 485 hours later and is 561 as of 2026-09-19, because the approval-inbox build is actively editing that file; grep for `_api = ` instead. An integration granted `content.manage` on brand B, correctly declaring `X-Brand: B`, passes the check and creates the record in brand 1. The comment names the fix it was waiting for — *"ADR-166 decides the real answer: one credential per brand, so the brand arrives with the caller's identity"* — and [[ADR-166 — Inbound Machine Callers Are Authenticated Principals]] has landed. `recipients/router.py:73,124` already takes `payload.brand_id`; the other three never adopted it. **The stale comment is the more dangerous half**: it tells the next reader the routers are unguarded, which would justify leaving this alone. Source: `/interview-prep-baseline` 2026-09-18, verified same day.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 116, section "Bugs", position 39 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
