---
id: TASK-348
title: 'Preference center: a page where a recipient chooses what they get'
status: To Do
assignee: []
created_date: '2026-10-10 21:16'
updated_date: '2026-10-11 10:02'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-11, the user, while trying the manager app: in the long run the preference center should also show a recipient their **interest profile** (the category affinities the platform has learned from their clicks) and let them correct it:
- **deselecting** a category sets its affinity to 0, so the platform stops choosing it for them;
- **selecting** a category gives it a push (an increase), so it is chosen more.
Open for its design: whether a deselection is a hard exclusion or a score the engine may still raise again from later clicks; how the push is sized against learned signal (task-86, negative affinities, and the signal layer); and whether these corrections are recorded as signals of their own source, so the audit can tell what the recipient chose from what the engine learned. The categories shown come from the shared taxonomy (ADR-150's 2026-09-15 addendum); ADR-080 keeps the taxonomy human-governed.
<!-- SECTION:NOTES:END -->
