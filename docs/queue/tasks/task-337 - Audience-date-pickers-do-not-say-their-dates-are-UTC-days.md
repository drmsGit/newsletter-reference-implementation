---
id: TASK-337
title: Audience date pickers do not say their dates are UTC days
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-09 18:23'
updated_date: '2026-10-10 20:27'
labels:
  - frontend
dependencies: []
type: feature
ordinal: 200750
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature]** An engagement rule with an absolute date range ("clicked between 1 and 15 September") counts each date as a UTC day: backend/app/audience/service.py:797-801 builds both boundaries from UTC midnights, and 'to' covers its whole day (task-296). The editor shows plain date inputs with no zone (frontend/src/screens/AudienceEngagement.tsx:148-152). For a manager in Berlin the range is shifted by one or two hours at each end, silently.

Decided with the user in the 2026-10-09 interview review (Audience Q2): keep UTC, and say so where the dates are picked. A company time zone setting stays a later idea. A manager's own browser zone was rejected, because the same saved rule would then mean different people depending on who opens it.

Source: [[Interview Prep - Since 2026-09-18]] → Audience history, delivery safety and recipient unsubscribe, Q2.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The engagement date pickers state that dates are UTC days
- [ ] #2 The saved rule and its resolution are unchanged
<!-- AC:END -->
