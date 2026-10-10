---
id: TASK-348
title: 'Preference center: a page where a recipient chooses what they get'
status: To Do
assignee: []
created_date: '2026-10-10 21:16'
labels:
  - backend
  - frontend
dependencies: []
priority: parked
type: feature
ordinal: 209500
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
**[Feature, parked]** Today a recipient can only unsubscribe: from one brand, or from everything if the company setting allows (ADR-191). There is no page where they choose which newsletters, purposes or channels they want. That is what a footer's 'manage your preferences' link would point to.

Filed by the user's decision in task-301's design session (2026-10-10, ADR-193 point 7): out of the header/footer work, and parked until prioritised. The visible footer has nothing to link to until this exists; the fixed unsubscribe line covers the legal minimum.

What it would build on:
- the per-message unsubscribe token and public page (ADR-191);
- consent recorded per brand, channel and purpose (ADR-163);
- the purpose vocabulary in task-134;
- the company-wide refusal noted on task-135.

Parked: it must be prioritised before anything else happens to it.
<!-- SECTION:DESCRIPTION:END -->
