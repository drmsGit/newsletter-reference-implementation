---
id: TASK-71
title: >-
  Rework seed/demo content into realistic material — prerequisite for testing
  Mode A.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
updated_date: '2026-10-08 22:25'
labels:
  - backend
dependencies: []
type: feature
ordinal: 202400
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Feature]** **Rework seed/demo content into realistic material — prerequisite for testing Mode A.** Surfaced 2026-07-31 (user). Today's seed content records are placeholders along the lines of *"this is content about X"* — fine for exercising plumbing, **useless for evaluating an AI feature**: a subject-line or content-suggestion task fed placeholder text produces generic output, so a test would be a **false negative** (concluding the feature doesn't work when the input simply carries no signal). Needs: real headlines and body text, realistic length, and enough **category variety** that personalization differences are visible between recipients. Keep the existing outdoor / hiking / wildlife theme so the demo narrative stays coherent. **Two payoffs:** it unblocks meaningful Mode-A testing *and* it is what a prospect actually sees in a demo (same "realistic volumes matter when presenting" argument as the pagination item). **No conflict with [[ADR-143 — AI-Assisted Development Boundary]]:** content records are not personal data — it is *recipient* data that must be pseudonymized, not editorial content. Source: user, 2026-07-31 (raised as a blocker before the Mode A build).
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 218, section "Features", position 24 in that section (top = do next). The description is the original entry, verbatim.

2026-10-08 queue cleanup (backlog-sequencer run 3, verified by hand): partly done. Realistic content exists as backend/scripts/seed_content_chatgpt.csv with its importer, backend/scripts/import_content_csv.py, and seed_content_prompt.md. The demo seed itself still writes placeholder bodies, at backend/scripts/seed_demo_data.py:146 ("An editorial piece about ... issue N"). Mode A in this dated entry is now called Assistive (ADR-140 addendum 2026-10-08).
<!-- SECTION:NOTES:END -->
