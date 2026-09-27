---
id: TASK-113
title: >-
  `duplicate_campaign` drops content overrides, and the stated reason is a
  category error.
status: To Do
assignee: []
created_date: '2026-09-27 13:57'
labels:
  - backend
dependencies: []
type: bug
ordinal: 206600
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
🔴 **[Bug] — a duplicated variant renders differently from its original, silently. Found 2026-09-26 closing [[Variant Editor - design interview]] question 3.6.** **`duplicate_campaign` drops content overrides, and the stated reason is a category error.** `backend/app/campaigns/duplication.py:147` groups content overrides with resolutions, snapshots, send instances and content versions — *"each of those is a record of something that happened, and a copy has no history — reproducing them would fabricate decisions, publications and sends"*. That reasoning is right about the other five and wrong about this one, because **an override is dual-natured**: it is a record of what happened (`overridden_by`, `reverted_at`, `outcome_delta`) **and** live configuration that `get_active_content_override` reads on every render. Dropping it means the copy produces different output from the original with nothing said — worst in exactly the duplicate-to-repeat workflow (the weekly newsletter) where a manager duplicates *because* they want the same thing again. **The fix draws the line inside the row rather than around it**, which keeps the docstring's instinct: copy `field_overrides`, `system_content_record_id` and `reason`; do not copy `outcome_delta` or `send_instance_id` (they measure a send that happened) or `reverted_at`; set `active = True`; **copy only rows that are already `active`**, since a reset row is purely history and reproducing it would fabricate precisely what the docstring warns about. **`overridden_by` becomes the person duplicating, not the original author** — carrying the name forward attributes an act they did not perform in a campaign they may not know exists, which is the same fabrication arriving through the field the docstring did not consider. Note that this file already reasons per-field about decision slots (copying name, type, strategy and `max_results` but not `candidate_filter`), so the discrimination is an established pattern here rather than a new one.
<!-- SECTION:DESCRIPTION:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated 2026-09-27 from `docs/backlog.md` line 400, section "Features", position 66 in that section (top = do next). The description is the original entry, verbatim.
<!-- SECTION:NOTES:END -->
