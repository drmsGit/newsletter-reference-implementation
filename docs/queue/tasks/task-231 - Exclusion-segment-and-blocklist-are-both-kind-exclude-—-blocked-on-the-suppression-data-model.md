---
id: TASK-231
title: >-
  Exclusion segment and blocklist are both kind="exclude" — blocked on the
  suppression data model
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
labels:
  - needs-adr
  - backend
dependencies:
  - TASK-135
priority: parked
type: decision
ordinal: 302200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Needs ADR]** **A distinction the model does not have** (Q2): an **exclusion segment** is an attribute, topic, interest or temporary reason and is editorial; a **blocklist** is legal and data-protection. Both are `kind="exclude"` today.

Source: [[Manager Workflow - design interview]] → What Cluster 4 produced (Q4.2).

**Blocked, not buildable — and deliberately so.** [[ADR-176 — A Negative Decision Outranks a Positive One]] point 3 states this distinction and **does not add a second kind**: nothing currently depends on telling them apart, since point 1 gives both kinds the same power over a pin, and inventing a block kind now would pre-empt the suppression data model that [[ADR-142 — Autonomous Workflows and the Automation Boundary]] §7 explicitly leaves open. This task keeps the knowledge without asserting the work is available. It becomes work when the suppression model (task-135) is decided. (Placed here, not in Features, on the interview session's review, 2026-09-27.)

**Verified against the code 2026-09-27:** a single `kind` column on the rule block (`backend/app/audience/db_models.py:73`); resolution branches only on `== "exclude"` (`backend/app/audience/service.py:567`).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
