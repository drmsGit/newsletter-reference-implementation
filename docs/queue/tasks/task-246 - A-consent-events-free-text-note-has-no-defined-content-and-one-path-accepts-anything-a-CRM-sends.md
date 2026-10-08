---
id: TASK-246
title: >-
  A consent event's free-text note has no defined content, and one path accepts
  anything a CRM sends
status: To Do
assignee: []
created_date: '2026-10-03 09:47'
labels:
  - backend
  - needs-adr
dependencies: []
type: decision
ordinal: 300170
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Decision, data protection]** Found 2026-10-03 during task-208's response-model sweep. `ConsentEventDB.note` (`backend/app/recipients/db_models.py:67`, `String`, no length limit) is not exposed by any response (`RecipientConsentEvent`, `backend/app/recipients/models.py`, drops it), and the user asked what it was meant to hold. **Nothing specifies it**: no ADR defines its content. ADR-163 only notes in passing (line 153) that the CRM sync payload carries one.

What writes it today:
- provider suppression (`suppress_recipient`, `backend/app/recipients/service.py:39-79`): the event type, e.g. 'bounced'. Not personal.
- `create_recipient` (`service.py:264`): 'set via create_recipient for external_id=…'. An internal identifier.
- the seed: 'seed_demo_data.py'.
- **the CRM consent sync** (`backend/app/recipients/router.py:187`, `ConsentSyncRequest.note`): whatever free text the calling system sends, unbounded. This is the path that can carry personal data ('customer phoned, asked to stop, …').

Why it matters: a consent record is a compliance record (ADR-154 keeps proof of consent through erasure in minimised form), and free text can't be minimised by rule. Erasure is unbuilt (`backend/app/privacy/` is empty; task-136), so such a note would never be cleared. The user's direction (2026-10-03): don't expose it on screens; decide what it is first.

Options to weigh, not decided: drop the field from the CRM input; replace it with a short reason code (the same move task-225 proposes for override reasons); or keep it bounded and make it part of task-136's erasure scope.

Related: task-136 (retention and erasure), task-225 (override reason as a code), ADR-154, ADR-163.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 What a consent note may contain is decided and recorded (ADR or ADR-163/154 addendum via the adr-author agent)
- [ ] #2 The CRM sync input enforces that decision
- [ ] #3 Whether and how notes are minimised on erasure is stated for task-136
<!-- AC:END -->
