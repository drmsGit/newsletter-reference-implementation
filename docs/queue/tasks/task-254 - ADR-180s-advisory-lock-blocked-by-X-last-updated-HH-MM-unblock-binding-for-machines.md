---
id: TASK-254
title: >-
  ADR-180's advisory lock: "blocked by X, last updated HH:MM, unblock", binding
  for machines
status: To Do
assignee: []
created_date: '2026-10-03 18:01'
labels:
  - backend
  - frontend
dependencies: []
references:
  - >-
    docs/architecture/ADR/ADR-180 — A Lock Is Advisory for a Person and Binding
    for a Machine.md
documentation:
  - >-
    docs/architecture/interview-prep/Campaign Write Surface - final design
    pass.md
type: feature
ordinal: 200060
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Split from task-110 on 2026-10-03 (user): task-110 built the layer underneath, optimistic concurrency (a write carrying If-Match with a stale `updated_at` is refused with 409, `backend/app/campaigns/service.py:_refuse_stale`). This is the layer on top that [[ADR-180 — A Lock Is Advisory for a Person and Binding for a Machine]] decides. Point 1: a variant carries an advisory fence, shown as "blocked by X, last updated HH:MM" with an unblock control that any person may use without asking — a social signal, deliberately not a real lock, so nothing is ever held by someone on holiday. Point 3: the same fence is binding for a machine — an agent never clears a fence it did not set, and a machine write to a variant fenced by somebody else is refused. Point 4: enforced server-side, conditioned on the actor type (`audit.ACTOR_INTEGRATION`), never a grantable permission key. What it needs that does not exist: somewhere to store the fence (who set it, when, on which variant); and "last updated by X", which no table records — the composer writes now audited (task-252) make `audit_events` the source, read by subject, with the `actor_id` to name join that ADR-153 kept out of the audit layer. It belongs with the React variant editor (slice 5 of the design pass), which is the screen that shows the fence; built before it, it would have no surface. Presence bubbles and a per-campaign history were deferred by the user ("not necessary from the beginning").
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A person can fence a variant, sees who fenced it and when, and can clear any fence
- [ ] #2 A machine write to a variant fenced by someone else is refused server-side; a machine can clear only a fence it set
- [ ] #3 "Last updated by X at HH:MM" for a variant is read from audit_events
- [ ] #4 The variant editor shows the fence and the unblock control
<!-- AC:END -->
