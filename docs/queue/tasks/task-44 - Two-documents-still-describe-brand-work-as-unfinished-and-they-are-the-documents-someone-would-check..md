---
id: TASK-44
title: >-
  Two documents still describe brand work as unfinished, and they are the
  documents someone would check.
status: To Do
assignee: []
created_date: '2026-09-27 13:56'
labels:
  - docs
dependencies: []
priority: p3
type: bug
ordinal: 104400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — P3, stale records in three files.** **Two documents still describe brand work as unfinished, and they are the documents someone would check.** (a) [[ADR-150 — Tenancy and Access Model]]'s implementation-status paragraphs at `:120`, `:132-139` and `:164` describe unenforced brand permissions and a brandless `consent_events`; `:164` says *"Today every permission behaves platform-level."* All three are superseded by code as of 2026-09-18 and none is marked so — unlike `:120`, which does carry a "Superseded by the status below" note, which is the pattern to copy. **Per the ADR rules this is an addendum, not a rewrite of Decision.** (b) `HANDOFF.md:3` says *"Brand scoping step 1 built"* while `:305` and `:311` record steps 2 and 3 as built. Source: `/interview-prep-baseline` 2026-09-18.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 126, section "Bugs", position 44 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
