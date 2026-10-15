---
id: TASK-379
title: 'How-to: keeping content records in step across brands'
status: To Do
assignee: []
created_date: '2026-10-15 20:04'
labels:
  - docs
dependencies: []
type: docs
ordinal: 210400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Docs]** Raised by the user on 2026-10-15 while deciding how images move between brands (task-112, ADR-197 addendum of 2026-10-15). It is to be written as a "sub chapter": a how-to, not built. Some companies use one content record across many brands. A change would then have to be made in, say, 15 brands by hand. The chapter describes a sync between brand content records, all or some fields. It covers what it would take: which record is the source; which fields follow and which stay local (texts in a brand's tone, its own images); what happens to a field a brand has changed itself; how a frozen, already-sent version stays as it was (ADR-183); and that images are copied, not shared, between brands (ADR-197 addendum). An adopter could build it with an integration key and the content API (ADR-166), or as a feature later.

**Related.** task-112, task-364 (the how-to on analytics), ADR-197, ADR-183, ADR-166, ADR-150.
<!-- SECTION:DESCRIPTION:END -->
