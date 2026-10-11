---
id: TASK-355
title: 'Transactional brand profiles: an email sent without the opt-in check, guarded'
status: To Do
assignee: []
created_date: '2026-10-11 08:39'
labels:
  - backend
  - frontend
dependencies:
  - TASK-350
type: feature
ordinal: 200985
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** Slice 4 of 5 of the brand-profile design (ADR-194, 2026-10-11).

A brand profile is marked marketing (the default) or transactional. A variant using a transactional profile may go out without opt-in consent. Today every planned send is marketing (task-42), and the send-time exclusion stack checks marketing consent for everyone (ADR-163; backend/app/delivery/exclusion.py).

Choosing a transactional profile on a marketing email would bypass that check, which would be a legal breach made with one dropdown. So, decided by the user:
- Creating a transactional profile, or marking one transactional, needs a separate permission and is audited.
- Choosing a transactional profile on a variant shows a clear 'sent without opt-in check' label and is audited.
- Duplicating a transactional profile keeps it transactional only for someone holding that right; otherwise the copy is marketing.
- A transactional profile may leave the unsubscribe text empty, and then no line is shown. The legal details are still on every email (task-350).

Final-design pass with the consent stage: how a transactional send meets the exclusion stack, which purpose it records (task-134's purpose vocabulary), and what still excludes a recipient (an unaddressable recipient, a hard suppression).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Only a holder of the transactional permission can create or mark a transactional profile; it is audited
- [ ] #2 A variant using a transactional profile is sent without the opt-in check, labelled and audited
- [ ] #3 Suppressed or unaddressable recipients are still excluded
<!-- AC:END -->
