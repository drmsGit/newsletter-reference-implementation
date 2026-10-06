---
id: TASK-294
title: >-
  Related data (CRM attributes, sales, product): synced and stored, or pulled
  when needed — and usable in audience rules?
status: To Do
assignee: []
created_date: '2026-10-06 19:25'
updated_date: '2026-10-06 20:11'
labels:
  - backend
  - needs-adr
dependencies: []
type: decision
ordinal: 305350
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**How related data — CRM attributes, sales and product data — gets into the platform, and whether audience rules can use it.** Split out of the task-293 audience-editor interview by the user on 2026-10-06: "this is about 'related data' so next to other attributes this also might cover sales / product data -> how do we get this data into the system. Is it synched into the platform and stored? or are those only pulled into the platform when needed. This will need architectural decision."

**The case that raised it** (the user, for client Condor): "anyone who is interested in beach content and departure airport FRA or BER", where *preferred departure airport* is an attribute synced from the CRM. The task-293 interview already decided that a rule field takes one or more values ("is one of") and that rules stay flat — values OR within a field, fields AND within a rule, rules OR across, exclusions subtract; this task decides which data such a field can read.

**What exists today:**
- `RecipientDB.attributes` (`backend/app/recipients/db_models.py:17`), a JSON column filled by the CRM sync; no audience rule reads it — rules know only language, status and category interest (`backend/app/audience/service.py`, `find_by_criteria`).
- [[ADR-120 — CRM as Customer Source of Truth]] and [[ADR-126 — Maintain Local Recipient Projection]]: the CRM owns the person; the platform keeps a projection.
- [[ADR-123 — Audience Ownership Depends on Reuse]]: long-lived reusable audiences belong in the CRM.
- [[ADR-052 — Delivery Layer Supports Multiple Audience Resolution Modes]]: references, queries, explicit lists.

**Questions for the session** (a starting list):
- Synced and stored (a projection, like the recipient itself) or pulled on demand from the source system when an audience resolves — and what that means for resolution time, offline sends, consistency and GDPR minimisation.
- Scope beyond recipient attributes: sales and product data (orders, bookings, products), which are relations, not fields on a person.
- Which data becomes usable in a rule, and who decides: declared (e.g. a declaration file with label and kind — one of / number / yes-no — proposed in the task-293 interview and parked) or discovered.
- Sensitive attributes (health, credit) and data minimisation (ADR-004, ADR-154).
- Relation to task-215 (criteria cannot express delivery history) and task-96 (engagement-driven suggestions).

**Until then** the task-293 audience editor works only with today's fields: language, status and category interest (decided 2026-10-06).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The way related data enters the platform is decided and recorded in an ADR
- [ ] #2 Which related data audience rules may use, and how it is declared, is decided
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-06: overlaps task-120 ('Sales and transaction data from the CRM or DWH — probably a playbook chapter rather than an implementation'); read it in the same session.
<!-- SECTION:NOTES:END -->
