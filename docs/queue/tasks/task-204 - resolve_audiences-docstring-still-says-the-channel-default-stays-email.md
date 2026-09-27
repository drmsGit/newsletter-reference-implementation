---
id: TASK-204
title: resolve_audience's docstring still says the channel default stays email
status: To Do
assignee: []
created_date: '2026-09-27 14:20'
labels:
  - backend
dependencies: []
priority: parked
type: chore
ordinal: 105200
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Chore]** Found 2026-09-27 while verifying [[Manager Workflow - design interview]] Cluster 4 gap 15 (`resolve_audience` defaults `channel` to email), which commit 248bf3f fixed: the signature at `backend/app/audience/service.py:514-515` is now `channel: str` with no default, but the docstring at `:547-548` still says *"The default stays email for the screens…"*, contradicting `:521-529`.

**Fix only that sentence.** The same docstring also documents the pre-ADR-176 precedence — that a manual pin is always included and exclude blocks never remove a hand-pinned recipient. **That half is accurate to the code today**, because [[ADR-176 — A Negative Decision Outranks a Positive One]] point 1 is not implemented (task-47). Correcting it now would describe behaviour the code does not have, in the opposite direction. It changes with task-47, not here. (Raised by the interview session's review, 2026-09-27.)
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Logged 2026-09-27 from the "What Cluster N produced" sections of the two design interviews, each gap re-verified against the code that day. The plan was reviewed and approved by the session that ran the interviews. Parked: not yet ranked by anyone.
<!-- SECTION:NOTES:END -->
