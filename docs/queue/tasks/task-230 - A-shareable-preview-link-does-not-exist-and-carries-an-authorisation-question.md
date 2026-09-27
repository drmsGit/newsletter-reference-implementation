---
id: TASK-230
title: 'A shareable preview link does not exist, and carries an authorisation question'
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
labels:
  - needs-adr
  - backend
dependencies: []
priority: parked
type: decision
ordinal: 302100
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Needs ADR]** A shareable preview link does not exist, and carries an authorisation question.

| # | Gap | Where |
|---|---|---|
| 26 | A shareable preview link does not exist, and carries an authorisation question | new |

Source: [[Variant Editor - design interview]] → What Cluster 4 produced, gap 26.

**Verified against the code 2026-09-27:** no share or preview token, and no signed URL, anywhere in `backend/app/`.

Needs a decision on who may open such a link, and how, before it is buildable.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
