---
id: TASK-158
title: >-
  `RecipientDB.attributes` is a completely open JSON blob with no documentation
  or validation bounding what belongs in it — nothing stops it drifting into
  CRM-scope data (service cases, addresses, invo…
status: Done
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 502200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
✅ **[Bug]** `RecipientDB.attributes` is a completely open JSON blob with no documentation or validation bounding what belongs in it — nothing stops it drifting into CRM-scope data (service cases, addresses, invoices) that [[ADR-126 — Maintain Local Recipient Projection]] explicitly forbids ("must not become... a full customer profile repository... a system of record for customer data"). Confirmed: a rich profile growing over time (especially via AI/decisioning) is fine and expected — the actual boundary to enforce is engagement/personalization-relevant data only, never CRM-owned data types. Fix: document and validate the allowed shape/keys for `attributes` so it can't silently absorb forbidden data. Source: [[Interview Prep - Delivery, Providers, Recipients]] → Recipients Q6. **Done 2026-07-12** — `validate_recipient_attributes` rejects keys matching a denylist of CRM-owned-data patterns (address, invoice, ssn, payment, billing, phone, etc.) with a 400, rather than trying to enumerate every allowed key. Verified live: `billing_address` rejected with a clear message; `loyalty_tier`/`preferred_airport` accepted.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 545, section "Done", position 22 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
