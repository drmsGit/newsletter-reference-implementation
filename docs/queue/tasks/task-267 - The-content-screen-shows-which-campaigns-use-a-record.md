---
id: TASK-267
title: The content screen shows which campaigns use a record
status: To Do
assignee: []
created_date: '2026-10-04 09:23'
labels:
  - frontend
  - backend
dependencies: []
type: feature
ordinal: 200067
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Raised by the user 2026-10-04 while trying the variant editor: "we don't have a list of 'used in campaign' on the content screen, but I assume we will work on the content screen later." A manager looking at a record cannot see where it is used. What exists: GET /content/{id}/unsent-campaigns (task-224) answers the unsent campaigns using it, the count the editor shows beside a catalogue act (ADR-186 point 8). A content screen probably wants all campaigns using the record — sent ones too, marked as sent — which is a small extension of the same query (backend/app/campaigns/monitoring.py: unsent_campaigns_using). To be built with the content screen work rather than on its own.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The content detail screen lists the campaigns whose modules use the record, each linked, sent ones marked as such
<!-- AC:END -->
