---
id: TASK-388
title: Decide whether the server may fetch a web address as the source of an AI draft
status: To Do
assignee: []
created_date: '2026-10-16 19:04'
labels:
  - needs-adr
  - backend
dependencies: []
type: decision
ordinal: 305700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Surfaced 2026-10-16 in the task-368 final-design pass. task-368 asked for a source that could be "a text, a link's text, a short brief"; the user chose pasted text only for now, because no ADR covers the server fetching a web address, and the ADR-141 addendum of 2026-10-16 (point 2) records that the content draft task never fetches one and that this needs its own decision. What the decision has to settle before any code: which addresses the server may reach (public internet only, never localhost, private ranges or the cloud metadata address, so the feature is not a way to make the server read its own network), redirects and how many, size and time limits, which content types it reads and how it strips a page to text, whether the fetched text is stored or, like the pasted source, only sent, and whether an integration may use it or only a person. Also whether this belongs to the AI layer at all or is a general "read a page" capability other features (task-370 prepares a variant from a topic) would share. Related: ADR-140, ADR-141 (addendum 2026-10-16), ADR-144 point 4 (what reaches the model), task-368, task-370.
<!-- SECTION:DESCRIPTION:END -->
